"use client";

import { useEffect, useState } from "react";
import { isAxiosError } from "axios";
import { Loader2, LockKeyhole, RefreshCw } from "lucide-react";
import { apiClient } from "@/lib/apiClient";

interface ThresholdResponse {
    status: string;
    data: {
        threshold: number;
        editable: boolean;
        note?: string;
    };
}

interface ThresholdSettings {
    threshold: number;
    note: string | null;
}

export default function AdminThresholdPage() {
    const [settings, setSettings] = useState<ThresholdSettings | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reloadVersion, setReloadVersion] = useState(0);

    useEffect(() => {
        const controller = new AbortController();
        setLoading(true);
        setError(null);
        setSettings(null);

        const loadThreshold = async () => {
            try {
                const response = await apiClient.get<ThresholdResponse>(
                    "/api/v1/admin/threshold",
                    { signal: controller.signal },
                );
                if (controller.signal.aborted) return;

                const data = response.data?.data;
                if (
                    response.data?.status !== "success" ||
                    typeof data?.threshold !== "number" ||
                    !Number.isFinite(data.threshold) ||
                    data.threshold < 0 || data.threshold > 1 ||
                    data.editable !== false
                ) {
                    throw new Error("Invalid threshold configuration");
                }

                setSettings({
                    threshold: data.threshold,
                    note: typeof data.note === "string" ? data.note : null,
                });
            } catch (err: unknown) {
                if (controller.signal.aborted) return;
                const detail = isAxiosError<{ detail?: unknown }>(err)
                    ? err.response?.data?.detail
                    : undefined;
                setError(
                    typeof detail === "string" && detail.trim()
                        ? detail
                        : "Konfigurasi ambang belum dapat dimuat. Coba lagi.",
                );
            } finally {
                if (!controller.signal.aborted) setLoading(false);
            }
        };

        void loadThreshold();
        return () => controller.abort();
    }, [reloadVersion]);

    return (
        <div className="space-y-6 pb-6">
            <div className="flex items-start gap-3">
                <span className="mt-1 h-9 w-1 rounded-full bg-emerald-600" />
                <div>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">Ambang Keputusan Model</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                        Konfigurasi aktif model beku.
                    </p>
                </div>
            </div>

            <div className="space-y-5 rounded-3xl border border-slate-200/80 bg-white p-6 shadow-2xs sm:p-8">
                <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-4">
                    <h3 className="text-sm font-bold text-slate-900">Ambang per seed</h3>
                    <button
                        type="button"
                        onClick={() => setReloadVersion(value => value + 1)}
                        disabled={loading}
                        className="flex items-center gap-1.5 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800 transition hover:bg-emerald-100 disabled:opacity-50"
                    >
                        <RefreshCw className="h-3.5 w-3.5" />
                        {error ? "Coba lagi" : "Muat ulang"}
                    </button>
                </div>

                {loading ? (
                    <p role="status" className="flex items-center gap-2 text-sm text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Memuat konfigurasi ambang...
                    </p>
                ) : error ? (
                    <p role="alert" className="text-sm text-rose-700">{error}</p>
                ) : settings ? (
                    <>
                        <div className="flex items-center gap-3">
                            <span className="font-mono text-5xl font-extrabold tracking-tight text-slate-900">
                                {settings.threshold.toFixed(2)}
                            </span>
                            <span className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600">
                                <LockKeyhole className="h-3.5 w-3.5" />
                                Hanya baca
                            </span>
                        </div>
                        {settings.note && <p className="text-sm text-slate-600">{settings.note}</p>}
                        <p className="text-xs leading-relaxed text-slate-500">
                            Ambang ini menentukan suara tiap seed. Keputusan akhir mengikuti aturan voting antar-seed.
                            Perubahan ambang melalui panel admin dinonaktifkan.
                        </p>
                    </>
                ) : null}
            </div>
        </div>
    );
}
