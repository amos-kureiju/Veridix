"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/apiClient";
import type { GlobalStats, AdminLogItem } from "@/types/admin";

export function useAdminDashboard() {
    // Inisialisasi state awal bersih (tanpa angka palsu)
    const [stats, setStats] = useState<GlobalStats | null>(null);
    const [recentLogs, setRecentLogs] = useState<AdminLogItem[]>([]);
    const [threshold, setThreshold] = useState<number | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // Ambil data statistik dari FastAPI
    // Ambil data statistik dari FastAPI
    const fetchDashboardData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // 1. Ambil Statistik Utama (Buka bungkusan resStats.data.data jika ada)
            const resStats = await apiClient.get<any>("/api/v1/admin/stats");
            const statsData = resStats.data?.data || resStats.data;
            setStats(statsData);

            const activeThreshold = statsData?.active_threshold;
            setThreshold(
                typeof activeThreshold === "number" && Number.isFinite(activeThreshold) && activeThreshold >= 0 && activeThreshold <= 1
                    ? activeThreshold
                    : null
            );

            // 2. Ambil Log Terkini (Pisahkan try-catch agar jika log 404, statistik dashboard tetap tampil)
            try {
                const resLogs = await apiClient.get<any>("/api/v1/admin/logs/recent");
                const logsData = resLogs.data?.data || resLogs.data;
                setRecentLogs(Array.isArray(logsData) ? logsData : []);
            } catch {
                setRecentLogs([]); // Fallback log kosong jika endpoint belum siap
            }

        } catch (err: any) {
            const message = err.response?.data?.detail || "Gagal memuat data statistik dari server.";
            setError(message);
            setRecentLogs([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    // Update Threshold AI (Gunakan PUT dan new_threshold sesuai schema backend)
    const updateThreshold = async (newValue: number) => {
        try {
            await apiClient.put("/api/v1/admin/threshold", { new_threshold: newValue });
            setThreshold(newValue);
            setStats((prev: any) => (prev ? { ...prev, active_threshold: newValue } : null));
            return { success: true, message: "Threshold AI berhasil diperbarui ke server." };
        } catch (err: any) {
            const message = err.response?.data?.detail || "Gagal menyimpan perubahan threshold ke server.";
            return { success: false, message };
        }
    };

    return {
        stats,
        recentLogs,
        threshold,
        loading,
        error,
        updateThreshold,
        reload: fetchDashboardData,
    };
}
