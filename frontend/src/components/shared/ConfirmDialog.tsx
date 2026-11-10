"use client";

import { AlertTriangle } from "lucide-react";

interface ConfirmDialogProps {
    open: boolean;
    title: string;
    description: string;
    confirmLabel?: string;
    cancelLabel?: string;
    pending?: boolean;
    error?: string | null;
    onConfirm: () => void;
    onCancel: () => void;
}

export default function ConfirmDialog({
    open,
    title,
    description,
    confirmLabel = "Konfirmasi",
    cancelLabel = "Batal",
    pending = false,
    error = null,
    onConfirm,
    onCancel,
}: ConfirmDialogProps) {
    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
            <div role="dialog" aria-modal="true" aria-label={title} aria-busy={pending} className="bg-white rounded-2xl max-w-sm w-full p-5 shadow-xl border border-slate-200 animate-in fade-in zoom-in-95 space-y-4">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center shrink-0 border border-rose-100">
                        <AlertTriangle className="w-5 h-5" />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-slate-800">{title}</h3>
                        <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
                    </div>
                </div>

                {error && <p role="alert" className="text-xs text-rose-700">{error}</p>}
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                    <button
                        type="button"
                        onClick={onCancel}
                        disabled={pending}
                        className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition"
                    >
                        {cancelLabel}
                    </button>
                    <button
                        type="button"
                        onClick={onConfirm}
                        disabled={pending}
                        className="px-4 py-2 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-xs transition"
                    >
                        {pending ? "Menghapus..." : confirmLabel}
                    </button>
                </div>
            </div>
        </div>
    );
}
