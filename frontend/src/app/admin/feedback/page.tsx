"use client";

import RetrainTable from "@/components/admin/RetrainTable";

export default function AdminFeedbackPage() {
    return (
        <div className="space-y-6 pb-6">
            <div>
                <h2 className="text-xl font-bold tracking-tight text-slate-900">Kelola Masukan & Human Feedback</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                    Kurasi sanggahan masyarakat terhadap vonis IndoBERT untuk memperkaya dataset retraining (Active Learning).
                </p>
            </div>

            <RetrainTable />
        </div>
    );
}