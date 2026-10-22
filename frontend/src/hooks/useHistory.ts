"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient as api } from "@/lib/apiClient";
import type { HistoryItem } from "@/types/detector";

export function useHistory(enabled: boolean) {
    const [items, setItems] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null); 

    const fetchHistory = useCallback(async () => {
        // Jika tidak aktif (misal user belum login / tamu), bersihkan data
        if (!enabled) {
            setItems([]);
            setError(null);
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const res = await api.get<any>("/api/v1/users/history");
            // 2. Pembacaan array secara aman
            const rawData = res.data?.data ?? res.data;
            const historyList: HistoryItem[] = Array.isArray(rawData) ? rawData : [];
            setItems(historyList);
        } catch (err: any) {
            // 3. Catat pesan error agar UI tahu ini kegagalan request, bukan riwayat kosong
            const message = err.response?.data?.detail || "Gagal memuat riwayat deteksi dari server.";
            setError(message);
            setItems([]);
        } finally {
            setLoading(false);
        }
    }, [enabled]);

    useEffect(() => {
        fetchHistory();
    }, [fetchHistory]);

    return {
        items,
        loading,
        error,                                      // Ekspor status error
        isEmpty: !loading && !error && items.length === 0, // Flag praktis untuk UI
        reload: fetchHistory,
    };
}