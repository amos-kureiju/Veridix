"use client";

import { useState, useEffect, useCallback } from "react";
import { isAxiosError } from "axios";
import { apiClient } from "@/lib/apiClient";
import type { UserProfile } from "@/types/user";

const AUTH_EP = {
    login: "/api/v1/auth/login",
    register: "/api/v1/auth/register",
    me: "/api/v1/auth/me",
    forgot: "/api/v1/auth/forgot-password",
    reset: "/api/v1/auth/reset-password",
    profile: "/api/v1/users/profile",
    changePassword: "/api/v1/users/change-password",
};

export function useAuth() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [ready, setReady] = useState<boolean>(false);
    const [sessionError, setSessionError] = useState<string | null>(null);

    const refreshUser = useCallback(async () => {
        setReady(false);
        setSessionError(null);
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
        if (!token) {
            setUser(null);
            setReady(true);
            return;
        }
        try {
            const res = await apiClient.get<any>(AUTH_EP.me);
            if (localStorage.getItem("token") !== token) return;
            const data = res.data;
            setUser({
                id: String(data.id),
                name: data.name || data.full_name || "",
                email: data.email,
                role: String(data.role).toUpperCase() as "USER" | "ADMIN",
                avatar_url: data.avatar_url || "",
                total_detections: data.total_detections ?? 0,
                total_feedbacks: data.total_feedbacks ?? 0,
                is_active: data.is_active,
                created_at: data.created_at ?? "",
            });
        } catch (err: any) {
            if (localStorage.getItem("token") !== token) return;
            if (err.response?.status === 401) {
                localStorage.removeItem("token");
                document.cookie = "token=; Max-Age=0; path=/";
                document.cookie = "role=; Max-Age=0; path=/";
                setUser(null);
            } else {
                setSessionError("Tidak dapat memverifikasi sesi. Pastikan backend aktif lalu coba lagi.");
            }
        } finally {
            setReady(true);
        }
    }, []);

    useEffect(() => {
        const handleSessionExpired = () => {
            setUser(null);
            setSessionError(null);
            setReady(true);
        };
        window.addEventListener("auth:session-expired", handleSessionExpired);
        refreshUser();
        return () => window.removeEventListener("auth:session-expired", handleSessionExpired);
    }, [refreshUser]);

    const login = async (email: string, password: string) => {
        setLoading(true);
        try {
            const res = await apiClient.post<{ access_token: string; user: any }>(
                AUTH_EP.login,
                { email, password }
            );
            const token = res.data.access_token;
            const raw = res.data.user;

            const userData: UserProfile = {
                id: String(raw.id),
                name: raw.name || raw.full_name || "",
                email: raw.email || email,
                role: String(raw.role).toUpperCase() as "USER" | "ADMIN",
                avatar_url: raw.avatar_url || "",
                total_detections: raw.total_detections ?? 0,
                total_feedbacks: raw.total_feedbacks ?? 0,
                is_active: raw.is_active,
                created_at: raw.created_at ?? "",
            };

            localStorage.setItem("token", token);
            document.cookie = `token=${token}; path=/; max-age=604800; SameSite=Lax`;
            document.cookie = `role=${userData.role}; path=/; max-age=604800; SameSite=Lax`;

            setUser(userData);
            setSessionError(null);
            setReady(true);
            return { success: true, user: userData };
        } catch (err: any) {
            return {
                success: false,
                message: err.response?.data?.detail || "Email atau kata sandi salah."
            };
        } finally {
            setLoading(false);
        }
    };

    const register = async (name: string, email: string, password: string) => {
        setLoading(true);
        try {
            const res = await apiClient.post<{ status: string; message: string }>(
                AUTH_EP.register,
                { name: name.trim(), email: email.trim().toLowerCase(), password }
            );
            return { success: true, message: res.data.message };
        } catch (err: unknown) {
            const detail = isAxiosError<{ detail?: string | { msg: string }[] }>(err)
                ? err.response?.data?.detail
                : undefined;
            const message = typeof detail === "string"
                ? detail
                : Array.isArray(detail) ? detail.map(issue => issue.msg).join(" ") : "";
            return { success: false, message: message || "Pendaftaran gagal. Silakan coba lagi." };
        } finally {
            setLoading(false);
        }
    };

    const logout = () => {
        localStorage.removeItem("token");
        document.cookie = "token=; Max-Age=0; path=/";
        document.cookie = "role=; Max-Age=0; path=/";
        setUser(null);
        window.location.href = "/";
    };

    return {
        user,
        ready,
        sessionError,
        retrySession: refreshUser,
        isGuest: ready && !user,
        isAdmin: user?.role === "ADMIN",
        loading,
        login,
        register,
        logout,
        refreshUser,
    };
}
