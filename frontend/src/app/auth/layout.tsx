import Link from "next/link";
import { Playfair_Display } from "next/font/google";
import { ArrowLeft, Cpu, Eye, ScanLine } from "lucide-react";

const serif = Playfair_Display({ subsets: ["latin"], weight: ["600", "700", "800"], style: ["normal", "italic"] });

const FEATURES = [
    { icon: Cpu, label: "IndoBERT Fine-Tuned", desc: "Model bahasa Indonesia untuk klasifikasi hoaks" },
    { icon: Eye, label: "Transparansi LIME XAI", desc: "Alasan prediksi dapat ditelusuri kata demi kata" },
    { icon: ScanLine, label: "Ekstraksi Teks PaddleOCR", desc: "Periksa klaim dari tangkapan layar & gambar" },
];

const TOPICS = ["Pemilu", "Kebijakan Publik", "Tokoh Politik"];

/* Motif hemicycle: susunan kursi parlemen */
const SEATS = Array.from({ length: 6 }, (_, row) => {
    const r = 100 + row * 36;
    const n = 9 + row * 4;
    return Array.from({ length: n }, (_, i) => {
        const a = Math.PI * (i / (n - 1));
        return { x: 300 + r * Math.cos(a), y: 300 - r * Math.sin(a), accent: (row * 3 + i) % 9 === 0 };
    });
}).flat();

export default function AuthLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="grid min-h-screen grid-cols-1 bg-slate-50 lg:grid-cols-2">

            {/* ============ PANEL KIRI ============ */}
            <aside className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-[#051a16] via-[#0a3329] to-[#135743] p-12 text-white lg:sticky lg:top-0 lg:flex lg:h-screen xl:p-16">

                {/* Tekstur: garis diagonal tipis (bukan kotak-kotak) */}
                <div
                    className="pointer-events-none absolute inset-0"
                    style={{
                        backgroundImage:
                            "repeating-linear-gradient(45deg, rgba(255,255,255,0.025) 0px, rgba(255,255,255,0.025) 1px, transparent 1px, transparent 22px)",
                    }}
                />

                {/* Busur konsentris bergaya podium / panggung */}
                <svg className="pointer-events-none absolute -left-40 top-1/4 h-[620px] w-[620px]" viewBox="0 0 620 620" fill="none" aria-hidden="true">
                    {[300, 240, 180, 120].map((r) => (
                        <circle key={r} cx="310" cy="310" r={r} stroke="white" strokeOpacity="0.05" />
                    ))}
                </svg>

                {/* Hemicycle parlemen */}
                <svg viewBox="0 0 600 320" className="pointer-events-none absolute -bottom-6 -right-16 w-[540px] max-w-none" aria-hidden="true">
                    {SEATS.map((s, i) => (
                        <circle key={i} cx={s.x} cy={s.y} r={s.accent ? 4.5 : 3.5}
                            fill={s.accent ? "#e9c46a" : "#ffffff"} opacity={s.accent ? 0.55 : 0.13} />
                    ))}
                </svg>

                {/* Cahaya halus */}
                <div className="pointer-events-none absolute -bottom-32 -left-20 h-[380px] w-[380px] rounded-full bg-emerald-400/10 blur-3xl" />

                {/* Brand */}
                <div className="relative flex items-center gap-4">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#051a16] p-2.5 shadow-lg ring-1 ring-white/20">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src="/logo.png" alt="VERIDIX Logo" className="h-full w-full object-contain" />
                    </div>
                    <div className="leading-tight">
                        <span className="block text-2xl font-extrabold tracking-[0.12em]">VERIDIX</span>
                        <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.28em] text-emerald-200/80">
                            Deteksi Hoaks Politik
                        </span>
                    </div>
                </div>

                {/* Headline */}
                <div className="relative">
                    <div className="flex items-center gap-3">
                        <span className="h-px w-10 bg-amber-300/70" />
                        <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-amber-200">
                            Platform Cek Fakta Berbasis AI
                        </p>
                    </div>

                    <h2 className={`${serif.className} mt-6 text-4xl font-bold leading-[1.1] tracking-tight xl:text-5xl 2xl:text-[3.4rem]`}>
                        Verifikasi Berita
                        <span className="block italic font-semibold text-emerald-200">Lebih Cerdas.</span>
                    </h2>

                    <p className="mt-6 max-w-md text-[15px] leading-relaxed text-emerald-50/70">
                        Sistem deteksi disinformasi politik yang menggabungkan IndoBERT, penjelasan LIME, dan OCR gambar dalam satu platform terpadu.
                    </p>

                    <ul className="mt-9 max-w-md divide-y divide-white/10 border-y border-white/10">
                        {FEATURES.map(({ icon: Icon, label, desc }, i) => (
                            <li key={label} className="flex items-center gap-4 py-4">
                                <span className={`${serif.className} w-7 text-lg font-semibold text-amber-200/80`}>0{i + 1}</span>
                                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/10 text-emerald-200 ring-1 ring-white/10">
                                    <Icon size={17} />
                                </span>
                                <span className="leading-snug">
                                    <span className="block text-[15px] font-semibold text-white">{label}</span>
                                    <span className="block text-xs text-emerald-100/60">{desc}</span>
                                </span>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* Topik + status */}
                <div className="relative space-y-4">
                    <div className="flex flex-wrap gap-2">
                        {TOPICS.map((t) => (
                            <span key={t} className="rounded-full border border-amber-200/25 px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-amber-100/80">
                                {t}
                            </span>
                        ))}
                    </div>
                    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-medium backdrop-blur">
                        <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                        </span>
                        Sistem aktif &amp; siap inferensi
                    </span>
                </div>
            </aside>

            {/* ============ PANEL KANAN ============ */}
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
                    <div className="flex h-24 w-24 items-center justify-center rounded-[28px] border-[3px] border-emerald-600 bg-[#051a16] p-4 shadow-xl shadow-emerald-900/20">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src="/logo.png" alt="VERIDIX Logo" className="h-full w-full object-contain" />
                    </div>
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