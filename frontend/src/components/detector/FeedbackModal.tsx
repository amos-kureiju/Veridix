"use client";

import { useEffect, useRef, useState } from "react";
import { isAxiosError } from "axios";
import { getApiConnectionMessage } from "@/lib/apiClient";
import { X, CheckCircle, XCircle } from "lucide-react";

interface FeedbackModalProps {
    onClose: () => void;
    onSubmit: (claimedVerdict: "BERPOLA HOAKS" | "TIDAK BERPOLA HOAKS", note: string) => Promise<void>;
}

export default function FeedbackModal({ onClose, onSubmit }: FeedbackModalProps) {
    const [claim, setClaim] = useState<"BERPOLA HOAKS" | "TIDAK BERPOLA HOAKS">("BERPOLA HOAKS");
    const [note, setNote] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const busyRef = useRef(false);
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;
        return () => { mountedRef.current = false; };
    }, []);

    const close = () => { if (!busyRef.current) onClose(); };
    const submit = async () => {
        if (busyRef.current || !mountedRef.current) return;
        if (note.length > 1000) {
            setError("Catatan maksimal 1000 karakter.");
            return;
        }
        busyRef.current = true;
        setSubmitting(true);
        setError(null);
        try {
            await onSubmit(claim, note);
        } catch (err: unknown) {
            if (!mountedRef.current) return;
            const detail = isAxiosError<{ detail?: string | Array<{ msg?: string }> }>(err)
                ? err.response?.data?.detail : undefined;
            const validationMessage = Array.isArray(detail)
                ? detail.map(item => item?.msg).filter(msg => typeof msg === "string" && msg).join(", ")
                : typeof detail === "string" ? detail : null;
            setError(getApiConnectionMessage(err) || validationMessage || "Umpan balik gagal dikirim. Coba lagi.");
        } finally {
            busyRef.current = false;
            if (mountedRef.current) setSubmitting(false);
        }
    };

    return (
        <div role="dialog" aria-modal="true" aria-labelledby="feedback-title" className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 animate-in fade-in zoom-in-95">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <h3 id="feedback-title" className="text-sm font-bold text-slate-800">Koreksi Penilaian Model (Feedback)</h3>
                    <button type="button" aria-label="Tutup umpan balik" onClick={close} disabled={submitting} className="text-slate-400 hover:text-slate-600 disabled:opacity-40">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <p className="text-xs text-slate-500 mt-3 leading-relaxed">
                    Bantu kami mengevaluasi model IndoBERT. Menurut penilaian Anda, pola mana yang lebih sesuai untuk teks ini?
                </p>

                {/* Pilihan Dua Tombol Besar */}
                <div className="grid grid-cols-2 gap-3 mt-4">
                    <button
                        type="button"
                        onClick={() => setClaim("BERPOLA HOAKS")}
                        disabled={submitting}
                        className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-bold transition disabled:opacity-40 ${claim === "BERPOLA HOAKS"
                                ? "bg-rose-50 border-rose-400 text-rose-700 ring-2 ring-rose-200"
                                : "border-slate-200 text-slate-600 hover:bg-slate-50"
                            }`}
                    >
                        <XCircle className="w-4 h-4 text-rose-500" />
                        Menurut saya BERPOLA HOAKS
                    </button>

                    <button
                        type="button"
                        onClick={() => setClaim("TIDAK BERPOLA HOAKS")}
                        disabled={submitting}
                        className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-bold transition disabled:opacity-40 ${claim === "TIDAK BERPOLA HOAKS"
                                ? "bg-emerald-50 border-emerald-400 text-emerald-700 ring-2 ring-emerald-200"
                                : "border-slate-200 text-slate-600 hover:bg-slate-50"
                            }`}
                    >
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        Menurut saya TIDAK BERPOLA HOAKS
                    </button>
                </div>

                {/* Input Catatan Opsional */}
                <div className="mt-4">
                    <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                        Catatan Sanggahan / Sumber Referensi (Opsional):
                    </label>
                    <textarea
                        rows={3}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        maxLength={1000}
                        disabled={submitting}
                        placeholder="Misal: Berita ini sudah diklarifikasi resmi oleh KPU pada..."
                        className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-800 focus:outline-none focus:border-emerald-500 transition"
                    />
                </div>
                {error && <p role="alert" className="mt-3 text-xs text-rose-600">{error}</p>}

                {/* Tombol Kirim */}
                <div className="mt-5 flex gap-2 justify-end">
                    <button
                        type="button"
                        onClick={close}
                        disabled={submitting}
                        className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition disabled:opacity-40"
                    >
                        Batal
                    </button>
                    <button
                        type="button"
                        onClick={submit}
                        disabled={submitting}
                        className="px-5 py-2 text-xs font-semibold bg-[#0b2520] hover:bg-[#133730] text-white rounded-xl transition shadow-xs disabled:opacity-40"
                    >
                        {submitting ? "Mengirim..." : "Kirim Masukan"}
                    </button>
                </div>
            </div>
        </div>
    );
}
