"use client";

import { useAdminDashboard } from "@/hooks/useAdminDashboard";
import GlobalLogsTable from "@/components/admin/GlobalLogsTable";

export default function AdminLogsPage() {
    const { recentLogs, loading } = useAdminDashboard();

    return (
        <div className="space-y-6 pb-6">
            <div>
                <h2 className="text-xl font-bold tracking-tight text-slate-900">Audit Log Deteksi Global</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                    Seluruh rekaman inferensi teks dan gambar politik dari sesi pengguna terdaftar dan tamu.
                </p>
            </div>

            <GlobalLogsTable logs={recentLogs} />
        </div>
    );
}