"use client";
import { useEffect, useState } from "react";
import { apiClient as api } from "@/lib/apiClient";
import type { HistoryItem } from "@/types/detector";

export function useHistory(enabled: boolean) {
    const [items, setItems] = useState<HistoryItem[]>([]);
    const [q, setQ] = useState("");
    const [topic, setTopic] = useState("");
    const [loading, setLoading] = useState(false);
    const [nonce, setNonce] = useState(0);

    useEffect(() => {
        if (!enabled) return;
        setLoading(true);
        const p = new URLSearchParams();
        if (q) p.set("q", q);
        if (topic) p.set("topic", topic);
        const t = setTimeout(
            () => api.get<HistoryItem[]>(`/api/history?${p}`).then(setItems).catch(() => setItems([])).finally(() => setLoading(false)),
            250
        );
        return () => clearTimeout(t);
    }, [enabled, q, topic, nonce]);

    const remove = async (id: string) => {
        await api.post(`/api/history/${id}/delete`, {});
        setItems((l) => l.filter((i) => i.id !== id));
    };
    const reload = () => setNonce((n) => n + 1);

    return { items, loading, q, setQ, topic, setTopic, remove, reload };
}