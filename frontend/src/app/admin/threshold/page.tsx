"use client";

import { useAdminDashboard } from "@/hooks/useAdminDashboard";
import ThresholdSlider from "@/components/admin/ThresholdSlider";

export default function AdminThresholdPage() {
    const { threshold, updateThreshold, recentLogs } = useAdminDashboard();

    return (
        <div className="space-y-6 pb-6">
            <div className="flex items-start gap-3">
                <span className="mt-1 h-9 w-1 rounded-full bg-emerald-600" />
                <div>
                    <h2 className="text-xl font-bold tracking-tight text-slate-900">Kontrol Threshold Sensitivitas AI</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                        Modifikasi batas toleransi keyakinan model secara langsung tanpa perlu melakukan restart backend server.
                    </p>
                </div>
            </div>

            <ThresholdSlider currentValue={threshold} onSave={updateThreshold} logs={recentLogs} />
        </div>
    );
}