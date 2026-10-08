"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/apiClient";
import type { GlobalStats, AdminLogItem, ThresholdConfig } from "@/types/admin";

export function useAdminDashboard() {
    const [stats, setStats] = useState<GlobalStats>({
        total_detections_today: 1248,
        total_detections_delta: 14.5,
        hoax_detected_today: 412,
        hoax_ratio_percent: 33.0,
        pending_feedbacks: 8,
        active_threshold: 0.50,
        active_users_count: 89,
    });

    const [recentLogs, setRecentLogs] = useState<AdminLogItem[]>([]);
    const [threshold, setThreshold] = useState<number>(0.50);
    const [loading, setLoading] = useState<boolean>(false);

    // Ambil data statistik dari FastAPI
    const fetchDashboardData = useCallback(async () => {
        setLoading(true);
        try {
            const resStats = await apiClient.get<GlobalStats>("/api/v1/admin/stats");
            setStats(resStats.data);
            const resLogs = await apiClient.get<AdminLogItem[]>("/api/v1/admin/logs/recent");
            setRecentLogs(resLogs.data);
        } catch {
            // Fallback data simulasi jika server belum menyalakan rute admin
            setRecentLogs([
                {
                    id: "LOG-9921",
                    user_identifier: "tamu · 182.253.11.90",
                    text_snippet: "KPU RI diklaim menggunakan server luar negeri untuk memanipulasi rekapitulasi suara...",
                    political_topic: "KPU & Pemilu",
                    prediction: "HOAKS",
                    confidence_score: 0.942,
                    inference_time: 0.38,
                    created_at: new Date().toISOString(),
                },
                {
                    id: "LOG-9920",
                    user_identifier: "tony.robert@analisis.id",
                    text_snippet: "Presiden RI meresmikan paket stimulus perlindungan pangan bagi masyarakat rentan...",
                    political_topic: "Kebijakan & Bansos",
                    prediction: "FAKTA",
                    confidence_score: 0.895,
                    inference_time: 0.41,
                    created_at: new Date(Date.now() - 3600000).toISOString(),
                },
                {
                    id: "LOG-9919",
                    user_identifier: "claribel.sefira@mail.com",
                    text_snippet: "DPR RI mengumumkan rencana rapat dengar pendapat umum bersama perwakilan ormas...",
                    political_topic: "DPR & Parlemen",
                    prediction: "FAKTA",
                    confidence_score: 0.781,
                    inference_time: 0.35,
                    created_at: new Date(Date.now() - 7200000).toISOString(),
                },
            ]);
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
            setStats((prev) => ({ ...prev, active_threshold: newValue }));
            return { success: true };
        } catch {
            setThreshold(newValue); // fallback lokal
            return { success: true, message: "Tersimpan secara lokal (Mode Pratinjau)" };
        }
    };

    return {
        stats,
        recentLogs,
        threshold,
        loading,
        updateThreshold,
        reload: fetchDashboardData,
    };
}