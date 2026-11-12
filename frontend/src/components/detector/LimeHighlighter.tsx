"use client";

import { useMemo } from "react";
import { LimeToken } from "@/types/detector";
import { Sparkles, Info } from "lucide-react";

interface LimeHighlighterProps {
    tokens?: LimeToken[];
    topHoax?: Array<{ word: string; score: number }>;
    topFact?: Array<{ word: string; score: number }>;
    showChart?: boolean; topWordsCount?: 3 | 5 | 7;
    prediction?: string;
    confidenceScore?: number;
    numSamples?: number;
}

// Fungsi sanitasi angka ketat: tolak boolean, array, null, objek, dan string non-numerik
const parseWeightStrict = (raw: any): number => {
    if (typeof raw === "number") {
        return Number.isFinite(raw) ? raw : 0;
    }
    if (typeof raw === "string" && raw.trim() !== "") {
        const num = Number(raw.trim());
        return Number.isFinite(num) ? num : 0;
    }
    return 0; // Menolak boolean (true/false), array, null, objek
};

export default function LimeHighlighter({
    tokens = [], topHoax = [], topFact = [], prediction = "TIDAK BERPOLA HOAKS",
    confidenceScore, numSamples, showChart = true, topWordsCount = 3
}: LimeHighlighterProps) {
    const wordLimit = topWordsCount === 5 || topWordsCount === 7 ? topWordsCount : 3;
    // ── 1. SANITASI TOKEN (Hooks selalu dipanggil di level teratas) ──
    const validTokens = useMemo(() => {
        if (!Array.isArray(tokens)) return [];
        return tokens
            .filter((t) => t && typeof t === "object" && typeof t.word === "string" && t.word.trim() !== "")
            .map((t: any) => {
                const safeWeight = parseWeightStrict(t.weight !== undefined ? t.weight : t.score);
                const rawInf = String(t.influence || "").toUpperCase();

                // Pemetaan pengaruh: dahulukan bobot negatif dan kata negasi 'TIDAK'
                let infType: "hoax" | "fact" | "neutral" = "neutral";
                if (safeWeight < 0 || rawInf.includes("TIDAK") || rawInf === "FACT" || rawInf.includes("FAKTA")) {
                    infType = "fact";
                } else if (safeWeight > 0 || rawInf.includes("HOAKS") || rawInf.includes("HOAX")) {
                    infType = "hoax";
                }

                return {
                    word: String(t.word),
                    weight: safeWeight,
                    influence: infType
                };
            });
    }, [tokens]);

    // Ekstraksi 5 kata pendorong hoaks (validasi ketat per elemen)
    const computedTopHoax = useMemo(() => {
        if (Array.isArray(topHoax) && topHoax.length > 0) {
            const sanitized = topHoax
                .filter((w) => w && typeof w === "object")
                .map((w) => ({ word: String(w.word || "").trim(), score: parseWeightStrict(w.score) }))
                .filter((w) => w.word !== "" && w.score > 0)
                .sort((a, b) => b.score - a.score);
            if (sanitized.length > 0) return sanitized.slice(0, wordLimit);
        }
        // Fallback: hitung dari validTokens jika prop kosong/rusak
        return validTokens
            .filter((t) => t.weight > 0)
            .sort((a, b) => b.weight - a.weight)
            .slice(0, wordLimit)
            .map((t) => ({ word: t.word, score: t.weight }));
    }, [validTokens, topHoax, wordLimit]);

    // Ekstraksi 5 kata penurun skor hoaks
    const computedTopFact = useMemo(() => {
        if (Array.isArray(topFact) && topFact.length > 0) {
            const sanitized = topFact.filter((w) => w && typeof w === "object").map((w) => ({ word: String(w.word || "").trim(), score: Math.abs(parseWeightStrict(w.score)) })).filter((w) => w.word !== "" && w.score > 0).sort((a, b) => b.score - a.score);
            if (sanitized.length > 0) return sanitized.slice(0, wordLimit);
        }
        return validTokens.filter((t) => t.weight < 0).sort((a, b) => a.weight - b.weight).slice(0, wordLimit).map((t) => ({ word: t.word, score: Math.abs(t.weight) }));
    }, [validTokens, topFact, wordLimit]);

    // ── SKALA MAKSIMUM ABSOLUT BERSAMA (Mencegah distorsi visual merah vs hijau) ──
    const globalMaxAbsScore = useMemo(() => {
        const maxH = computedTopHoax.length > 0 ? Math.max(...computedTopHoax.map(w => w.score)) : 0;
        const maxF = computedTopFact.length > 0 ? Math.max(...computedTopFact.map(w => w.score)) : 0;
        return Math.max(maxH, maxF, 0.0001);
    }, [computedTopHoax, computedTopFact]);

    // ── 2. EARLY RETURN JIKA TOKEN KOSONG ──
    if (validTokens.length === 0) {
        return (
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 text-xs text-slate-400 italic">
                Data penjelasan lokal LIME belum tersedia untuk sampel ini.
            </div>
        );
    }

    // ── 3. EVALUASI LABEL PENJELASAN ──
    const predUpper = (prediction || "").toUpperCase();
    const isHoax = (predUpper.includes("HOAKS") || predUpper.includes("HOAX")) && !predUpper.includes("TIDAK");
    const isAmbiguous = predUpper.includes("AMBIGU") || predUpper.includes("VERIFIKASI") || predUpper.includes("KONFIRMASI");
    const isFact = predUpper.includes("FAKTA") || predUpper.includes("TIDAK BERPOLA HOAKS");

    const validScoreStr = (typeof confidenceScore === "number" && Number.isFinite(confidenceScore) && confidenceScore >= 0 && confidenceScore <= 1)
        ? ` ${(confidenceScore * 100).toFixed(1)}%`
        : "";

    return (
        <div className="space-y-4 font-sans">
            <div className="grid grid-cols-1 gap-4 items-stretch">

                {/* DAFTAR KATA BERWARNA BERDASARKAN BOBOT ASLI */}
                <div className="min-w-0 bg-[#f8fafc] border border-slate-200/80 rounded-2xl p-4 flex flex-col justify-between space-y-3">
                    <div>
                        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 mb-2 border-b border-slate-200/60 text-[11px] font-bold text-slate-500">
                            <span>Sebaran Kata Berpengaruh (Token Highlights)</span>
                            <span className="shrink-0 whitespace-nowrap text-[10px] text-slate-400 font-mono">
                                {typeof numSamples === "number" ? `${numSamples} variasi teks diuji` : "Variasi teks diuji"}
                            </span>
                        </div>

                        <div className="p-3 bg-white border border-slate-200/60 rounded-xl leading-relaxed text-xs text-slate-800 max-h-48 overflow-y-auto shadow-2xs">
                            {validTokens.map((item, idx) => {
                                let badgeStyle = "";
                                if (item.influence === "hoax" && item.weight > 0) {
                                    badgeStyle = "bg-rose-100 text-rose-800 font-bold px-1 py-0.5 rounded border border-rose-200 mx-0.5 shadow-2xs inline-block";
                                } else if (item.influence === "fact" && item.weight < 0) {
                                    badgeStyle = "bg-emerald-100 text-emerald-800 font-bold px-1 py-0.5 rounded border border-emerald-200 mx-0.5 shadow-2xs inline-block";
                                }

                                return (
                                    <span
                                        key={idx}
                                        className={badgeStyle}
                                        title={`Bobot Pengaruh: ${item.weight > 0 ? "+" : ""}${item.weight.toFixed(4)}`}
                                    >
                                        {item.word}{" "}
                                    </span>
                                );
                            })}
                        </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-2 border-t border-slate-200/60 text-[11px] text-slate-500">
                        <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                            <span>Merah: Menaikkan Skor Hoaks (+)</span>
                        </span>
                        <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                            <span>Hijau: Menurunkan Skor Hoaks (-)</span>
                        </span>
                    </div>
                </div>

                {/* KETERANGAN CARA KERJA MODEL */}
                <div className="min-w-0 bg-gradient-to-br from-slate-900 to-[#0b2520] text-white rounded-2xl p-4 flex flex-col justify-between shadow-xs border border-emerald-950">
                    <div className="space-y-3">
                        <div className="flex items-center gap-2 pb-2 border-b border-white/10">
                            <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
                            <h4 className="text-xs font-bold tracking-tight text-white">
                                Mekanisme Keputusan Model
                            </h4>
                        </div>

                        {/* Narasi Objektif Sesuai Cara Kerja Backend */}
                        <p className="text-[11px] text-emerald-100/80 leading-relaxed">
                            Warna menunjukkan pengaruh lokal kata terhadap rerata skor kelas hoaks.
                            {isAmbiguous ? (
                                <> Status <strong>PERLU VERIFIKASI</strong> berasal dari ketidaksepakatan keputusan antar-seed model.</>
                            ) : isHoax ? (
                                    <> Keputusan <strong>BERPOLA HOAKS{validScoreStr}</strong> mengikuti aturan voting antar-seed. Kata merah menaikkan skor kelas hoaks, sedangkan kata hijau menurunkannya.</>
                                ) : isFact ? (
                                    <> Keputusan <strong>TIDAK BERPOLA HOAKS{validScoreStr}</strong> mengikuti aturan voting antar-seed. Kata hijau menurunkan skor kelas hoaks, sedangkan kata merah menaikkannya.</>
                            ) : (
                                <> Label keputusan tidak dikenali sistem, sehingga hasil perlu diverifikasi manual. Warna kata tetap menunjukkan pengaruh lokal terhadap skor kelas hoaks.</>
                            )}
                        </p>

                        {/* Daftar Kata Teratas dengan Presisi 4 Desimal */}
                        <div className="bg-white/10 border border-white/10 rounded-xl p-2.5 space-y-1.5">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-300 block">
                                Kata Paling Berpengaruh:
                            </span>

                            {isHoax && computedTopHoax.length > 0 ? (
                                <div className="space-y-1">
                                    {computedTopHoax.map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-rose-300 font-mono font-bold truncate max-w-[120px]">"{w.word}"</span>
                                            <span className="text-rose-400 font-mono font-extrabold text-[10px]">+{w.score.toFixed(4)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : isAmbiguous ? (
                                <div className="space-y-1">
                                        {computedTopHoax.map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-rose-300 font-mono font-bold truncate max-w-[120px]">"{w.word}"</span>
                                            <span className="text-rose-400 font-mono font-extrabold text-[10px]">+{w.score.toFixed(4)}</span>
                                        </div>
                                    ))}
                                        {computedTopFact.map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-emerald-300 font-mono font-bold truncate max-w-[120px]">"{w.word}"</span>
                                            <span className="text-emerald-400 font-mono font-extrabold text-[10px]">-{w.score.toFixed(4)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : computedTopFact.length > 0 ? (
                                <div className="space-y-1">
                                            {computedTopFact.map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-emerald-300 font-mono font-bold truncate max-w-[120px]">"{w.word}"</span>
                                            <span className="text-emerald-400 font-mono font-extrabold text-[10px]">-{w.score.toFixed(4)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <span className="text-[10px] text-slate-300 italic">Data bobot kata tidak tersedia.</span>
                            )}
                        </div>
                    </div>

                    <div className="pt-2 mt-2 border-t border-white/10 flex items-center gap-1.5 text-[10px] text-emerald-300/70">
                        <Info className="w-3 h-3 text-emerald-400 shrink-0" />
                        <span>Bobot dihitung via perturbasi lokal LIME, bukan kamus kata statis.</span>
                    </div>
                </div>

            </div>

            {/* BAGIAN BAWAH: GRAFIK PROPORSI BOBOT KATA (SKALA BERSAMA MURNI TANPA FLOOR 1%) */}
            {showChart && (computedTopHoax.length > 0 || computedTopFact.length > 0) && (
                <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-2xs space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs pb-2 border-b border-slate-100">
                        <span className="font-bold text-slate-800">Seberapa besar pengaruh tiap kata</span>
                        <span className="text-[10px] text-slate-500">
                            Panjang batang = pengaruh relatif, bukan persentase kebenaran
                        </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {/* Kolom Pendorong Hoaks */}
                        <div className="space-y-2">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600 block">
                                Top Kata Menaikkan Skor Hoaks (+):
                            </span>
                            {computedTopHoax.length > 0 ? (
                                computedTopHoax.map((w, i) => {
                                    const pct = Math.min(100, Math.max(0, (w.score / globalMaxAbsScore) * 100));
                                    return (
                                        <div key={i} className="space-y-1">
                                            <div className="flex justify-between text-[11px]">
                                                <span className="font-bold text-slate-700 font-mono">"{w.word}"</span>
                                                <span className="font-mono text-rose-600 font-extrabold">+{w.score.toFixed(4)}</span>
                                            </div>
                                            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-rose-500 rounded-full transition-all"
                                                    style={{ width: `${pct}%` }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })
                            ) : (
                                <p className="text-[11px] text-slate-400 italic">Tidak ada kata yang menaikkan skor hoaks.</p>
                            )}
                        </div>

                        {/* Kolom Pendorong Fakta */}
                        <div className="space-y-2">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 block">
                                Top Kata Menurunkan Skor Hoaks (-):
                            </span>
                            {computedTopFact.length > 0 ? (
                                computedTopFact.map((w, i) => {
                                    const pct = Math.min(100, Math.max(0, (w.score / globalMaxAbsScore) * 100));
                                    return (
                                        <div key={i} className="space-y-1">
                                            <div className="flex justify-between text-[11px]">
                                                <span className="font-bold text-slate-700 font-mono">"{w.word}"</span>
                                                <span className="font-mono text-emerald-600 font-extrabold">-{w.score.toFixed(4)}</span>
                                            </div>
                                            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-emerald-500 rounded-full transition-all"
                                                    style={{ width: `${pct}%` }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })
                            ) : (
                                <p className="text-[11px] text-slate-400 italic">Tidak ada kata yang menurunkan skor hoaks.</p>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
