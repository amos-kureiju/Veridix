"use client";

import { useState } from "react";
import { useAdminDashboard } from "@/hooks/useAdminDashboard";
import {
    ShieldAlert,
    CheckCircle,
    Clock,
    Sliders,
    ArrowUpRight,
    Eye,
    Download,
    Activity,
    Users,
} from "lucide-react";
import Link from "next/link";

/* Gaya bersama: satu warna hijau (emerald) + netral slate */
const CARD = "bg-white border border-slate-200/80 rounded-3xl shadow-2xs";
const CHIP = "w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100";
const LABEL = "text-[11px] font-bold text-slate-400 uppercase tracking-wider";
const PILL = "text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200/60";

type Period = "week" | "month" | "year";
type RegPoint = { label: string; count: number };

const PERIODS: { key: Period; label: string; sub: string; unit: string }[] = [
    { key: "week", label: "Minggu", sub: "Pendaftar 7 hari terakhir", unit: "hari" },
    { key: "month", label: "Bulan", sub: "Pendaftar per minggu bulan ini", unit: "minggu" },
    { key: "year", label: "Tahun", sub: "Pendaftar per bulan tahun ini", unit: "bulan" },
];

/** Data contoh, hanya dipakai bila backend belum mengirim `stats.registrations` */
const SAMPLE_REG: Record<Period, RegPoint[]> = {
    week: [
        { label: "Sen", count: 6 }, { label: "Sel", count: 9 }, { label: "Rab", count: 7 },
        { label: "Kam", count: 12 }, { label: "Jum", count: 15 }, { label: "Sab", count: 8 }, { label: "Min", count: 5 },
    ],
    month: [
        { label: "M1", count: 38 }, { label: "M2", count: 52 }, { label: "M3", count: 47 }, { label: "M4", count: 64 },
    ],
    year: [
        { label: "Jan", count: 120 }, { label: "Feb", count: 98 }, { label: "Mar", count: 143 }, { label: "Apr", count: 131 },
        { label: "Mei", count: 170 }, { label: "Jun", count: 156 }, { label: "Jul", count: 190 }, { label: "Agu", count: 178 },
        { label: "Sep", count: 205 }, { label: "Okt", count: 88 }, { label: "Nov", count: 0 }, { label: "Des", count: 0 },
    ],
};

