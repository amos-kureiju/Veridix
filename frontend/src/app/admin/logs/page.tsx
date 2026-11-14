"use client";

import { useAdminDashboard } from "@/hooks/useAdminDashboard";
import GlobalLogsTable from "@/components/admin/GlobalLogsTable";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function AdminLogsPage() {
    // 1. PERBAIKAN: Ambil logsError dan reload dari hook
    const { recentLogs, loading, logsError, reload } = useAdminDashboard();

    return (
        <div className="space-y-6 pb-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">Audit Log Deteksi Global</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                        Seluruh rekaman inferensi teks dan gambar politik dari sesi pengguna terdaftar dan tamu.
                    </p>
                </div>

                {/* Tombol refresh data */}
                <button
                    type="button"
                    onClick={() => reload()}
                    disabled={loading}
                    className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50 transition cursor-pointer disabled:opacity-50"
                >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    <span>Segarkan</span>
                </button>
            </div>

            {/* 2. PERBAIKAN: Tampilkan pesan error transparan jika log gagal dimuat */}
            {logsError ? (
                <div className="bg-rose-50 border border-rose-200/80 rounded-2xl p-4 text-xs text-rose-800 flex items-center justify-between shadow-2xs">
                    <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                        <span><strong>Gagal memuat log audit:</strong> {logsError}</span>
                    </div>
                    <button
                        type="button"
                        onClick={() => reload()}
                        className="font-bold underline hover:text-rose-950 cursor-pointer ml-3 shrink-0"
                    >
                        Coba Lagi
                    </button>
                </div>
            ) : (
                <GlobalLogsTable logs={recentLogs} />
            )}
        </div>
    );
}