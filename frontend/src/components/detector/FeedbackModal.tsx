"use client";

import { useState } from "react";
import { X, CheckCircle, XCircle } from "lucide-react";

interface FeedbackModalProps {
    onClose: () => void;
    onSubmit: (claimedVerdict: "HOAKS" | "FAKTA", note: string) => void;
}

export default function FeedbackModal({ onClose, onSubmit }: FeedbackModalProps) {
    const [claim, setClaim] = useState<"HOAKS" | "FAKTA">("HOAKS");
    const [note, setNote] = useState("");

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 animate-in fade-in zoom-in-95">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <h3 className="text-sm font-bold text-slate-800">Koreksi Penilaian Model (Feedback)</h3>
                    <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <p className="text-xs text-slate-500 mt-3 leading-relaxed">
                    Bantu kami menyempurnakan model IndoBERT. Menurut penilaian Anda, apa label yang sebenarnya untuk berita ini?
                </p>

                {/* Pilihan Dua Tombol Besar */}
                <div className="grid grid-cols-2 gap-3 mt-4">
                    <button
                        type="button"
                        onClick={() => setClaim("HOAKS")}
                        className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-bold transition ${claim === "HOAKS"
                                ? "bg-rose-50 border-rose-400 text-rose-700 ring-2 ring-rose-200"
                                : "border-slate-200 text-slate-600 hover:bg-slate-50"
                            }`}
                    >
                        <XCircle className="w-4 h-4 text-rose-500" />
                        Menurut saya HOAKS
                    </button>

                    <button
                        type="button"
                        onClick={() => setClaim("FAKTA")}
                        className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-bold transition ${claim === "FAKTA"
                                ? "bg-emerald-50 border-emerald-400 text-emerald-700 ring-2 ring-emerald-200"
                                : "border-slate-200 text-slate-600 hover:bg-slate-50"
                            }`}
                    >
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        Menurut saya FAKTA
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
                        placeholder="Misal: Berita ini sudah diklarifikasi resmi oleh KPU pada..."
                        className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-800 focus:outline-none focus:border-emerald-500 transition"
                    />
                </div>

                {/* Tombol Kirim */}
                <div className="mt-5 flex gap-2 justify-end">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition"
                    >
                        Batal
                    </button>
                    <button
                        type="button"
                        onClick={() => onSubmit(claim, note)}
                        className="px-5 py-2 text-xs font-semibold bg-[#0b2520] hover:bg-[#133730] text-white rounded-xl transition shadow-xs"
                    >
                        Kirim Masukan
                    </button>
                </div>
            </div>
        </div>
    );
}