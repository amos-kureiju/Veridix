"use client";

import { useState } from "react";
import type { UserProfile, UpdateProfilePayload, ChangePasswordPayload } from "@/types/user";

export function useAuth() {
    // Data user dinamis (nanti otomatis sinkron dengan Supabase / FastAPI)
    const [user, setUser] = useState<UserProfile | null>({
        id: "usr-7721",
        name: "Tony Robert",
        email: "tony.robert@analisis.id",
        avatar_url: "",
        role: "USER",
        is_active: true,
        total_detections: 42,
        total_feedbacks: 7,
        created_at: "2026-03-15T08:00:00Z",
    });

    const [isGuest, setIsGuest] = useState<boolean>(false);
    const [loading, setLoading] = useState<boolean>(false);

    // Fungsi Update Profil
    const updateProfile = async (payload: UpdateProfilePayload) => {
        setLoading(true);
        try {
            // Simulasi PATCH /api/v1/user/profile
            setUser((prev) => prev ? { ...prev, name: payload.name, email: payload.email } : null);
            return { success: true, message: "Profil berhasil diperbarui" };
        } catch {
            return { success: false, message: "Gagal memperbarui profil" };
        } finally {
            setLoading(false);
        }
    };

    // Fungsi Ganti Password
    const changePassword = async (payload: ChangePasswordPayload) => {
        setLoading(true);
        try {
            if (payload.new_password !== payload.confirm_password) {
                throw new Error("Konfirmasi kata sandi tidak cocok.");
            }
            return { success: true, message: "Kata sandi berhasil diubah." };
        } catch (err: any) {
            return { success: false, message: err.message || "Gagal mengganti kata sandi." };
        } finally {
            setLoading(false);
        }
    };

    // Fungsi Hapus Akun
    const deleteAccount = async () => {
        setLoading(true);
        try {
            setUser(null);
            setIsGuest(true);
            return { success: true };
        } finally {
            setLoading(false);
        }
    };

    const logout = () => {
        setUser(null);
        setIsGuest(true);
    };

    return {
        user,
        isGuest,
        loading,
        updateProfile,
        changePassword,
        deleteAccount,
        logout,
    };
}