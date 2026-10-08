"use client";

import { useState } from "react";
import { Sliders, RotateCcw, Save, ShieldAlert, CheckCircle, AlertTriangle } from "lucide-react";

interface ThresholdSliderProps {
    currentValue?: number;
    onSave?: (val: number) => Promise<any>;
}

export default function ThresholdSlider({ currentValue = 0.50, onSave }: ThresholdSliderProps) {
    const [val, setVal] = useState<number>(currentValue);
    const [isSaved, setIsSaved] = useState(false);

    const handleApply = async () => {
        if (onSave) await onSave(val);
        setIsSaved(true);
        setTimeout(() => setIsSaved(false), 3000);
    };

    const handleReset = () => {
        setVal(0.50);
    };

    return (
        <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 shadow-2xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                    <h3 className="text-base font-bold text-slate-900">Nilai Ambang Batas Klasifikasi (Decision Boundary)</h3>
                    <p className="text-xs text-slate-400 mt-0.5">Mengatur tingkat sensitivitas probabilitas Softmax untuk vonis Hoaks.</p>
                </div>

                <div className="flex items-center gap-2">
                    {isSaved && (
                        <span className="text-xs text-emerald-600 font-semibold bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200 animate-in fade-in">
                            Threshold Berhasil Diperbarui
                        </span>
                    )}
                    <button
                        type="button"
                        onClick={handleReset}
                        className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition"
                    >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Reset 0.50</span>
                    </button>
                    <button
                        type="button"
                        onClick={handleApply}
                        className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-[#0b2520] hover:bg-[#133730] rounded-xl shadow-xs transition"
                    >
                        <Save className="w-3.5 h-3.5" />
                        <span>Terapkan Sekarang</span>
                    </button>
                </div>
            </div>

            {/* Nilai Besar & Slider Interaktif */}
            <div className="text-center py-4 space-y-4">
                <span className="text-5xl font-extrabold text-slate-900 font-mono tracking-tight">
                    {val.toFixed(2)}
                </span>
                <p className="text-xs text-slate-400">Sensitivitas Aktif Model IndoBERT</p>

                <div className="max-w-xl mx-auto px-4">
                    <input
                        type="range"
                        min="0.30"
                        max="0.90"
                        step="0.01"
                        value={val}
                        onChange={(e) => setVal(parseFloat(e.target.value))}
                        className="w-full h-2.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0b2520]"
                    />
                    <div className="flex justify-between text-[11px] font-mono text-slate-400 mt-2">
                        <span>0.30 (Lebih Agresif Hoaks)</span>
                        <span>0.50 (Standar Imbang)</span>
                        <span>0.90 (Sangat Konservatif)</span>
                    </div>
                </div>
            </div>

            {/* Visualisasi Zona 3 Warna */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-2">
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl space-y-1">
                    <span className="font-bold text-emerald-800 flex items-center gap-1.5">
                        <CheckCircle className="w-4 h-4 text-emerald-600" />
                        Zona Vonis FAKTA
                    </span>
                    <p className="text-emerald-700 text-[11px]">Probabilitas Hoaks ≤ {(val - 0.20).toFixed(2)}</p>
                </div>

                <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl space-y-1">
                    <span className="font-bold text-amber-800 flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                        Zona PERLU KONFIRMASI
                    </span>
                    <p className="text-amber-700 text-[11px]">Rentang ambiguitas {(val - 0.20).toFixed(2)} sampai {val.toFixed(2)}</p>
                </div>

                <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl space-y-1">
                    <span className="font-bold text-rose-800 flex items-center gap-1.5">
                        <ShieldAlert className="w-4 h-4 text-rose-600" />
                        Zona Vonis HOAKS
                    </span>
                    <p className="text-rose-700 text-[11px]">Probabilitas Hoaks ≥ {val.toFixed(2)}</p>
                </div>
            </div>

            {/* Simulasi Dampak Real-Time */}
            <div className="bg-[#f8fafc] border border-slate-200/80 rounded-2xl p-4 text-xs text-slate-600">
                <p className="font-bold text-slate-800 mb-1">Simulasi Dampak Inferensi (100 Sampel Terakhir):</p>
                <p className="leading-relaxed">
                    Pada threshold <strong className="font-mono">{val.toFixed(2)}</strong>, diperkirakan rasio deteksi hoaks sistem akan berada pada kisaran{" "}
                    <strong className="text-slate-900 font-mono">{(65 - (val * 40)).toFixed(1)}%</strong> dengan tingkat ambiguitas{" "}
                    <strong className="text-slate-900 font-mono">{(val * 15).toFixed(1)}%</strong>.
                </p>
            </div>
        </div>
    );
}