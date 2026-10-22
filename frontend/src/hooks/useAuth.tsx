"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/apiClient";
import type {
    UserProfile,
    UpdateProfilePayload,
    ChangePasswordPayload
} from "@/types/user";

const AUTH_EP = {
    login: "/api/v1/auth/login",
    register: "/api/v1/auth/register",
    me: "/api/v1/auth/me",
    forgot: "/api/v1/auth/forgot-password",
    reset: "/api/v1/auth/reset-password",
    profile: "/api/v1/users/profile",
    changePassword: "/api/v1/users/change-password",
    deleteAccount: "/api/v1/users/account",
};

interface AuthContextType {
    user: UserProfile | null;
    loading: boolean;
    ready: boolean;
    isGuest: boolean;
    isAdmin: boolean;
    sessionError: boolean;
    login: (email: string, password: string) => Promise<{ success: boolean; user?: UserProfile; message?: string }>;
    register: (name: string, email: string, password: string) => Promise<{ success: boolean; message?: string }>;
    updateProfile: (payload: UpdateProfilePayload) => Promise<{ success: boolean; message?: string }>;
    changePassword: (payload: ChangePasswordPayload) => Promise<{ success: boolean; message?: string }>;
    forgotPassword: (email: string) => Promise<{ success: boolean; message?: string }>;
    forgot: (email: string) => Promise<{ success: boolean; message?: string }>;
    resetPassword: (token: string, password: string) => Promise<{ success: boolean; message?: string }>;
    reset: (token: string, password: string) => Promise<{ success: boolean; message?: string }>;
    deleteAccount: () => Promise<{ success: boolean; message?: string }>;
    logout: () => void;
    refreshUser: () => Promise<void>;
    retrySession: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [ready, setReady] = useState<boolean>(false);
    const [sessionError, setSessionError] = useState<boolean>(false);

    // 1. SINKRONISASI SESI (/auth/me)
    const refreshUser = useCallback(async () => {
        if (typeof window === "undefined") return;
        const token = localStorage.getItem("token");

        if (!token) {
            setUser(null);
            setSessionError(false);
            setReady(true);
            return;
        }

        try {
            setSessionError(false);
            const res = await apiClient.get<any>(AUTH_EP.me);
            const data = res.data;

            const mappedUser: UserProfile = {
                id: String(data.id),
                name: data.name || data.full_name || "",
                email: data.email || "",
                role: (String(data.role || "USER").toUpperCase()) as "USER" | "ADMIN",
                avatar_url: data.avatar_url || "",
                is_active: data.is_active ?? true,
                total_detections: Number(data.total_detections ?? 0),
                total_feedbacks: Number(data.total_feedbacks ?? 0),
                created_at: data.created_at || undefined,
            };

            setUser(mappedUser);
            document.cookie = `role=${mappedUser.role}; path=/; max-age=604800; SameSite=Lax`;
        } catch (err: any) {
            // HANYA bersihkan sesi jika server eksplisit menolak kredensial (401)
            if (err.response?.status === 401) {
                localStorage.removeItem("token");
                document.cookie = "token=; Max-Age=0; path=/";
                document.cookie = "role=; Max-Age=0; path=/";
                setUser(null);
                setSessionError(false);
            } else {
                // Gangguan jaringan / timeout backend: jangan anggap tamu dan jangan buang token
                console.warn("[Auth]: Gagal memverifikasi sesi karena gangguan jaringan.");
                setSessionError(true);
            }
        } finally {
            setReady(true);
        }
    }, []);

    useEffect(() => {
        refreshUser();
    }, [refreshUser]);

