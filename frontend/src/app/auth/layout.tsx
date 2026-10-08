import Link from "next/link";
import { ArrowLeft, Cpu, Eye, ScanLine } from "lucide-react";

const FEATURES = [
    { icon: Cpu, label: "IndoBERT Fine-Tuned" },
    { icon: Eye, label: "Transparansi LIME XAI" },
    { icon: ScanLine, label: "Ekstraksi Teks PaddleOCR" },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="grid min-h-screen grid-cols-1 bg-slate-50 lg:grid-cols-2">

            {/* ============ PANEL KIRI: BRANDING (hanya layar lg+) ============ */}
            <aside className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-[#0b2520] via-[#0f4a3c] to-[#1f7a63] p-12 text-white lg:sticky lg:top-0 lg:flex lg:h-screen xl:p-16">

                {/* Dekorasi: grid halus + lingkaran transparan */}
                <div
                    className="pointer-events-none absolute inset-0"
                    style={{
                        backgroundImage:
                            "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
                        backgroundSize: "36px 36px",
                    }}
                />
                <div className="pointer-events-none absolute -left-32 top-1/3 h-[420px] w-[420px] rounded-full bg-white/[0.04]" />
                <div className="pointer-events-none absolute -bottom-40 -right-24 h-[460px] w-[460px] rounded-full bg-emerald-300/10" />

                {/* Brand: logo + nama */}
                <div className="relative flex items-center gap-4">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#0b2520] p-2.5 shadow-lg ring-1 ring-white/20">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src="/logo.png" alt="VERIDIX Logo" className="h-full w-full object-contain" />
                    </div>
                    <div className="leading-tight">
                        <span className="block text-2xl font-extrabold tracking-wide">VERIDIX</span>
                        <span className="mt-0.5 block text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-300">
                            Deteksi Hoaks Politik
                        </span>
                    </div>
                </div>

                {/* Headline */}
                <div className="relative">
                    <p className="text-xs font-bold uppercase tracking-[0.3em] text-emerald-300">
                        Platform Cek Fakta Berbasis AI
                    </p>
                    <h2 className="mt-5 text-4xl font-extrabold leading-[1.05] tracking-tight xl:text-5xl 2xl:text-6xl">
                        Verifikasi Berita
                        <span className="block text-emerald-300">Lebih Cerdas.</span>
                    </h2>
                    <p className="mt-6 max-w-md text-[15px] leading-relaxed text-emerald-100/75">
                        Sistem deteksi disinformasi politik yang menggabungkan IndoBERT, penjelasan LIME, dan OCR gambar dalam satu platform terpadu.
                    </p>

                    <ul className="mt-10 space-y-4">
                        {FEATURES.map(({ icon: Icon, label }) => (
                            <li key={label} className="flex items-center gap-4">
                                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/10 text-emerald-300 backdrop-blur">
                                    <Icon size={18} />
                                </span>
                                <span className="text-[15px] font-semibold text-emerald-50">{label}</span>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* Status */}
                <div className="relative">
                    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-medium backdrop-blur">
                        <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                        </span>
                        Sistem aktif &amp; siap inferensi
                    </span>
                </div>
            </aside>

            {/* ============ PANEL KANAN: LOGO + FORM ============ */}
            <main className="flex min-h-screen flex-col px-6 py-6 sm:px-10">
                <div className="flex justify-end">
                    <Link
                        href="/"
                        className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
                    >
                        <ArrowLeft size={14} /> Beranda
                    </Link>
                </div>

                <div className="flex flex-1 flex-col items-center justify-center py-8">
                    {/* Badge logo besar */}
                    <div className="flex h-24 w-24 items-center justify-center rounded-[28px] border-[3px] border-emerald-500 bg-[#0b2520] p-4 shadow-xl shadow-emerald-900/20">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src="/logo.png" alt="VERIDIX Logo" className="h-full w-full object-contain" />
                    </div>
                    {/* Nama — tampil di mobile saat panel kiri disembunyikan */}
                    <p className="mt-3 text-lg font-extrabold tracking-[0.25em] text-slate-900 lg:hidden">VERIDIX</p>

                    <div className="mt-8 w-full max-w-md">{children}</div>
                </div>

                <p className="pt-2 text-center text-xs text-slate-400">
                    © 2026 VERIDIX · Hasil AI bukan pengganti verifikasi faktual.
                </p>
            </main>
        </div>
    );
}