"use client";

import { useAdminDashboard } from "@/hooks/useAdminDashboard";
import ThresholdSlider from "@/components/admin/ThresholdSlider";

export default function AdminThresholdPage() {
    const { threshold, updateThreshold } = useAdminDashboard();

    return (
        <div className="space-y-6 pb-6">
            <div>
                <h2 className="text-xl font-bold tracking-tight text-slate-900">Kontrol Threshold Sensitivitas AI</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                    Modifikasi batas toleransi keyakinan model secara langsung tanpa perlu melakukan restart backend server.
                </p>
            </div>

            <ThresholdSlider currentValue={threshold} onSave={updateThreshold} />
        </div>
    );
}