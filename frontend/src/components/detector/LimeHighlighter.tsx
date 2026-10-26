"use client";

import { useMemo } from "react";
import { LimeToken } from "@/types/detector";
import { Sparkles, Info } from "lucide-react";

interface LimeHighlighterProps {
    tokens?: LimeToken[];
    topHoax?: Array<{ word: string; score: number }>;
    topFact?: Array<{ word: string; score: number }>;
    prediction?: string;
    confidenceScore?: number;
    numSamples?: number;
}

export default function LimeHighlighter({
    tokens = [],
    topHoax = [],
    topFact = [],
    prediction = "TIDAK BERPOLA HOAKS",
    confidenceScore,
    numSamples = 200
}: LimeHighlighterProps) {
    // ── 1. SANITASI DATA & EKSEKUSI HOOKS SELALU DI LEVEL TERATAS (Rules of Hooks) ──
    const validTokens = useMemo(() => {
        if (!Array.isArray(tokens)) return [];
        return tokens
            .filter((t) => t && typeof t.word === "string")
            .map((t: any) => {
                const rawW = t.weight !== undefined ? t.weight : t.score;
                const numW = typeof rawW === "number" ? rawW : parseFloat(String(rawW));
                const safeWeight = Number.isFinite(numW) ? numW : 0;
                const rawInf = String(t.influence || "").toUpperCase();

                // Pemetaan pengaruh eksplisit: dahulukan cek negasi 'TIDAK' / nilai negatif
                let infType: "hoax" | "fact" | "neutral" = "neutral";
                if (rawInf.includes("TIDAK") || rawInf.includes("FACT") || rawInf.includes("FAKTA") || safeWeight < 0) {
                    infType = "fact";
                } else if (rawInf.includes("HOAKS") || rawInf.includes("HOAX") || safeWeight > 0) {
                    infType = "hoax";
                }

                return {
                    word: String(t.word),
                    weight: safeWeight,
                    influence: infType
                };
            });
    }, [tokens]);

    // Ekstraksi 5 kata pendorong hoaks teratas
    const computedTopHoax = useMemo(() => {
        if (Array.isArray(topHoax) && topHoax.length > 0) {
            return topHoax
                .map((w) => ({ word: String(w.word), score: Number(w.score) }))
                .filter((w) => Number.isFinite(w.score) && w.score > 0);
        }
        return validTokens
            .filter((t) => t.weight > 0)
            .sort((a, b) => b.weight - a.weight)
            .slice(0, 5)
            .map((t) => ({ word: t.word, score: t.weight }));
    }, [validTokens, topHoax]);

    // Ekstraksi 5 kata pendorong fakta teratas
    const computedTopFact = useMemo(() => {
        if (Array.isArray(topFact) && topFact.length > 0) {
            return topFact
                .map((w) => ({ word: String(w.word), score: Math.abs(Number(w.score)) }))
                .filter((w) => Number.isFinite(w.score));
        }
        return validTokens
            .filter((t) => t.weight < 0)
            .sort((a, b) => a.weight - b.weight)
            .slice(0, 5)
            .map((t) => ({ word: t.word, score: Math.abs(t.weight) }));
    }, [validTokens, topFact]);

    // Skala maksimum untuk grafik batang proporsional tanpa batas bawah buatan
    const maxHoaxScore = useMemo(() => {
        if (computedTopHoax.length === 0) return 1.0;
        return Math.max(...computedTopHoax.map((w) => w.score), 0.0001);
    }, [computedTopHoax]);

    const maxFactScore = useMemo(() => {
        if (computedTopFact.length === 0) return 1.0;
        return Math.max(...computedTopFact.map((w) => w.score), 0.0001);
    }, [computedTopFact]);

    // ── 2. EARLY RETURN JIKA TOKEN KOSONG (Dipanggil SETELAH semua hook selesai) ──
    if (validTokens.length === 0) {
        return (
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 text-xs text-slate-400 italic">
                Data penjelasan lokal LIME belum tersedia untuk sampel ini.
            </div>
        );
    }

    // ── 3. EVALUASI LABEL & KELAYAKAN SKOR KEYAKINAN ──
    const predUpper = (prediction || "").toUpperCase();
    const isHoax = (predUpper.includes("HOAKS") || predUpper.includes("HOAX")) && !predUpper.includes("TIDAK");
    const isAmbiguous = predUpper.includes("AMBIGU") || predUpper.includes("VERIFIKASI") || predUpper.includes("KONFIRMASI");
    const isFact = predUpper.includes("FAKTA") || predUpper.includes("TIDAK BERPOLA HOAKS");
    const isNeutral = !isHoax && !isAmbiguous && !isFact;

    // Tampilkan persentase HANYA jika nilainya berupa angka valid [0.0 - 1.0]
    const validScoreStr = (typeof confidenceScore === "number" && Number.isFinite(confidenceScore) && confidenceScore >= 0 && confidenceScore <= 1)
        ? ` ${(confidenceScore * 100).toFixed(1)}%`
        : "";

    return (
        <div className="space-y-4 font-sans">

            {/* GRID DUA KOLOM BERDAMPINGAN: VISUAL LIME vs EDUKASI/REASONING */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">

                {/* SISI KIRI (7 KOLOM): TEKS BERWARNA BERDASARKAN BOBOT ASLI */}
                <div className="lg:col-span-7 bg-[#f8fafc] border border-slate-200/80 rounded-2xl p-4 flex flex-col justify-between space-y-3">
                    <div>
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-200/60 text-[11px] font-bold text-slate-500">
                            <span>Sebaran Kata Berpengaruh (Token Highlights)</span>
                            <span className="text-[10px] text-slate-400 font-mono">{numSamples} Perturbasi LIME</span>
                        </div>

                        {/* Kotak Teks Highlight Kata */}
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

                    {/* Legenda Warna Bawah */}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-200/60 text-[11px] text-slate-500">
                        <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                            <span>Merah: Mendorong Hoaks (+)</span>
                        </span>
                        <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                            <span>Hijau: Mendorong Fakta (-)</span>
                        </span>
                    </div>
                </div>

                {/* SISI KANAN (5 KOLOM): KOTAK KETERANGAN LIME */}
                <div className="lg:col-span-5 bg-gradient-to-br from-slate-900 to-[#0b2520] text-white rounded-2xl p-4 flex flex-col justify-between shadow-xs border border-emerald-950">
                    <div className="space-y-3">
                        <div className="flex items-center gap-2 pb-2 border-b border-white/10">
                            <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
                            <h4 className="text-xs font-bold tracking-tight text-white">
                                Mengapa Hasil Ini Muncul?
                            </h4>
                        </div>

                        {/* Narasi Alasan Sesuai Status Real */}
                        <p className="text-[11px] text-emerald-100/80 leading-relaxed">
                            {isHoax ? (
                                <>
                                    Model mendeteksi <strong>kemiripan pola klaim disinformasi</strong>. Kata-kata bertanda <span className="text-rose-400 font-bold">merah</span> memberikan kontribusi terbesar hingga mengarahkan keputusan ke <strong>BERPOLA HOAKS{validScoreStr}</strong>.
                                </>
                            ) : isAmbiguous ? (
                                <>
                                    Model mendeteksi <strong>karakteristik campuran (ambigu)</strong>. Terjadi tarik-menarik bobot antara kata pendorong hoaks (<span className="text-rose-400 font-bold">merah</span>) dan fakta (<span className="text-emerald-400 font-bold">hijau</span>) sehingga status ditetapkan <strong>PERLU VERIFIKASI</strong>.
                                </>
                            ) : isFact ? (
                                <>
                                    Model mengidentifikasi <strong>struktur penulisan berita faktual</strong>. Kata-kata bertanda <span className="text-emerald-400 font-bold">hijau</span> menetralkan kecurigaan dan mengonfirmasi pola <strong>TIDAK BERPOLA HOAKS{validScoreStr}</strong>.
                                </>
                            ) : (
                                <>
                                    Model <strong>tidak dapat menetapkan atribusi bobot spesifik</strong> karena teks berada di luar cakupan evaluasi politik atau tidak memenuhi syarat analisis.
                                </>
                            )}
                        </p>

                        {/* Daftar Kata Teratas Berdasarkan Bobot Aktual */}
                        <div className="bg-white/10 border border-white/10 rounded-xl p-2.5 space-y-1.5">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-300 block">
                                Kata Paling Berpengaruh (Top Weight):
                            </span>

                            {isHoax && computedTopHoax.length > 0 ? (
                                <div className="space-y-1">
                                    {computedTopHoax.slice(0, 3).map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-rose-300 font-mono font-bold truncate max-w-[120px]">"{w.word}"</span>
                                            <span className="text-rose-400 font-mono font-extrabold text-[10px]">+{w.score.toFixed(3)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : isAmbiguous ? (
                                <div className="space-y-1">
                                    {computedTopHoax.slice(0, 1).map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-rose-300 font-mono font-bold truncate max-w-[120px]">"{w.word}"</span>
                                            <span className="text-rose-400 font-mono font-extrabold text-[10px]">+{w.score.toFixed(3)}</span>
                                        </div>
                                    ))}
                                    {computedTopFact.slice(0, 1).map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-emerald-300 font-mono font-bold truncate max-w-[120px]">"{w.word}"</span>
                                            <span className="text-emerald-400 font-mono font-extrabold text-[10px]">-{w.score.toFixed(3)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : computedTopFact.length > 0 ? (
                                <div className="space-y-1">
                                    {computedTopFact.slice(0, 3).map((w, i) => (
                                        <div key={i} className="flex items-center justify-between text-[11px]">
                                            <span className="text-emerald-300 font-mono font-bold truncate max-w-[120px]">"{w.word}"</span>
                                            <span className="text-emerald-400 font-mono font-extrabold text-[10px]">-{w.score.toFixed(3)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <span className="text-[10px] text-slate-300 italic">Data kata kunci tidak tersedia.</span>
                            )}
                        </div>
                    </div>

                    <div className="pt-2 mt-2 border-t border-white/10 flex items-center gap-1.5 text-[10px] text-emerald-300/70">
                        <Info className="w-3 h-3 text-emerald-400 shrink-0" />
                        <span>Bobot dihitung via perturbasi lokal LIME, bukan kamus kata statis.</span>
                    </div>
                </div>

            </div>

            {/* ========================================================= */}
            {/* BAGIAN BAWAH: GRAFIK PROPORSI BOBOT KATA (FEATURE IMPORTANCE) */}
            {/* ========================================================= */}
            {(computedTopHoax.length > 0 || computedTopFact.length > 0) && (
                <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-2xs space-y-3">
                    <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-100">
                        <span className="font-bold text-slate-800">Grafik Nilai Pengaruh Kata (Feature Importance Chart)</span>
                        <span className="text-[10px] text-slate-400 font-mono">Skala Proporsional Terhadap Bobot Tertinggi</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {/* Kolom Pendorong Hoaks */}
                        <div className="space-y-2">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600 block">
                                Top Kata Mendorong Hoaks (+):
                            </span>
                            {computedTopHoax.length > 0 ? (
                                computedTopHoax.slice(0, 3).map((w, i) => {
                                    const pct = Math.min(100, Math.max(1, (w.score / maxHoaxScore) * 100));
                                    return (
                                        <div key={i} className="space-y-1">
                                            <div className="flex justify-between text-[11px]">
                                                <span className="font-bold text-slate-700 font-mono">"{w.word}"</span>
                                                <span className="font-mono text-rose-600 font-extrabold">+{w.score.toFixed(3)}</span>
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
                                <p className="text-[11px] text-slate-400 italic">Tidak ada kata pendorong hoaks.</p>
                            )}
                        </div>

                        {/* Kolom Pendorong Fakta */}
                        <div className="space-y-2">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 block">
                                Top Kata Mendorong Fakta (-):
                            </span>
                            {computedTopFact.length > 0 ? (
                                computedTopFact.slice(0, 3).map((w, i) => {
                                    const pct = Math.min(100, Math.max(1, (w.score / maxFactScore) * 100));
                                    return (
                                        <div key={i} className="space-y-1">
                                            <div className="flex justify-between text-[11px]">
                                                <span className="font-bold text-slate-700 font-mono">"{w.word}"</span>
                                                <span className="font-mono text-emerald-600 font-extrabold">-{w.score.toFixed(3)}</span>
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
                                <p className="text-[11px] text-slate-400 italic">Tidak ada kata pendorong fakta.</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

        </div>
    );
}