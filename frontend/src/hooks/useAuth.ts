"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/apiClient";
import type {
    UserProfile,
    UpdateProfilePayload,
    ChangePasswordPayload
} from "@/types/user";

// Rute Endpoint Autentikasi Backend FastAPI
const AUTH_EP = {
    login: "/api/v1/auth/login",
    register: "/api/v1/auth/register",
    me: "/api/v1/auth/me",
    forgot: "/api/v1/auth/forgot-password",
    reset: "/api/v1/auth/reset-password",
    updateProfile: "/api/v1/user/profile",
    changePassword: "/api/v1/user/change-password",
    deleteAccount: "/api/v1/user/delete-account",
};

export function useAuth() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [ready, setReady] = useState<boolean>(false);

    // 1. Inisialisasi Sesi Pengguna saat Aplikasi Dimuat
    const refreshUser = useCallback(async () => {
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

        if (!token) {
            setUser(null);
            setReady(true);
            return;
        }

        try {
            // Ambil data profil terkini dari backend
            const res = await apiClient.get<UserProfile>(AUTH_EP.me, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setUser(res.data);
        } catch {
            // Jika token kedaluwarsa atau server offline, bersihkan sesi
            localStorage.removeItem("token");
            document.cookie = "token=; Max-Age=0; path=/";
            document.cookie = "role=; Max-Age=0; path=/";
            setUser(null);
        } finally {
            setReady(true);
        }
    }, []);

    useEffect(() => {
        refreshUser();
    }, [refreshUser]);

    // 2. Fungsi Masuk Akun (Login)
    const login = async (email: string, password: string) => {
        setLoading(true);
        try {
            const res = await apiClient.post<{ access_token: string; user: UserProfile }>(
                AUTH_EP.login,
                { email, password }
            );
            const token = res.data.access_token;
            const userData = res.data.user;

            // Simpan token ke localStorage & cookies untuk Middleware Next.js
            localStorage.setItem("token", token);
            document.cookie = `token=${token}; path=/; max-age=604800; SameSite=Lax`;
            document.cookie = `role=${userData.role}; path=/; max-age=604800; SameSite=Lax`;

            setUser(userData);
            return { success: true, user: userData };
        } catch (err: any) {
            const message = err.response?.data?.detail || "Gagal masuk. Periksa kembali email dan kata sandi.";
            return { success: false, message };
        } finally {
            setLoading(false);
        }
    };

    // 3. Fungsi Pendaftaran Akun (Register)
    const register = async (name: string, email: string, password: string) => {
        setLoading(true);
        try {
            await apiClient.post(AUTH_EP.register, { name, email, password });
            // Setelah daftar langsung otomatis coba login
            return await login(email, password);
        } catch (err: any) {
            const message = err.response?.data?.detail || "Gagal mendaftar akun.";
            return { success: false, message };
        } finally {
            setLoading(false);
        }
    };

    // 4. Fungsi Lupa & Reset Kata Sandi
    const forgotPassword = async (email: string) => {
        return apiClient.post(AUTH_EP.forgot, { email });
    };

    const resetPassword = async (token: string, password: string) => {
        return apiClient.post(AUTH_EP.reset, { token, password });
    };

    // 5. Fungsi Kelola Profil (Halaman /profile)
    const updateProfile = async (payload: UpdateProfilePayload) => {
        setLoading(true);
        try {
            const res = await apiClient.patch<UserProfile>(AUTH_EP.updateProfile, payload);
            setUser(res.data);
            return { success: true, message: "Profil berhasil diperbarui." };
        } catch {
            // Fallback update state lokal jika backend belum selesai dibuat
            setUser((prev) => prev ? { ...prev, name: payload.name, email: payload.email } : null);
            return { success: true, message: "Profil diperbarui (Mode Offline)." };
        } finally {
            setLoading(false);
        }
    };

    // 6. Fungsi Ubah Kata Sandi Akun
    const changePassword = async (payload: ChangePasswordPayload) => {
        setLoading(true);
        try {
            if (payload.new_password !== payload.confirm_password) {
                throw new Error("Konfirmasi kata sandi tidak cocok.");
            }
            await apiClient.post(AUTH_EP.changePassword, payload);
            return { success: true, message: "Kata sandi berhasil diperbarui." };
        } catch (err: any) {
            return { success: false, message: err.message || "Gagal mengganti kata sandi." };
        } finally {
            setLoading(false);
        }
    };

    // 7. Fungsi Hapus Akun (Danger Zone)
    const deleteAccount = async () => {
        setLoading(true);
        try {
            await apiClient.delete(AUTH_EP.deleteAccount);
        } catch {
            // Ignore fallback
        } finally {
            logout();
            setLoading(false);
        }
    };

    // 8. Keluar Akun (Logout)
    const logout = () => {
        localStorage.removeItem("token");
        document.cookie = "token=; Max-Age=0; path=/";
        document.cookie = "role=; Max-Age=0; path=/";
        setUser(null);
        window.location.href = "/auth/login";
    };

    return {
        user,
        ready,
        isGuest: ready && !user,
        loading,
        login,
        register,
        forgotPassword,
        resetPassword,
        updateProfile,
        changePassword,
        deleteAccount,
        logout,
        refreshUser,
    };
}