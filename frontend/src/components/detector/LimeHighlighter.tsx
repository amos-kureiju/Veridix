"use client";

import { LimeToken } from "@/types/detector";

interface LimeHighlighterProps {
    tokens?: LimeToken[];
    topHoax?: Array<{ word: string; score: number }>;
    topFact?: Array<{ word: string; score: number }>;
}

export default function LimeHighlighter({ tokens = [], topHoax = [], topFact = [] }: LimeHighlighterProps) {
    if (!tokens || tokens.length === 0) {
        return (
            <p className="text-xs text-slate-400 italic">
                Data penjelasan lokal LIME tidak tersedia untuk inferensi ini.
            </p>
        );
    }

    return (
        <div className="space-y-4">
            {/* 1. Teks Berwarna Dinamis */}
            <div className="p-3.5 bg-slate-50 border border-slate-200/70 rounded-xl leading-relaxed text-xs sm:text-sm text-slate-700 font-sans max-h-48 overflow-y-auto">
                {tokens.map((item, idx) => {
                    let styleClass = "";
                    if (item.influence === "hoax") {
                        styleClass = "bg-rose-100 text-rose-800 font-medium px-1 py-0.5 rounded border border-rose-200 mx-0.5";
                    } else if (item.influence === "fact") {
                        styleClass = "bg-emerald-100 text-emerald-800 font-medium px-1 py-0.5 rounded border border-emerald-200 mx-0.5";
                    }
                    return (
                        <span key={idx} className={styleClass}>
                            {item.word}{" "}
                        </span>
                    );
                })}
            </div>

            {/* 2. Legenda Warna */}
            <div className="flex items-center gap-4 text-[11px] text-slate-500 font-medium">
                <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" /> Pendorong Hoaks
                </span>
                <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Pendorong Fakta
                </span>
            </div>

            {/* 3. Bar Chart Bobot Terbesar */}
            {(topHoax.length > 0 || topFact.length > 0) && (
                <div className="pt-2 border-t border-slate-100">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                        Bobot Kata Paling Berpengaruh (Top Weights):
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {/* Kolom Hoaks */}
                        <div className="space-y-1.5">
                            {topHoax.slice(0, 3).map((w, i) => (
                                <div key={i} className="flex items-center justify-between text-xs bg-rose-50/60 px-2 py-1 rounded-lg border border-rose-100">
                                    <span className="font-semibold text-rose-700 truncate max-w-[100px]">{w.word}</span>
                                    <span className="text-[10px] font-mono text-rose-600 font-bold">+{w.score.toFixed(3)}</span>
                                </div>
                            ))}
                        </div>

                        {/* Kolom Fakta */}
                        <div className="space-y-1.5">
                            {topFact.slice(0, 3).map((w, i) => (
                                <div key={i} className="flex items-center justify-between text-xs bg-emerald-50/60 px-2 py-1 rounded-lg border border-emerald-100">
                                    <span className="font-semibold text-emerald-700 truncate max-w-[100px]">{w.word}</span>
                                    <span className="text-[10px] font-mono text-emerald-600 font-bold">-{Math.abs(w.score).toFixed(3)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}