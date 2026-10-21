"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/apiClient";
import type { GlobalStats, AdminLogItem } from "@/types/admin";

export function useAdminDashboard() {
    // Inisialisasi state awal bersih (tanpa angka palsu)
    const [stats, setStats] = useState<GlobalStats | null>(null);
    const [recentLogs, setRecentLogs] = useState<AdminLogItem[]>([]);
    const [threshold, setThreshold] = useState<number>(0.60);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // Ambil data statistik dari FastAPI
    const fetchDashboardData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const resStats = await apiClient.get<GlobalStats>("/api/v1/admin/stats");
            setStats(resStats.data);
            if (resStats.data.active_threshold !== undefined) {
                setThreshold(resStats.data.active_threshold);
            }
            const resLogs = await apiClient.get<AdminLogItem[]>("/api/v1/admin/logs/recent");
            setRecentLogs(resLogs.data || []);
        } catch (err: any) {
            const message = err.response?.data?.detail || "Gagal memuat data statistik dari server.";
            setError(message);
            // Bersihkan data log: jangan tampilkan log simulasi/rekaan
            setRecentLogs([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    // Update Threshold AI secara Real-Time
    const updateThreshold = async (newValue: number) => {
        try {
            await apiClient.post("/api/v1/admin/threshold", { threshold: newValue });
            setThreshold(newValue);
            setStats((prev) => (prev ? { ...prev, active_threshold: newValue } : null));
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
