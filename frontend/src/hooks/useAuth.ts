"use client";

import { useState, useEffect, useCallback } from "react";
import { isAxiosError } from "axios";
import { apiClient, getApiConnectionMessage } from "@/lib/apiClient";
import type { UserProfile, UpdateProfilePayload, ChangePasswordPayload } from "@/types/user";

const AUTH_EP = {
    login: "/api/v1/auth/login",
    register: "/api/v1/auth/register",
    me: "/api/v1/auth/me",
    forgot: "/api/v1/auth/forgot-password",
    reset: "/api/v1/auth/reset-password",
    profile: "/api/v1/users/profile",
    changePassword: "/api/v1/users/change-password",
};

const parseErrorMessage = (err: any, fallback: string): string => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail)) {
        const msg = detail
            .map((d: any) => (d && typeof d.msg === "string" ? d.msg : ""))
            .filter(Boolean)
            .join(", ");
        if (msg) return msg;
    }
    return fallback;
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
                message: getApiConnectionMessage(err) ?? parseErrorMessage(
                    err,
                    err?.response?.status === 401
                        ? "Email atau kata sandi salah."
                        : "Gagal masuk. Silakan coba lagi."
                ),
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

    // --- 1. LUPA PASSWORD (Kirim email tautan) ---
    const forgotPassword = async (email: string) => {
        setLoading(true);
        try {
            const res = await apiClient.post(AUTH_EP.forgot, {
                email: email.trim().toLowerCase()
            });
            return {
                success: true,
                message: res.data?.message || "Tautan pemulihan kata sandi telah dikirim ke email Anda."
            };
        } catch (err: any) {
            return {
                success: false,
                message: parseErrorMessage(err, "Gagal memproses permintaan lupa kata sandi.")
            };
        } finally {
            setLoading(false);
        }
    };

    // --- 2. RESET PASSWORD (Pakai token dari link email) ---
    const resetPassword = async (token: string, password: string, confirmPassword?: string) => {
        setLoading(true);
        try {
            const res = await apiClient.post(AUTH_EP.reset, {
                token: token.trim(),
                new_password: password,
                confirm_password: confirmPassword || password,
            });
            return {
                success: true,
                message: res.data?.message || "Kata sandi berhasil diperbarui. Silakan login."
            };
        } catch (err: any) {
            return {
                success: false,
                message: parseErrorMessage(err, "Tautan reset tidak valid atau sudah kedaluwarsa.")
            };
        } finally {
            setLoading(false);
        }
    };

    // --- 3. GANTI PASSWORD (Saat sudah login) ---
    const changePassword = async (payload: ChangePasswordPayload) => {
        if (payload.confirm_password && payload.new_password !== payload.confirm_password) {
            return { success: false, message: "Konfirmasi kata sandi baru tidak cocok." };
        }

        setLoading(true);
        try {
            const res = await apiClient.post(AUTH_EP.changePassword, {
                old_password: payload.old_password,
                new_password: payload.new_password,
                confirm_password: payload.confirm_password,
            });
            return {
                success: true,
                message: res.data?.message || "Kata sandi berhasil diperbarui."
            };
        } catch (err: any) {
            return {
                success: false,
                message: parseErrorMessage(err, "Gagal mengganti kata sandi.")
            };
        } finally {
            setLoading(false);
        }
    };

    // --- 4. UPDATE PROFIL (Nama & Avatar) ---
    const updateProfile = async (payload: UpdateProfilePayload) => {
        setLoading(true);
        try {
            const fullName = payload.full_name || payload.name;
            const res = await apiClient.put(AUTH_EP.profile, {
                full_name: fullName,
                avatar_url: payload.avatar_url,
            });

            // Update state user lokal langsung
            setUser((prev) => prev ? {
                ...prev,
                name: fullName || prev.name,
                avatar_url: payload.avatar_url !== undefined ? payload.avatar_url : prev.avatar_url,
            } : null);

            return { success: true, message: res.data?.message || "Profil berhasil diperbarui." };
        } catch (err: any) {
            return {
                success: false,
                message: parseErrorMessage(err, "Gagal memperbarui profil.")
            };
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
        forgotPassword,
        forgot: forgotPassword,
        resetPassword,
        reset: resetPassword,
        changePassword,
        updateProfile,
        logout,
        refreshUser,
    };
}
