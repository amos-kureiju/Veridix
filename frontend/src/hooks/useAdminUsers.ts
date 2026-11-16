"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { isAxiosError, isCancel } from "axios";
import { apiClient, getApiConnectionMessage } from "@/lib/apiClient";
import type {
    AdminUserListResponse,
    AdminUsersParams,
    AdminUserStatusResult,
    ManagedUser,
    UserStatusUpdateResponse,
} from "@/types/admin";

type Query = AdminUsersParams & { skip: number; limit: number };
type Filters = Pick<AdminUsersParams, "search" | "role" | "is_active">;
type Scope = { key: string; token: string | null; active: boolean };
type View = { scope: Scope; key: string; params: Query };
type Request = { scope: Scope; controller: AbortController; valid: () => boolean; finish: () => void };
type ListState = {
    key: string;
    users: ManagedUser[];
    total: number | null;
    count: number | null;
    loading: boolean;
    error: string | null;
    hasLoaded: boolean;
    stale: boolean;
};

const ENDPOINT = "/api/v1/admin/users";
const DEFAULT_QUERY: Query = { skip: 0, limit: 20 };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const tokenInBrowser = () => typeof window === "undefined" ? null : window.localStorage.getItem("token");
const record = (value: unknown): value is Record<string, unknown> =>
    typeof value === "object" && value !== null && !Array.isArray(value);
const integer = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const timestamp = (value: unknown): value is string => typeof value === "string" &&
    /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value));

function parseUser(value: unknown): ManagedUser {
    if (!record(value) || typeof value.id !== "string" || !UUID.test(value.id) ||
        typeof value.name !== "string" || typeof value.email !== "string" || !value.email.trim() ||
        (value.role !== "USER" && value.role !== "ADMIN") || !integer(value.analysis_count) ||
        typeof value.is_active !== "boolean" || typeof value.has_password !== "boolean" ||
        typeof value.google_linked !== "boolean" || !timestamp(value.created_at)) {
        throw new Error("Format data akun dari server tidak valid.");
    }
    return {
        id: value.id.toLowerCase(), name: value.name, email: value.email, role: value.role,
        analysis_count: value.analysis_count, is_active: value.is_active,
        has_password: value.has_password, google_linked: value.google_linked, created_at: value.created_at,
    };
}

function parseList(value: unknown, params: Query): AdminUserListResponse {
    if (!record(value) || value.status !== "success" || !Array.isArray(value.data) ||
        !integer(value.count) || !integer(value.total) || !integer(value.skip) || !integer(value.limit) ||
        value.limit < 1 || value.limit > 100 || value.skip !== params.skip || value.limit !== params.limit ||
        value.count !== value.data.length || value.count > value.limit || value.total < value.count ||
        (value.count > 0 && value.skip + value.count > value.total)) {
        throw new Error("Format daftar atau pagination pengguna dari server tidak valid.");
    }
    const data = value.data.map(parseUser);
    if (new Set(data.map(user => user.id)).size !== data.length) {
        throw new Error("Daftar pengguna dari server memuat ID yang berulang.");
    }
    return { status: "success", data, count: value.count, total: value.total, skip: value.skip, limit: value.limit };
}

function parseStatus(value: unknown, id: string, isActive: boolean): UserStatusUpdateResponse {
    if (!record(value) || value.status !== "success" || typeof value.message !== "string" || !value.message.trim() || !record(value.data) ||
        typeof value.data.id !== "string" || value.data.id.toLowerCase() !== id || value.data.is_active !== isActive) {
        throw new Error("Respons perubahan status tidak sesuai permintaan. Muat ulang daftar untuk memastikan hasilnya.");
    }
    return { status: "success", message: value.message, data: { id, is_active: isActive } };
}

