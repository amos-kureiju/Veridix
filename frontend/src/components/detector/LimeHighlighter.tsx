"use client";

import { LimeToken } from "@/types/detector";
import { HelpCircle, Sparkles, TrendingUp, TrendingDown, Info, ShieldAlert, CheckCircle2 } from "lucide-react";

interface LimeHighlighterProps {
    tokens?: LimeToken[];
    topHoax?: Array<{ word: string; score: number }>;
    topFact?: Array<{ word: string; score: number }>;
    prediction?: string;
    confidenceScore?: number;
}

export default function LimeHighlighter({
    tokens = [],
    topHoax = [],
    topFact = [],
    prediction = "HOAKS",
    confidenceScore = 0.934
}: LimeHighlighterProps) {
    if (!tokens || tokens.length === 0) {
        return (
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 text-xs text-slate-400 italic">
                Data penjelasan lokal LIME belum tersedia untuk sampel ini.
            </div>
        );
    }

    const isHoaxVerdict = prediction === "HOAKS";

    return (
        <div className="space-y-4 font-sans">

            {/* GRID DUA KOLOM BERDAMPINGAN: VISUAL LIME (KIRI) vs EDUKASI/REASONING (KANAN) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">

                {/* ========================================================= */}
                {/* SISI KIRI (7 KOLOM): TEKS BERWARNA & BARIS BOBOT          */}
                {/* ========================================================= */}
                <div className="lg:col-span-7 bg-[#f8fafc] border border-slate-200/80 rounded-2xl p-4 flex flex-col justify-between space-y-3">
                    <div>
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-200/60 text-[11px] font-bold text-slate-500">
                            <span>Sebaran Kata Berpengaruh (Token Highlights)</span>
                            <span className="text-[10px] text-slate-400 font-mono">100 Perturbasi</span>
                        </div>

                        {/* Kotak Teks Highlight Kata */}
                        <div className="p-3 bg-white border border-slate-200/60 rounded-xl leading-relaxed text-xs text-slate-800 max-h-48 overflow-y-auto shadow-2xs">
                            {tokens.map((item, idx) => {
                                let badgeStyle = "";
                                if (item.influence === "hoax") {
                                    badgeStyle = "bg-rose-100 text-rose-800 font-bold px-1 py-0.5 rounded border border-rose-200 mx-0.5 shadow-2xs";
                                } else if (item.influence === "fact") {
                                    badgeStyle = "bg-emerald-100 text-emerald-800 font-bold px-1 py-0.5 rounded border border-emerald-200 mx-0.5 shadow-2xs";
                                }
                                return (
                                    <span key={idx} className={badgeStyle}>
                                        {item.word}{" "}
                                    </span>
                                );
                            })}
                        </div>
                    </div>

                    {/* Legenda Warna Bawah */}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-200/60 text-[11px] text-slate-500">
                        <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                            <span>Merah: Mendorong Hoaks</span>
                        </span>
                        <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                            <span>Hijau: Mendorong Fakta</span>
                        </span>
                    </div>
                </div>

                {/* ========================================================= */}
                {/* SISI KANAN (5 KOLOM): KOTAK PENJELASAN "BAGAIMANA BISA TAHU?" */}
                {/* ========================================================= */}
                <div className="lg:col-span-5 bg-gradient-to-br from-slate-900 to-[#0b2520] text-white rounded-2xl p-4 flex flex-col justify-between shadow-xs border border-emerald-950">

                    <div className="space-y-3">
                        <div className="flex items-center gap-2 pb-2 border-b border-white/10">
                            <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
                            <h4 className="text-xs font-bold tracking-tight text-white">
                                Mengapa Hasil Ini Muncul?
                            </h4>
                        </div>

                        {/* Narasi Alasan Matematis */}
                        <p className="text-[11px] text-emerald-100/80 leading-relaxed">
                            {isHoaxVerdict ? (
                                <>
                                    Model IndoBERT mendeteksi <strong>pola retorika provokatif</strong>. LIME menemukan kata-kata berlatar <span className="text-rose-400 font-bold">merah</span> memberikan lonjakan bobot terbesar hingga memicu vonis <strong>HOAKS {(confidenceScore * 100).toFixed(1)}%</strong>.
                                </>
                            ) : (
                                <>
                                    Model mengidentifikasi <strong>struktur jurnalistik baku</strong>. Kata-kata bertanda <span className="text-emerald-400 font-bold">hijau</span> menetralkan kecurigaan dan mengonfirmasi pola <strong>FAKTA {(confidenceScore * 100).toFixed(1)}%</strong>.
                                </>
                            )}
                        </p>

                        {/* Kata Kunci Paling Berdampak */}
                        <div className="bg-white/10 border border-white/10 rounded-xl p-2.5 space-y-1.5">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-300 block">
                                Kata Paling Berpengaruh (Top Weight):
                            </span>

                            {isHoaxVerdict && topHoax.length > 0 ? (
                                <div className="space-y-1">
                                    {topHoax.slice(0, 2).map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-rose-300 font-mono font-bold truncate max-w-[100px]">"{w.word}"</span>
                                            <span className="text-rose-400 font-mono font-extrabold text-[10px]">+{w.score.toFixed(3)} pendorong hoaks</span>
                                        </div>
                                    ))}
                                </div>
                            ) : topFact.length > 0 ? (
                                <div className="space-y-1">
                                    {topFact.slice(0, 2).map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-emerald-300 font-mono font-bold truncate max-w-[100px]">"{w.word}"</span>
                                            <span className="text-emerald-400 font-mono font-extrabold text-[10px]">{w.score.toFixed(3)} pendorong fakta</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <span className="text-[10px] text-slate-300 italic">Distribusi kata seimbang.</span>
                            )}
                        </div>
                    </div>

                    {/* Catatan Transparansi XAI */}
                    <div className="pt-2 mt-2 border-t border-white/10 flex items-center gap-1.5 text-[10px] text-emerald-300/70">
                        <Info className="w-3 h-3 text-emerald-400 shrink-0" />
                        <span>Hasil diuji via perturbasi nyata, bukan kamus kata statis.</span>
                    </div>

                </div>

            </div>

            {/* ========================================================= */}
            {/* BAGIAN BAWAH: BAR CHART BOBOT KATA (GRAFIK NUMERIK LIME)   */}
            {/* ========================================================= */}
            {(topHoax.length > 0 || topFact.length > 0) && (
                <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-2xs space-y-3">
                    <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-100">
                        <span className="font-bold text-slate-800">Grafik Nilai Pengaruh Kata (Feature Importance Chart)</span>
                        <span className="text-[10px] text-slate-400">Nilai Bobot Positif (+) vs Negatif (-)</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {/* Kolom Pendorong Hoaks */}
                        <div className="space-y-2">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600 block">
                                Top Kata Mendorong Hoaks:
                            </span>
                            {topHoax.slice(0, 3).map((w, i) => (
                                <div key={i} className="space-y-1">
                                    <div className="flex justify-between text-[11px]">
                                        <span className="font-bold text-slate-700 font-mono">"{w.word}"</span>
                                        <span className="font-mono text-rose-600 font-extrabold">+{w.score.toFixed(3)}</span>
                                    </div>
                                    {/* Progress Bar Merah */}
                                    <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-rose-500 rounded-full"
                                            style={{ width: `${Math.min(100, Math.abs(w.score) * 200)}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Kolom Pendorong Fakta */}
                        <div className="space-y-2">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 block">
                                Top Kata Mendorong Fakta:
                            </span>
                            {topFact.slice(0, 3).map((w, i) => (
                                <div key={i} className="space-y-1">
                                    <div className="flex justify-between text-[11px]">
                                        <span className="font-bold text-slate-700 font-mono">"{w.word}"</span>
                                        <span className="font-mono text-emerald-600 font-extrabold">{w.score.toFixed(3)}</span>
                                    </div>
                                    {/* Progress Bar Hijau */}
                                    <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-emerald-500 rounded-full"
                                            style={{ width: `${Math.min(100, Math.abs(w.score) * 200)}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

        </div>
    );
}