    // 2. LOGIN PENGGUNA
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
                role: (String(raw.role || "USER").toUpperCase()) as "USER" | "ADMIN",
                avatar_url: raw.avatar_url || "",
                is_active: raw.is_active ?? true,
                total_detections: Number(raw.total_detections ?? 0),
                total_feedbacks: Number(raw.total_feedbacks ?? 0),
                created_at: raw.created_at || undefined,
            };

            localStorage.setItem("token", token);
            document.cookie = `token=${token}; path=/; max-age=604800; SameSite=Lax`;
            document.cookie = `role=${userData.role}; path=/; max-age=604800; SameSite=Lax`;

            setUser(userData);
            setSessionError(false);
            return { success: true, user: userData };
        } catch (err: any) {
            const message = err.response?.data?.detail || "Gagal masuk. Periksa kembali email dan kata sandi.";
            return { success: false, message };
        } finally {
            setLoading(false);
        }
    };

    // 3. REGISTRASI
    const register = async (name: string, email: string, password: string) => {
        setLoading(true);
        try {
            await apiClient.post(AUTH_EP.register, { name, email, password });
            return await login(email, password);
        } catch (err: any) {
            const message = err.response?.data?.detail || "Gagal mendaftar akun.";
            return { success: false, message };
        } finally {
            setLoading(false);
        }
    };

    // 4. PEMBARUAN PROFIL (PUT /users/profile dengan full_name & avatar_url)
    const updateProfile = async (payload: UpdateProfilePayload) => {
        setLoading(true);
        try {
            const fullName = payload.full_name || payload.name;
            const body: Record<string, any> = {
                full_name: fullName,
                avatar_url: payload.avatar_url,
            };

            await apiClient.put(AUTH_EP.profile, body);

            // Update state lokal langsung agar UI responsif seketika
            setUser((prev) => (prev ? {
                ...prev,
                name: fullName || prev.name,
                avatar_url: payload.avatar_url !== undefined ? payload.avatar_url : prev.avatar_url,
            } : null));

            return { success: true, message: "Profil berhasil diperbarui." };
        } catch (err: any) {
            return { success: false, message: err.response?.data?.detail || "Gagal memperbarui profil." };
        } finally {
            setLoading(false);
        }
    };

    // 5. GANTI PASSWORD (Dengan validasi konfirmasi lokal terlebih dahulu)
    const changePassword = async (payload: ChangePasswordPayload) => {
        if (payload.confirm_password && payload.new_password !== payload.confirm_password) {
            return { success: false, message: "Konfirmasi kata sandi baru tidak cocok." };
        }

        setLoading(true);
        try {
            const res = await apiClient.post(AUTH_EP.changePassword, {
                old_password: payload.old_password,
                new_password: payload.new_password,
            });
            return { success: true, message: res.data?.message || "Kata sandi berhasil diperbarui." };
        } catch (err: any) {
            return { success: false, message: err.response?.data?.detail || "Gagal mengganti kata sandi." };
        } finally {
            setLoading(false);
        }
    };

    // 6. FORGOT & RESET PASSWORD (Mendukung alias nama metode)
    const forgotPassword = async (email: string) => {
        setLoading(true);
        try {
            await apiClient.post(AUTH_EP.forgot, { email });
            return { success: true, message: "Instruksi reset kata sandi telah dikirim ke email." };
        } catch (err: any) {
            return {
                success: false,
                message: err.response?.data?.detail || "Fitur reset kata sandi sedang dalam penyesuaian backend (404)."
            };
        } finally {
            setLoading(false);
        }
    };

    const resetPassword = async (token: string, password: string) => {
        setLoading(true);
        try {
            await apiClient.post(AUTH_EP.reset, { token_code: token, new_password: password });
            return { success: true, message: "Kata sandi berhasil diatur ulang. Silakan login." };
        } catch (err: any) {
            return {
                success: false,
                message: err.response?.data?.detail || "Gagal mengatur ulang kata sandi."
            };
        } finally {
            setLoading(false);
        }
    };

    // 7. HAPUS AKUN (Penanganan elegan jika endpoint belum terpasang di backend)
    const deleteAccount = async () => {
        setLoading(true);
        try {
            await apiClient.delete(AUTH_EP.deleteAccount);
            logout();
            return { success: true, message: "Akun berhasil dihapus." };
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            return {
                success: false,
                message: detail || "Fitur hapus akun belum didukung oleh server (404)."
            };
        } finally {
            setLoading(false);
        }
    };

    // 8. LOGOUT
    const logout = () => {
        localStorage.removeItem("token");
        document.cookie = "token=; Max-Age=0; path=/";
        document.cookie = "role=; Max-Age=0; path=/";
        setUser(null);
        setSessionError(false);
        window.location.href = "/auth/login";
    };

    return (
        <AuthContext.Provider
            value= {{
        user,
            loading,
            ready,
            isGuest: ready && !user && !sessionError,
                isAdmin: user?.role === "ADMIN",
                    sessionError,
                    login,
                    register,
                    updateProfile,
                    changePassword,
                    forgotPassword,
                    forgot: forgotPassword,
                        resetPassword,
                        reset: resetPassword,
                            deleteAccount,
                            logout,
                            refreshUser,
                            retrySession: refreshUser,
            }
}
        >
    { children }
    </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}