function errorMessage(error: unknown, fallback: string): string {
    const connection = getApiConnectionMessage(error);
    if (connection) return connection;
    if (isAxiosError<{ detail?: unknown }>(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string" && detail.trim()) return detail;
        if (Array.isArray(detail)) {
            const messages = detail.filter(record).map(issue => issue.msg).filter((msg): msg is string => typeof msg === "string");
            if (messages.length) return messages.join(" ");
        }
        return fallback;
    }
    return error instanceof Error ? error.message : fallback;
}

function emptyList(key: string): ListState {
    return { key, users: [], total: null, count: null, loading: false, error: null, hasLoaded: false, stale: false };
}

/** Call only with an enabled flag derived from a verified admin session. */
export function useAdminUsers(enabled: boolean, adminId?: string) {
    const token = tokenInBrowser();
    const scopeKey = JSON.stringify([enabled, adminId ?? null, token]);
    const scopeRef = useRef<Scope>({ key: scopeKey, token, active: true });
    if (scopeRef.current.key !== scopeKey) scopeRef.current = { key: scopeKey, token, active: true };
    const scope = scopeRef.current;

    const [queryState, setQueryState] = useState({ key: scopeKey, params: DEFAULT_QUERY });
    const params = queryState.key === scopeKey ? queryState.params : DEFAULT_QUERY;
    const viewKey = JSON.stringify([scopeKey, params]);
    const viewRef = useRef<View>({ scope, key: viewKey, params });
    if (viewRef.current.key !== viewKey) viewRef.current = { scope, key: viewKey, params };

    const [state, setState] = useState<ListState>(() => emptyList(viewKey));
    const [mutations, setMutations] = useState<{ key: string; savingIds: string[]; error: string | null }>({
        key: scopeKey, savingIds: [], error: null,
    });
    const requests = useRef(new Set<Request>());
    const listRequest = useRef<Request | null>(null);
    const pendingStatus = useRef(new Map<string, Request>());
    const generation = useRef(0);

    const current = useCallback(() => enabled && scope.active && scopeRef.current === scope &&
        Boolean(scope.token) && tokenInBrowser() === scope.token, [enabled, scope]);

    const begin = useCallback((signal?: AbortSignal): Request | null => {
        if (!current() || signal?.aborted) return null;
        const controller = new AbortController();
        const abort = () => controller.abort();
        signal?.addEventListener("abort", abort, { once: true });
        const request: Request = {
            scope, controller,
            valid: () => current() && !controller.signal.aborted,
            finish: () => {
                signal?.removeEventListener("abort", abort);
                requests.current.delete(request);
            },
        };
        requests.current.add(request);
        return request;
    }, [current, scope]);

    const reload = useCallback(async (signal?: AbortSignal): Promise<boolean> => {
        const request = begin(signal);
        if (!request) return false;
        const view = viewRef.current;
        listRequest.current?.controller.abort();
        listRequest.current = request;
        const version = ++generation.current;
        const ownsView = () => current() && version === generation.current && viewRef.current === view;
        const valid = () => request.valid() && ownsView();
        setState(previous => valid() ? {
            ...(previous.key === view.key ? previous : emptyList(view.key)), loading: true, error: null,
        } : previous);
        try {
            const response = await apiClient.get<unknown>(ENDPOINT, { params: view.params, signal: request.controller.signal });
            if (!valid()) return false;
            const result = parseList(response.data, view.params);
            setState(previous => valid() ? {
                key: view.key, users: result.data, total: result.total, count: result.count,
                loading: false, error: null, hasLoaded: true, stale: false,
            } : previous);
            return true;
        } catch (error: unknown) {
            if (valid() && !isCancel(error)) {
                const denied = isAxiosError(error) && (error.response?.status === 401 || error.response?.status === 403);
                setState(previous => valid() ? {
                    ...(!denied && previous.key === view.key ? previous : emptyList(view.key)), loading: false,
                    error: errorMessage(error, "Gagal memuat daftar pengguna. Silakan coba lagi."),
                    stale: !denied && previous.key === view.key && previous.hasLoaded,
                } : previous);
            }
            return false;
        } finally {
            // External cancellation still ends loading, without touching a newer request/view.
            if (ownsView()) setState(previous => ownsView() ? { ...previous, loading: false } : previous);
            if (listRequest.current === request) listRequest.current = null;
            request.finish();
        }
    }, [begin, current]);

    const setFilters = useCallback((filters: Filters) => {
        if (!current()) return;
        setQueryState(previous => {
            if (!current()) return previous;
            const base = previous.key === scopeKey ? previous.params : DEFAULT_QUERY;
            const next = { ...base, ...filters, skip: 0 };
            next.search = next.search?.trim() || undefined;
            return { key: scopeKey, params: next };
        });
    }, [current, scopeKey]);

    const setPage = useCallback((skip: number, limit?: number) => {
        if (!current()) return;
        if (!integer(skip) || (limit !== undefined && (!integer(limit) || limit < 1 || limit > 100))) {
            throw new Error("Posisi atau ukuran halaman pengguna tidak valid.");
        }
        setQueryState(previous => {
            if (!current()) return previous;
            const base = previous.key === scopeKey ? previous.params : DEFAULT_QUERY;
            return { key: scopeKey, params: { ...base, skip, limit: limit ?? base.limit } };
        });
    }, [current, scopeKey]);

    const updateStatus = useCallback(async (id: string, nextActive: boolean, signal?: AbortSignal): Promise<AdminUserStatusResult> => {
        const request = begin(signal);
        if (!request) return { success: false, cancelled: true, message: "Permintaan tidak lagi berada pada sesi admin yang aktif." };
        const userId = id.toLowerCase();
        if (!UUID.test(userId) || typeof nextActive !== "boolean") {
            request.finish();
            return { success: false, message: "ID atau status pengguna tidak valid." };
        }
        if (pendingStatus.current.get(userId)?.scope === scope) {
            request.finish();
            return { success: false, message: "Perubahan status akun ini masih diproses." };
        }
        pendingStatus.current.set(userId, request);
        setMutations(previous => request.valid() ? {
            key: scopeKey, savingIds: [...(previous.key === scopeKey ? previous.savingIds : []), userId], error: null,
        } : previous);
        try {
            const response = await apiClient.patch<unknown>(`${ENDPOINT}/${encodeURIComponent(userId)}/status`,
                { is_active: nextActive }, { signal: request.controller.signal });
            if (!request.valid()) return { success: false, cancelled: true, message: "Sesi admin telah berubah." };
            const result = parseStatus(response.data, userId, nextActive);
            // A list started before this confirmation must not restore the previous status.
            ++generation.current;
            listRequest.current?.controller.abort();
            const view = viewRef.current;
            setState(previous => current() && viewRef.current === view && previous.key === view.key ? {
                ...previous, users: previous.users.map(user => user.id === userId ? { ...user, is_active: nextActive } : user),
                total: null, count: null, stale: true, error: null,
            } : previous);
            const refreshed = await reload();
            if (!current()) return { success: false, cancelled: true, message: "Sesi admin telah berubah." };
            return { success: true, message: result.message, data: result.data, refreshed };
        } catch (error: unknown) {
            if (!request.valid() || isCancel(error)) return { success: false, cancelled: true, message: "Permintaan dibatalkan." };
            const connection = getApiConnectionMessage(error);
            const message = connection
                ? `${connection} Hasil perubahan belum dapat dipastikan. Muat ulang daftar untuk memeriksa status akun.`
                : errorMessage(error, "Server belum mengonfirmasi perubahan status pengguna.");
            setMutations(previous => request.valid() ? {
                key: scopeKey, savingIds: previous.key === scopeKey ? previous.savingIds : [], error: message,
            } : previous);
            return { success: false, message };
        } finally {
            if (pendingStatus.current.get(userId) === request) pendingStatus.current.delete(userId);
            setMutations(previous => current() && previous.key === scopeKey ? {
                ...previous, savingIds: previous.savingIds.filter(value => value !== userId),
            } : previous);
            request.finish();
        }
    }, [begin, current, reload, scope, scopeKey]);

    const clearMutationError = useCallback(() => {
        setMutations(previous => current() && previous.key === scopeKey ? { ...previous, error: null } : previous);
    }, [current, scopeKey]);

    useEffect(() => {
        scope.active = true;
        return () => {
            scope.active = false;
            for (const request of requests.current) if (request.scope === scope) request.controller.abort();
        };
    }, [scope]);

    useEffect(() => { void reload(); }, [reload, viewKey]);

    const visible = current() && state.key === viewKey;
    const users = visible ? state.users : [];
    const loading = current() && (!visible || state.loading);
    const error = visible ? state.error : null;
    const hasLoaded = visible && state.hasLoaded;
    const stale = visible && state.stale;
    return {
        users, total: visible ? state.total : null, count: visible ? state.count : null, params,
        loading, error, hasLoaded, stale,
        isEmpty: hasLoaded && !loading && !error && !stale && state.total === 0,
        isPageEmpty: hasLoaded && !loading && !error && !stale && users.length === 0 && (state.total ?? 0) > 0,
        savingIds: current() && mutations.key === scopeKey ? mutations.savingIds : [],
        mutationError: current() && mutations.key === scopeKey ? mutations.error : null,
        setFilters, setPage, reload, updateStatus, clearMutationError,
    };
}
