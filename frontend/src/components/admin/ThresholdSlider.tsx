"use client";

import { useEffect, useState } from "react";
import {
    RotateCcw,
    Save,
    ShieldAlert,
    CheckCircle,
    AlertTriangle,
    TrendingUp,
    Loader2,
} from "lucide-react";

interface LogPoint {
    prediction: string;
    confidence_score: number;
}

interface ThresholdSliderProps {
    currentValue?: number;
    onSave?: (val: number) => Promise<any>;
    /** Opsional: log inferensi terkini untuk grafik progres keyakinan */
    logs?: LogPoint[];
}

const MIN = 0.3;
const MAX = 0.9;

const PRESETS = [
    { label: "Agresif", v: 0.4 },
    { label: "Standar", v: 0.5 },
    { label: "Konservatif", v: 0.7 },
];

export default function ThresholdSlider({ currentValue = 0.5, onSave, logs = [] }: ThresholdSliderProps) {
    const [val, setVal] = useState<number>(currentValue);
    const [isSaved, setIsSaved] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Sinkron bila nilai threshold dari server baru datang / berubah
    useEffect(() => {
        setVal(currentValue);
    }, [currentValue]);

    const isDirty = Math.abs(val - currentValue) > 0.0001;

    const handleApply = async () => {
        setError(null);
        setSaving(true);
        try {
            if (onSave) await onSave(val);
            setIsSaved(true);
            setTimeout(() => setIsSaved(false), 3000);
        } catch {
            setError("Gagal menyimpan threshold. Coba lagi.");
        } finally {
            setSaving(false);
        }
    };

    const handleReset = () => {
        setVal(0.5);
    };

    /* ---------- Rumus (TIDAK diubah) ---------- */
    const faktaMax = val - 0.2;
    const hoaxRate = 65 - val * 40;
    const ambigRate = val * 15;

    /* ---------- Posisi zona pada bar 0..1 ---------- */
    const faktaPct = Math.max(faktaMax, 0) * 100;
    const ambigPct = Math.min(val, 1) * 100 - faktaPct;
    const hoaxPct = (1 - val) * 100;
    const fill = ((val - MIN) / (MAX - MIN)) * 100;

    /* ---------- Grafik progres keyakinan ---------- */
    const chrono = [...logs].reverse(); // lama -> baru
    const avgConf = chrono.length ? chrono.reduce((a, l) => a + l.confidence_score, 0) / chrono.length : 0;

    const W = 640, H = 200, PL = 36, PR = 14, PT = 14, PB = 22;
    const LO = 0.3, HI = 1;
    const innerW = W - PL - PR;
    const innerH = H - PT - PB;
    const clamp = (c: number) => Math.min(Math.max(c, LO), HI);
    const px = (i: number) => (chrono.length > 1 ? PL + (i * innerW) / (chrono.length - 1) : PL + innerW / 2);
    const py = (c: number) => PT + (1 - (clamp(c) - LO) / (HI - LO)) * innerH;
    const pts = chrono.map((l, i) => ({ x: px(i), y: py(l.confidence_score), hoax: l.prediction === "HOAKS" }));
    const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const areaPath = pts.length
        ? `${linePath} L${pts[pts.length - 1].x.toFixed(1)},${PT + innerH} L${pts[0].x.toFixed(1)},${PT + innerH} Z`
        : "";
    const thrY = py(val);

    return (
        <div className="space-y-6">

            {/* ============ KARTU KONTROL ============ */}
            <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 shadow-2xs space-y-6">

                {/* Header + aksi */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                    <div>
                        <h3 className="text-base font-bold text-slate-900">Nilai Ambang Batas Klasifikasi (Decision Boundary)</h3>
                        <p className="text-xs text-slate-400 mt-0.5">Mengatur tingkat sensitivitas probabilitas Softmax untuk vonis Hoaks.</p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        {isSaved && (
                            <span className="text-xs text-emerald-700 font-semibold bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200 animate-in fade-in">
                                Threshold Berhasil Diperbarui
                            </span>
                        )}
                        {error && (
                            <span className="text-xs text-slate-700 font-semibold bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">
                                {error}
                            </span>
                        )}
                        <button
                            type="button"
                            onClick={handleReset}
                            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-100 rounded-xl transition"
                        >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>Reset 0.50</span>
                        </button>
                        <button
                            type="button"
                            onClick={handleApply}
                            disabled={saving}
                            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-emerald-800 hover:bg-emerald-700 disabled:opacity-60 rounded-xl shadow-sm shadow-emerald-900/20 transition"
                        >
                            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                            <span>{saving ? "Menyimpan..." : "Terapkan Sekarang"}</span>
                        </button>
                    </div>
                </div>

                {/* Nilai besar + slider */}
                <div className="text-center py-2 space-y-4">
                    <div className="flex items-center justify-center gap-3">
                        <span className="text-5xl font-extrabold text-slate-900 font-mono tracking-tight">
                            {val.toFixed(2)}
                        </span>
                        {isDirty && (
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-100 border border-emerald-200 px-2 py-1 rounded-lg">
                                Belum disimpan
                            </span>
                        )}
                    </div>
                    <p className="text-xs text-slate-400">Sensitivitas Aktif Model IndoBERT</p>

                    {/* Preset cepat */}
                    <div className="flex items-center justify-center gap-2">
                        {PRESETS.map((p) => {
                            const active = Math.abs(val - p.v) < 0.001;
                            return (
                                <button
                                    key={p.label}
                                    type="button"
                                    onClick={() => setVal(p.v)}
                                    className={`px-3 py-1 text-[11px] font-bold rounded-lg border transition ${active
                                        ? "bg-emerald-800 text-white border-emerald-800"
                                        : "bg-white text-emerald-800 border-emerald-200 hover:bg-emerald-50"
                                        }`}
                                >
                                    {p.label} · {p.v.toFixed(2)}
                                </button>
                            );
                        })}
                    </div>

                    <div className="max-w-xl mx-auto px-4">
                        <input
                            type="range"
                            min={MIN}
                            max={MAX}
                            step="0.01"
                            value={val}
                            onChange={(e) => setVal(parseFloat(e.target.value))}
                            style={{ background: `linear-gradient(to right,#047857 ${fill}%,#e2e8f0 ${fill}%)` }}
                            className="w-full h-2.5 rounded-full appearance-none cursor-pointer
                                [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5
                                [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-emerald-700
                                [&::-webkit-slider-thumb]:border-4 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:shadow-md
                                [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:rounded-full
                                [&::-moz-range-thumb]:bg-emerald-700 [&::-moz-range-thumb]:border-4 [&::-moz-range-thumb]:border-white"
                        />
                        <div className="flex justify-between text-[11px] font-mono text-slate-400 mt-2">
                            <span>0.30 (Lebih Agresif Hoaks)</span>
                            <span>0.50 (Standar Imbang)</span>
                            <span>0.90 (Sangat Konservatif)</span>
                        </div>
                    </div>
                </div>

                {/* Bar zona 0..1 (bergeser mengikuti slider) */}
                <div>
                    <div className="flex h-3 w-full overflow-hidden rounded-full">
                        <div className="bg-emerald-100 transition-all duration-300" style={{ width: `${faktaPct}%` }} />
                        <div className="bg-emerald-400 transition-all duration-300" style={{ width: `${ambigPct}%` }} />
                        <div className="bg-emerald-900 transition-all duration-300" style={{ width: `${hoaxPct}%` }} />
                    </div>
                    <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1.5">
                        <span>0.00</span>
                        <span>Probabilitas Hoaks</span>
                        <span>1.00</span>
                    </div>
                </div>

                {/* Zona 3 vonis (satu warna hijau, beda tingkat) */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-2xl space-y-1">
                        <span className="font-bold text-emerald-800 flex items-center gap-1.5">
                            <CheckCircle className="w-4 h-4 text-emerald-600" />
                            Zona Vonis FAKTA
                        </span>
                        <p className="text-emerald-700 text-[11px]">Probabilitas Hoaks ≤ {faktaMax.toFixed(2)}</p>
                    </div>

                    <div className="p-4 bg-emerald-100/70 border border-dashed border-emerald-400 rounded-2xl space-y-1">
                        <span className="font-bold text-emerald-900 flex items-center gap-1.5">
                            <AlertTriangle className="w-4 h-4 text-emerald-700" />
                            Zona PERLU KONFIRMASI
                        </span>
                        <p className="text-emerald-800 text-[11px]">Rentang ambiguitas {faktaMax.toFixed(2)} sampai {val.toFixed(2)}</p>
                    </div>

                    <div className="p-4 bg-emerald-900 border border-emerald-900 rounded-2xl space-y-1">
                        <span className="font-bold text-white flex items-center gap-1.5">
                            <ShieldAlert className="w-4 h-4 text-emerald-300" />
                            Zona Vonis HOAKS
                        </span>
                        <p className="text-emerald-200 text-[11px]">Probabilitas Hoaks ≥ {val.toFixed(2)}</p>
                    </div>
                </div>

                {/* Simulasi dampak (rumus asli, tampilan baru) */}
                <div className="bg-emerald-50/60 border border-emerald-100 rounded-2xl p-4 text-xs text-slate-600 space-y-3">
                    <p className="font-bold text-slate-800">Simulasi Dampak Inferensi (100 Sampel Terakhir):</p>
                    <p className="leading-relaxed">
                        Pada threshold <strong className="font-mono">{val.toFixed(2)}</strong>, diperkirakan rasio deteksi hoaks sistem akan berada pada kisaran{" "}
                        <strong className="text-slate-900 font-mono">{hoaxRate.toFixed(1)}%</strong> dengan tingkat ambiguitas{" "}
                        <strong className="text-slate-900 font-mono">{ambigRate.toFixed(1)}%</strong>.
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <div className="flex justify-between text-[11px] mb-1">
                                <span className="font-semibold text-slate-600">Rasio deteksi hoaks</span>
                                <span className="font-mono font-bold text-emerald-900">{hoaxRate.toFixed(1)}%</span>
                            </div>
                            <div className="h-2 rounded-full bg-emerald-100 overflow-hidden">
                                <div className="h-full rounded-full bg-emerald-800 transition-all duration-300" style={{ width: `${Math.min(Math.max(hoaxRate, 0), 100)}%` }} />
                            </div>
                        </div>
                        <div>
                            <div className="flex justify-between text-[11px] mb-1">
                                <span className="font-semibold text-slate-600">Tingkat ambiguitas</span>
                                <span className="font-mono font-bold text-emerald-900">{ambigRate.toFixed(1)}%</span>
                            </div>
                            <div className="h-2 rounded-full bg-emerald-100 overflow-hidden">
                                <div className="h-full rounded-full bg-emerald-400 transition-all duration-300" style={{ width: `${Math.min(Math.max(ambigRate, 0), 100)}%` }} />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ============ KARTU PROGRES KEYAKINAN MODEL ============ */}
            <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 shadow-2xs">
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100">
                            <TrendingUp className="w-4 h-4" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900 leading-tight">Progres Keyakinan Model</h3>
                            <p className="text-xs text-slate-400 mt-0.5">
                                {chrono.length} inferensi terakhir. Garis putus-putus mengikuti slider threshold.
                            </p>
                        </div>
                    </div>
                    <div className="text-right shrink-0">
                        <p className="text-xl font-extrabold text-slate-900 leading-none">{(avgConf * 100).toFixed(1)}%</p>
                        <p className="text-[11px] text-slate-400 mt-1">rata-rata keyakinan</p>
                    </div>
                </div>

                {chrono.length === 0 ? (
                    <div className="h-44 flex items-center justify-center text-xs text-slate-400">
                        Belum ada data inferensi.
                    </div>
                ) : (
                    <svg viewBox={`0 0 ${W} ${H}`} className="mt-4 w-full h-auto" role="img" aria-label="Grafik progres keyakinan model">
                        <defs>
                            <linearGradient id="vx-conf" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
                                <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                            </linearGradient>
                        </defs>

                        {[0.3, 0.5, 0.75, 1].map((v) => (
                            <g key={v}>
                                <line x1={PL} x2={W - PR} y1={py(v)} y2={py(v)} className="stroke-slate-200" strokeDasharray="3 4" />
                                <text x={PL - 6} y={py(v) + 3} textAnchor="end" fontSize="9" className="fill-slate-400">{Math.round(v * 100)}%</text>
                            </g>
                        ))}

                        {/* Garis threshold hidup */}
                        <line x1={PL} x2={W - PR} y1={thrY} y2={thrY} className="stroke-emerald-800" strokeWidth="1.4" strokeDasharray="5 4" />
                        <text x={W - PR} y={thrY - 5} textAnchor="end" fontSize="10" fontWeight="700" className="fill-emerald-800">
                            threshold {val.toFixed(2)}
                        </text>

                        <path d={areaPath} fill="url(#vx-conf)" />
                        <path d={linePath} fill="none" className="stroke-emerald-600" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />

                        {pts.map((p, i) => (
                            <circle
                                key={i}
                                cx={p.x}
                                cy={p.y}
                                r="4"
                                strokeWidth="2"
                                className={p.hoax ? "stroke-emerald-800 fill-emerald-800" : "stroke-emerald-500 fill-white"}
                            />
                        ))}
                    </svg>
                )}

                <div className="mt-2 flex items-center gap-4 text-[11px] text-slate-500">
                    <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-emerald-800" />Hoaks</span>
                    <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full border-2 border-emerald-500 bg-white" />Valid</span>
                </div>
            </div>
        </div>
    );
}