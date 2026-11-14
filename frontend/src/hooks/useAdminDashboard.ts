"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/apiClient";
import type { GlobalStats, AdminLogItem } from "@/types/admin";

export function useAdminDashboard() {
    const [stats, setStats] = useState<GlobalStats | null>(null);
    const [recentLogs, setRecentLogs] = useState<AdminLogItem[]>([]);
    const [threshold, setThreshold] = useState<number | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // --- PERBAIKAN AUDIT: Pisahkan status error pengambilan log ---
    const [logsError, setLogsError] = useState<string | null>(null);

    const fetchDashboardData = useCallback(async () => {
        setLoading(true);
        setError(null);
        setLogsError(null);

        try {
            // 1. Ambil Statistik Utama
            const resStats = await apiClient.get<any>("/api/v1/admin/stats");
            const statsData = resStats.data?.data || resStats.data;
            setStats(statsData);

            const activeThreshold = statsData?.active_threshold;
            setThreshold(
                typeof activeThreshold === "number" &&
                    Number.isFinite(activeThreshold) &&
                    activeThreshold >= 0 &&
                    activeThreshold <= 1
                    ? activeThreshold
                    : null
            );

            // 2. Ambil Log Terkini (Validasi kontrak array ketat & pesan error jaringan riil)
            try {
                const resLogs = await apiClient.get<any>("/api/v1/admin/logs/recent");
                const logsData = resLogs.data?.data ?? resLogs.data;

                if (Array.isArray(logsData)) {
                    setRecentLogs(logsData);
                } else {
                    // Jangan samarkan sebagai data kosong jika format server keliru
                    setLogsError("Format data log dari server tidak valid (diharapkan array).");
                    setRecentLogs([]);
                }
            } catch (err: any) {
                // Tangkap detail backend atau pesan jaringan (misal: "Network Error" jika server mati)
                const logErrMessage =
                    err.response?.data?.detail ||
                    err.message ||
                    "Gagal memuat log aktivitas terkini dari server.";
                setLogsError(logErrMessage);
                setRecentLogs([]);
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
        logsError, // Ditampilkan ke UI agar kegagalan log transparan
        updateThreshold,
        reload: fetchDashboardData,
    };
}