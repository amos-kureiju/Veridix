"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/apiClient";
import RetrainTable from "@/components/admin/RetrainTable";
import { AdminFeedbackItem } from "@/types/admin";
import { Loader2, RefreshCw } from "lucide-react";

export default function AdminFeedbackPage() {
    const [feedbacks, setFeedbacks] = useState<AdminFeedbackItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await apiClient.get<any>("/api/v1/admin/feedbacks");
            const raw = res.data?.data || res.data;
            setFeedbacks(Array.isArray(raw) ? raw : []);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Gagal memuat antrean masukan kurasi.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold text-slate-900">Kurasi Sanggahan & Korpus Retraining</h2>
                    <p className="text-xs text-slate-500 mt-1">
                        Tinjau masukan pengguna untuk divalidasi sebagai korpus pelatihan model IndoBERT berikutnya.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={loadData}
                    disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50 transition cursor-pointer"
                >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    <span>Segarkan Data</span>
                </button>
            </div>

            {error ? (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-700">
                    {error}
                </div>
            ) : loading && feedbacks.length === 0 ? (
                <div className="p-12 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-2">
                    <Loader2 className="w-5 h-5 text-emerald-600 animate-spin" />
                    <span>Memuat data sanggahan nyata dari server...</span>
                </div>
            ) : (
                <RetrainTable initialItems={feedbacks} onRefresh={loadData} />
            )}
        </div>
    );
}