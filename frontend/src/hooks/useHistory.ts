"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient as api } from "@/lib/apiClient";
import type { HistoryItem } from "@/types/detector";

export function useHistory(enabled: boolean) {
    const [items, setItems] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState<boolean>(false);

    const fetchHistory = useCallback(async () => {
        if (!enabled) return;
        setLoading(true);
        try {
            const res = await api.get("/api/v1/history");
            setItems(res.data || []);
        } catch {
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
        reload: fetchHistory,
    };
}