export default function AdminDashboardPage() {
    const { stats, recentLogs, loading } = useAdminDashboard();

    /* ---------- Data turunan ---------- */
    const logs = recentLogs ?? [];
    const chrono = [...logs].reverse(); // lama -> baru

    // 1) Pendaftaran akun baru (filter dinamis)
    const [period, setPeriod] = useState<Period>("week");
    const [hover, setHover] = useState<number | null>(null);

    // Backend cukup mengirim: stats.registrations = { week: [...], month: [...], year: [...] }
    const apiReg = (stats as unknown as { registrations?: Partial<Record<Period, RegPoint[]>> }).registrations;
    const apiSeries = apiReg?.[period];
    const isSample = !apiSeries || apiSeries.length === 0;
    const series: RegPoint[] = isSample ? SAMPLE_REG[period] : apiSeries!;
    const meta = PERIODS.find((p) => p.key === period)!;

    const n = series.length;
    const maxReg = Math.max(...series.map((w) => w.count), 0);
    const totalReg = series.reduce((a, w) => a + w.count, 0);
    const avgReg = n ? totalReg / n : 0;
    const peak = series.reduce((best, w) => (w.count > best.count ? w : best), series[0] ?? { label: "-", count: 0 });
    const lastReg = n ? series[n - 1].count : 0;
    const prevReg = n > 1 ? series[n - 2].count : 0;
    const regDelta = prevReg > 0 ? ((lastReg - prevReg) / prevReg) * 100 : 0;

    // Geometri grafik area
    const CW = 760, CH = 280, CL = 42, CR = 18, CT = 18, CB = 30;
    const cInnerW = CW - CL - CR;
    const cInnerH = CH - CT - CB;
    const TICKS = 4;
    const rawStep = Math.max(maxReg, 1) / TICKS;
    const pow = 10 ** Math.floor(Math.log10(rawStep));
    const frac = rawStep / pow;
    const niceFrac = frac <= 1 ? 1 : frac <= 2 ? 2 : frac <= 2.5 ? 2.5 : frac <= 5 ? 5 : 10;
    const stepY = niceFrac * pow;
    const topY = stepY * TICKS;
    const cx = (i: number) => (n > 1 ? CL + (i * cInnerW) / (n - 1) : CL + cInnerW / 2);
    const cy = (v: number) => CT + (1 - v / topY) * cInnerH;
    const cpts = series.map((w, i) => ({ x: cx(i), y: cy(w.count) }));
    // Kurva halus (bezier dengan tangen horizontal, tanpa overshoot)
    const curve = cpts.reduce((d, p, i) => {
        if (i === 0) return `M${p.x.toFixed(1)},${p.y.toFixed(1)}`;
        const q = cpts[i - 1];
        const mx = ((q.x + p.x) / 2).toFixed(1);
        return `${d} C${mx},${q.y.toFixed(1)} ${mx},${p.y.toFixed(1)} ${p.x.toFixed(1)},${p.y.toFixed(1)}`;
    }, "");
    const area = cpts.length
        ? `${curve} L${cpts[n - 1].x.toFixed(1)},${CT + cInnerH} L${cpts[0].x.toFixed(1)},${CT + cInnerH} Z`
        : "";
    const active = hover ?? n - 1;
    const colW = n > 1 ? cInnerW / (n - 1) : cInnerW;
    const TW = 132, TH = 46;
    const tipX = cpts[active] ? Math.min(Math.max(cpts[active].x - TW / 2, CL), CW - CR - TW) : 0;
    const tipY = cpts[active] ? (cpts[active].y - TH - 14 < CT ? cpts[active].y + 14 : cpts[active].y - TH - 14) : 0;

    // Mini bar kartu hoaks (8 log terakhir)
    const miniBars = chrono.slice(-8);

    return (
        <div className="space-y-6 pb-6">

            {/* 1. HERO BANNER */}
            <div className="relative overflow-hidden bg-gradient-to-r from-emerald-950 via-emerald-900 to-emerald-800 rounded-3xl p-6 sm:p-8 text-white shadow-md border border-emerald-900/50">
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#6ee7b7_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
                <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-emerald-400/20 blur-3xl pointer-events-none" />

                <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <span className="text-[11px] font-bold tracking-widest text-emerald-300 uppercase">
                            METRIK MONITORING GLOBAL
                        </span>
                        <div className="flex items-baseline gap-3 mt-1">
                            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight font-sans">
                                {stats.total_detections_today.toLocaleString("id-ID")}
                            </h2>
                            <span className="inline-flex items-center gap-0.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-white/10 text-emerald-200 border border-white/15">
                                <ArrowUpRight className="w-3.5 h-3.5" />
                                +{stats.total_detections_delta}% hari ini
                            </span>
                        </div>
                        <p className="text-xs text-emerald-100/70 mt-2 max-w-md leading-relaxed">
                            Total artikel dan tangkapan layar politik yang telah diverifikasi oleh korpus IndoBERT dan OCR.
                        </p>
                    </div>

                    <div className="flex items-center gap-3 self-start md:self-auto">
                        <Link
                            href="/admin/threshold"
                            className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-4 py-2.5 rounded-xl border border-white/15 backdrop-blur-xs transition"
                        >
                            <Sliders className="w-3.5 h-3.5 text-emerald-300" />
                            <span>Threshold: {stats.active_threshold.toFixed(2)}</span>
                        </Link>

                        <Link
                            href="/admin/export"
                            className="flex items-center gap-2 bg-emerald-400 hover:bg-emerald-300 text-emerald-950 text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-lg shadow-emerald-950/30"
                        >
                            <Download className="w-3.5 h-3.5" />
                            <span>Ekspor Rekap</span>
                        </Link>
                    </div>
                </div>
            </div>

            {/* 2. TIGA KARTU METRIK */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* Hoaks Terdeteksi */}
                <div className={`${CARD} p-6 flex flex-col justify-between`}>
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className={LABEL}>HOAKS TERDETEKSI</span>
                            <div className={CHIP}><ShieldAlert className="w-4 h-4" /></div>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.hoax_detected_today}</h3>
                            <span className={PILL}>{stats.hoax_ratio_percent}% rasio</span>
                        </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-end gap-1.5 h-10 box-content">
                        {(miniBars.length ? miniBars.map((l) => ({ h: Math.max(l.confidence_score * 100, 15), hoax: l.prediction === "HOAKS" }))
                            : [40, 65, 30, 85, 95, 45, 75, 60].map((h, i) => ({ h, hoax: i === 4 }))
                        ).map((b, i) => (
                            <div
                                key={i}
                                style={{ height: `${b.h}%` }}
                                className={`flex-1 rounded-sm transition-all duration-700 ${b.hoax ? "bg-emerald-700" : "bg-emerald-200"}`}
                            />
                        ))}
                    </div>
                </div>

                {/* Feedback */}
                <div className={`${CARD} p-6 flex flex-col justify-between`}>
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className={LABEL}>SANGGAHAN USER (FEEDBACK)</span>
                            <div className={CHIP}><Clock className="w-4 h-4" /></div>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.pending_feedbacks}</h3>
                            <span className={PILL}>Menunggu Review</span>
                        </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                        <span className="text-slate-400">Kandidat Dataset Baru</span>
                        <Link href="/admin/feedback" className="font-bold text-emerald-700 hover:underline">
                            Kelola Sekarang →
                        </Link>
                    </div>
                </div>

                {/* Pengguna Aktif */}
                <div className={`${CARD} p-6 flex flex-col justify-between`}>
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className={LABEL}>PENGGUNA AKTIF SISTEM</span>
                            <div className={CHIP}><Activity className="w-4 h-4" /></div>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.active_users_count}</h3>
                            <span className={PILL}>Online</span>
                        </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                        <span>Beban Server: Optimal (0.38s/inf)</span>
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    </div>
                </div>
            </div>

            {/* 3. GRAFIK PENGGUNA BARU */}
            <div className={`${CARD} p-6 sm:p-7`}>

                {/* Header + filter */}
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className={CHIP}><Users className="w-4 h-4" /></div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900 leading-tight flex items-center gap-2">
                                Pendaftaran Akun Baru
                                {isSample && (
                                    <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded-md">
                                        Contoh
                                    </span>
                                )}
                            </h3>
                            <p className="text-xs text-slate-400 mt-0.5">{meta.sub}</p>
                        </div>
                    </div>

                    <div className="inline-flex rounded-xl bg-emerald-50 p-1 border border-emerald-100">
                        {PERIODS.map((p) => (
                            <button
                                key={p.key}
                                type="button"
                                onClick={() => { setPeriod(p.key); setHover(null); }}
                                className={`px-3.5 py-1.5 text-[11px] font-bold rounded-lg transition ${period === p.key
                                    ? "bg-emerald-700 text-white shadow-sm"
                                    : "text-emerald-700 hover:bg-emerald-100"
                                    }`}
                            >
                                {p.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Ringkasan */}
                <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="rounded-2xl bg-emerald-50/70 border border-emerald-100 px-4 py-3">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total akun baru</p>
                        <div className="mt-1 flex items-baseline gap-2">
                            <span className="text-2xl font-extrabold text-slate-900 leading-none">{totalReg.toLocaleString("id-ID")}</span>
                            <span className={`text-[11px] font-bold ${regDelta >= 0 ? "text-emerald-700" : "text-slate-500"}`}>
                                {regDelta >= 0 ? "▲" : "▼"} {Math.abs(regDelta).toFixed(1)}%
                            </span>
                        </div>
                    </div>
                    <div className="rounded-2xl bg-emerald-50/70 border border-emerald-100 px-4 py-3">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Rata-rata per {meta.unit}</p>
                        <span className="mt-1 block text-2xl font-extrabold text-slate-900 leading-none">{avgReg.toFixed(1)}</span>
                    </div>
                    <div className="rounded-2xl bg-emerald-50/70 border border-emerald-100 px-4 py-3">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Puncak</p>
                        <div className="mt-1 flex items-baseline gap-2">
                            <span className="text-2xl font-extrabold text-slate-900 leading-none">{peak.count}</span>
                            <span className="text-[11px] font-semibold text-emerald-700">{peak.label}</span>
                        </div>
                    </div>
                </div>

                {/* Grafik area halus + tooltip */}
                <svg
                    viewBox={`0 0 ${CW} ${CH}`}
                    className="mt-5 w-full h-auto"
                    role="img"
                    aria-label="Grafik pendaftaran akun baru"
                    onMouseLeave={() => setHover(null)}
                >
                    <defs>
                        <linearGradient id="vx-reg" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.32" />
                            <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                        </linearGradient>
                    </defs>

                    {/* Grid + sumbu Y */}
                    {Array.from({ length: TICKS + 1 }, (_, i) => i * stepY).map((v) => (
                        <g key={v}>
                            <line x1={CL} x2={CW - CR} y1={cy(v)} y2={cy(v)} className="stroke-slate-200/80" strokeDasharray={v === 0 ? "0" : "3 5"} />
                            <text x={CL - 8} y={cy(v) + 3} textAnchor="end" fontSize="10" className="fill-slate-400">{Number.isInteger(v) ? v : v.toFixed(1)}</text>
                        </g>
                    ))}

                    {/* Garis panduan titik aktif */}
                    {cpts[active] && (
                        <line x1={cpts[active].x} x2={cpts[active].x} y1={CT} y2={CT + cInnerH} className="stroke-emerald-300" strokeWidth="1.2" strokeDasharray="4 4" />
                    )}

                    <path d={area} fill="url(#vx-reg)" />
                    <path d={curve} fill="none" className="stroke-emerald-600" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />

                    {/* Titik: kecil biasa, besar saat aktif */}
                    {cpts.map((p, i) => (
                        <circle
                            key={i}
                            cx={p.x}
                            cy={p.y}
                            r={i === active ? 6 : n > 8 ? 2.5 : 3.5}
                            strokeWidth={i === active ? 3 : 2}
                            className={i === active ? "stroke-white fill-emerald-700" : "stroke-emerald-500 fill-white"}
                            style={{ transition: "r .15s ease" }}
                        />
                    ))}

                    {/* Label sumbu X */}
                    {series.map((w, i) => (
                        <text
                            key={w.label}
                            x={cx(i)}
                            y={CH - 8}
                            textAnchor="middle"
                            fontSize="10.5"
                            fontWeight={i === active ? 700 : 500}
                            className={i === active ? "fill-emerald-800" : "fill-slate-400"}
                        >
                            {w.label}
                        </text>
                    ))}

                    {/* Tooltip */}
                    {hover !== null && cpts[hover] && (
                        <g transform={`translate(${tipX},${tipY})`} pointerEvents="none">
                            <rect width={TW} height={TH} rx="10" className="fill-emerald-950" opacity="0.96" />
                            <text x="12" y="19" fontSize="10" className="fill-emerald-300" fontWeight="600">{series[hover].label}</text>
                            <text x="12" y="36" fontSize="13" className="fill-white" fontWeight="800">
                                {series[hover].count.toLocaleString("id-ID")} akun baru
                            </text>
                        </g>
                    )}

                    {/* Area hover per kolom */}
                    {series.map((w, i) => (
                        <rect
                            key={w.label}
                            x={cx(i) - colW / 2}
                            y={CT}
                            width={colW}
                            height={cInnerH}
                            fill="transparent"
                            onMouseEnter={() => setHover(i)}
                            style={{ cursor: "crosshair" }}
                        />
                    ))}
                </svg>
            </div>

            {/* 4. TABEL LOG */}
            <div className={`${CARD} overflow-hidden`}>

                <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h3 className="text-base font-bold text-slate-900 leading-tight">Log Inferensi Terkini</h3>
                        <p className="text-xs text-slate-400 mt-0.5">Aktivitas deteksi masyarakat yang masuk secara real-time.</p>
                    </div>

                    <Link
                        href="/admin/logs"
                        className="px-3.5 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-100 rounded-xl transition"
                    >
                        Lihat Semua Log
                    </Link>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-emerald-50/60 text-emerald-700 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3.5 px-6">Identitas Pengguna</th>
                                <th className="py-3.5 px-6">Cuplikan Berita</th>
                                <th className="py-3.5 px-6">Sub-Topik</th>
                                <th className="py-3.5 px-6">Vonis IndoBERT</th>
                                <th className="py-3.5 px-6">Keyakinan</th>
                                <th className="py-3.5 px-6 text-right">Aksi</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {logs.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="py-10 text-center text-slate-400">
                                        {loading ? "Memuat log..." : "Belum ada log inferensi."}
                                    </td>
                                </tr>
                            )}
                            {logs.map((log) => {
                                const isHoax = log.prediction === "HOAKS";
                                return (
                                    <tr key={log.id} className="hover:bg-emerald-50/50 transition">
                                        <td className="py-4 px-6 font-mono text-slate-600 whitespace-nowrap">
                                            {log.user_identifier}
                                        </td>
                                        <td className="py-4 px-6 font-medium text-slate-800 max-w-xs truncate">
                                            {log.text_snippet}
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-lg text-[11px] font-medium border border-slate-200">
                                                {log.political_topic}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${isHoax
                                                ? "bg-emerald-900 text-white"
                                                : "bg-emerald-50 text-emerald-700 border border-emerald-200/60"
                                                }`}>
                                                {isHoax ? <ShieldAlert className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
                                                {log.prediction}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6">
                                            <div className="flex items-center gap-2.5">
                                                <span className="font-mono font-semibold text-slate-700 w-12">
                                                    {(log.confidence_score * 100).toFixed(1)}%
                                                </span>
                                                <div className="h-1.5 w-16 rounded-full bg-slate-100 overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full ${isHoax ? "bg-emerald-800" : "bg-emerald-400"}`}
                                                        style={{ width: `${Math.min(log.confidence_score * 100, 100)}%` }}
                                                    />
                                                </div>
                                            </div>
                                        </td>
                                        <td className="py-4 px-6 text-right whitespace-nowrap">
                                            <button
                                                type="button"
                                                onClick={() => alert(`Inspeksi Log: ${log.id}`)}
                                                className="p-1.5 text-slate-400 hover:text-emerald-800 hover:bg-emerald-50 rounded-lg transition"
                                                title="Inspeksi LIME"
                                            >
                                                <Eye className="w-4 h-4" />
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    );
}