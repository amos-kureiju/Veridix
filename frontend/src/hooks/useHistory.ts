"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient as api, getApiConnectionMessage } from "@/lib/apiClient";
import type { HistoryItem } from "@/types/detector";

export function historyErrorMessage(error: unknown, fallback: string): string {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    return typeof detail === "string" ? detail : getApiConnectionMessage(error) || fallback;
}

type Scope = { key: string; token: string | null; active: boolean };
type HistoryState = { key: string; items: HistoryItem[]; loading: boolean; error: string | null };

export function useHistory(enabled: boolean, accountId?: string) {
    const token = typeof localStorage === "undefined" ? null : localStorage.getItem("token");
    const key = JSON.stringify([enabled, accountId ?? null, token]);
    const scopeRef = useRef<Scope>({ key, token, active: true });
    if (scopeRef.current.key !== key) scopeRef.current = { key, token, active: true };
    const scope = scopeRef.current;
    const requests = useRef(new Map<AbortController, Scope>());
    const listRequest = useRef<AbortController | null>(null);
    const generation = useRef(0);
    const [state, setState] = useState<HistoryState>({ key, items: [], loading: false, error: null });

    const current = useCallback(() => enabled && scope.active && scopeRef.current === scope &&
        Boolean(scope.token) && localStorage.getItem("token") === scope.token, [enabled, scope]);

    const begin = useCallback((signal?: AbortSignal) => {
        if (!current() || signal?.aborted) return null;
        const controller = new AbortController();
        const abort = () => controller.abort();
        signal?.addEventListener("abort", abort, { once: true });
        requests.current.set(controller, scope);
        return {
            controller,
            valid: () => current() && !controller.signal.aborted,
            finish: () => {
                signal?.removeEventListener("abort", abort);
                requests.current.delete(controller);
            },
        };
    }, [current, scope]);

    const reload = useCallback(async (signal?: AbortSignal): Promise<boolean> => {
        // Check ownership before cancelling: an old callback cannot cancel a new session's list.
        const request = begin(signal);
        if (!request) return false;
        listRequest.current?.abort();
        listRequest.current = request.controller;
        const version = ++generation.current;
        setState(previous => ({ key, items: previous.key === key ? previous.items : [], loading: true, error: null }));
        try {
            const response = await api.get("/api/v1/users/history", { signal: request.controller.signal });
            if (!request.valid() || version !== generation.current) return false;
            const data = response.data?.data ?? response.data;
            if (!Array.isArray(data)) throw new Error("Invalid history response");
            setState({ key, items: data, loading: false, error: null });
            return true;
        } catch (error) {
            if (request.valid() && version === generation.current) {
                setState(previous => ({ key, items: previous.key === key ? previous.items : [], loading: false,
                    error: historyErrorMessage(error, "Gagal memuat riwayat deteksi. Silakan coba lagi.") }));
            }
            return false;
        } finally {
            request.finish();
        }
    }, [begin, key]);

    const getDetail = useCallback(async (id: string, signal?: AbortSignal): Promise<HistoryItem | null> => {
        const request = begin(signal);
        if (!request) return null;
        try {
            const response = await api.get(`/api/v1/users/history/${encodeURIComponent(id)}`, { signal: request.controller.signal });
            if (!request.valid()) return null;
            if (response.data?.status !== "success" || response.data?.data?.id !== id) throw new Error("Invalid detail response");
            return response.data.data;
        } catch (error) {
            if (request.valid()) throw error;
            return null;
        } finally {
            request.finish();
        }
    }, [begin]);

    const remove = useCallback(async (id: string, signal?: AbortSignal): Promise<boolean> => {
        const request = begin(signal);
        if (!request) return false;
        try {
            const response = await api.delete(`/api/v1/users/history/${encodeURIComponent(id)}`, { signal: request.controller.signal });
            if (!request.valid()) return false;
            if (response.data?.status !== "success" || response.data?.data?.id !== id) throw new Error("Invalid deletion response");
            // A list started before deletion must not restore the deleted row.
            ++generation.current;
            listRequest.current?.abort();
            setState(previous => ({ key, items: previous.key === key ? previous.items.filter(item => item.id !== id) : [], loading: false, error: null }));
            return true;
        } catch (error) {
            if (request.valid()) throw error;
            return false;
        } finally {
            request.finish();
        }
    }, [begin, key]);

    useEffect(() => {
        scope.active = true;
        void reload();
        return () => {
            scope.active = false;
            for (const [controller, owner] of requests.current) if (owner === scope) controller.abort();
        };
    }, [reload, scope]);

    const visible = state.key === key && enabled && token;
    const items = visible ? state.items : [];
    const loading = visible ? state.loading : false;
    const error = visible ? state.error : null;
    return { items, loading, error, isEmpty: !loading && !error && items.length === 0, reload, getDetail, remove };
}
