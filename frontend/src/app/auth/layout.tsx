import type { CSSProperties } from "react";
import Link from "next/link";
import { ArrowLeft, Cpu, Eye, ScanLine, UserRound, ShieldCheck } from "lucide-react";

const FEATURES = [
    { icon: Cpu, label: "IndoBERT Fine-Tuned", desc: "Model bahasa Indonesia untuk klasifikasi hoaks" },
    { icon: Eye, label: "Transparansi LIME XAI", desc: "Alasan prediksi dapat ditelusuri kata demi kata" },
    { icon: ScanLine, label: "Ekstraksi Teks PaddleOCR", desc: "Periksa klaim dari tangkapan layar & gambar" },
];

// Satu halaman masuk dipakai dua jenis akun
const ROLES = [
    { icon: UserRound, label: "Pengguna", desc: "Deteksi berita & riwayat" },
    { icon: ShieldCheck, label: "Admin", desc: "Kelola data & model" },
];

// Jeda animasi masuk (ms) lewat CSS variable
const delay = (ms: number) => ({ "--d": `${ms}ms` }) as CSSProperties;

// Keyframes & kelas animasi. Otomatis mati bila pengguna memilih "kurangi gerakan" di sistemnya.
const ANIMATION_CSS = `
@keyframes auth-fade-up { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }
@keyframes auth-float { 0%, 100% { transform: translate3d(0, 0, 0); } 50% { transform: translate3d(0, -8px, 0); } }
@keyframes auth-drift-a { 0%, 100% { transform: translate3d(0, 0, 0) scale(1); } 50% { transform: translate3d(28px, 20px, 0) scale(1.1); } }
@keyframes auth-drift-b { 0%, 100% { transform: translate3d(0, 0, 0) scale(1); } 50% { transform: translate3d(-24px, -18px, 0) scale(1.08); } }
@keyframes auth-shimmer { to { background-position: 200% center; } }
.auth-fade-up { opacity: 0; animation: auth-fade-up .75s cubic-bezier(.22, 1, .36, 1) forwards; animation-delay: var(--d, 0ms); }
.auth-float { animation: auth-float 5s ease-in-out infinite; }
.auth-drift-a { animation: auth-drift-a 14s ease-in-out infinite; }
.auth-drift-b { animation: auth-drift-b 18s ease-in-out infinite; }
.auth-shimmer { background-size: 200% auto; animation: auth-shimmer 6s linear infinite; }
@media (prefers-reduced-motion: reduce) {
  .auth-fade-up { opacity: 1; animation: none; }
  .auth-float, .auth-drift-a, .auth-drift-b, .auth-shimmer { animation: none; }
}
`;

export default function AuthLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="grid min-h-screen grid-cols-1 bg-slate-50 lg:grid-cols-2">
            <style>{ANIMATION_CSS}</style>

            {/* ============ PANEL KIRI ============ */}
            <aside className="relative hidden overflow-hidden border-r border-white/10 bg-gradient-to-br from-[#04140f] via-[#0a2b23] to-[#0f4a39] text-white lg:sticky lg:top-0 lg:block lg:h-screen">

                {/* Latar: glow bergerak pelan + pola titik halus + kilau kaca */}
                <div className="pointer-events-none absolute inset-0">
                    <div className="auth-drift-a absolute -top-24 -left-20 h-[380px] w-[380px] rounded-full bg-emerald-400/25 blur-3xl" />
                    <div className="auth-drift-b absolute top-1/2 -right-28 h-[320px] w-[320px] rounded-full bg-cyan-300/10 blur-3xl" />
                    <div className="auth-drift-a absolute -bottom-32 left-1/4 h-[380px] w-[380px] rounded-full bg-teal-300/15 blur-3xl" />
                    <div
                        className="absolute inset-0 opacity-70"
                        style={{
                            backgroundImage: "radial-gradient(rgba(255,255,255,0.09) 1px, transparent 1px)",
                            backgroundSize: "24px 24px",
                            maskImage: "radial-gradient(ellipse at 30% 40%, black 10%, transparent 70%)",
                            WebkitMaskImage: "radial-gradient(ellipse at 30% 40%, black 10%, transparent 70%)",
                        }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-b from-white/[0.06] via-transparent to-black/25" />
                </div>

                {/* Isi: bisa digulir bila layar pendek, jarak antarbagian dijaga oleh gap */}
                <div className="relative flex h-full flex-col justify-between gap-8 overflow-y-auto p-10 xl:p-14 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">

                    {/* Baris atas: brand + status sistem */}
                    <div className="auth-fade-up flex items-center justify-between gap-4" style={delay(0)}>
                        <div className="flex items-center gap-3.5">
                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/20 bg-white/10 p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.25)] backdrop-blur-md">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src="/logo.png" alt="VERIDIX Logo" className="h-full w-full object-contain drop-shadow-sm" />
                            </div>
                            <div className="leading-tight">
                                <span className="block text-xl font-extrabold tracking-[0.14em]">VERIDIX</span>
                                <span className="mt-1 block text-[10px] font-semibold uppercase tracking-[0.26em] text-emerald-200/70">
                                    Deteksi Hoaks Politik
                                </span>
                            </div>
                        </div>

                        <span className="inline-flex shrink-0 items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3.5 py-1.5 text-[11px] font-medium backdrop-blur-md">
                            <span className="relative flex h-2 w-2">
                                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                            </span>
                            Sistem aktif
                        </span>
                    </div>

                    {/* Tengah: headline + fitur */}
                    <div>
                        <span
                            className="auth-fade-up inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-100 backdrop-blur-md"
                            style={delay(120)}
                        >
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_8px_rgba(110,231,183,0.9)]" />
                            Platform Cek Fakta Berbasis AI
                        </span>

                        <h2
                            className="auth-fade-up mt-6 text-4xl font-extrabold leading-[1.08] tracking-tight xl:text-5xl"
                            style={delay(220)}
                        >
                            Verifikasi Berita
                            <span className="auth-shimmer block bg-[linear-gradient(90deg,#a7f3d0,#5eead4,#a7f3d0)] bg-clip-text italic text-transparent">
                                Lebih Cerdas.
                            </span>
                        </h2>

                        <p
                            className="auth-fade-up mt-5 max-w-md text-[15px] leading-relaxed text-emerald-50/70 [@media(max-height:760px)]:hidden"
                            style={delay(320)}
                        >
                            Sistem deteksi disinformasi politik yang menggabungkan IndoBERT, penjelasan LIME, dan OCR gambar dalam satu platform terpadu.
                        </p>

                        <ul className="mt-7 max-w-md space-y-2.5">
                            {FEATURES.map(({ icon: Icon, label, desc }, i) => (
                                <li
                                    key={label}
                                    className="auth-fade-up group flex items-center gap-3.5 rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3 backdrop-blur-md transition duration-300 hover:-translate-y-0.5 hover:border-emerald-300/30 hover:bg-white/[0.1] hover:shadow-[0_10px_30px_-12px_rgba(16,185,129,0.45)]"
                                    style={delay(420 + i * 110)}
                                >
                                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-300/15 text-emerald-200 ring-1 ring-white/10 transition duration-300 group-hover:scale-110 group-hover:bg-emerald-300/25">
                                        <Icon size={17} strokeWidth={1.75} />
                                    </span>
                                    <span className="leading-snug">
                                        <span className="block text-sm font-semibold text-white">{label}</span>
                                        <span className="block text-xs text-emerald-100/60 [@media(max-height:820px)]:hidden">{desc}</span>
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Bawah: dua peran akun */}
                    <div className="auth-fade-up max-w-md" style={delay(780)}>
                        <p className="mb-3 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.24em] text-emerald-200/60">
                            Satu halaman masuk untuk dua peran
                            <span className="h-px flex-1 bg-white/10" />
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                            {ROLES.map(({ icon: Icon, label, desc }) => (
                                <div
                                    key={label}
                                    className="group flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-3.5 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] backdrop-blur-md transition duration-300 hover:-translate-y-0.5 hover:border-emerald-300/40 hover:bg-white/[0.15]"
                                >
                                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-300/40 to-teal-500/30 text-white ring-1 ring-white/20 transition duration-300 group-hover:scale-110">
                                        <Icon size={16} strokeWidth={1.75} />
                                    </span>
                                    <span className="leading-tight">
                                        <span className="block text-sm font-semibold text-white">{label}</span>
                                        <span className="block text-[11px] text-emerald-100/60">{desc}</span>
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </aside>

            {/* ============ PANEL KANAN ============ */}
            <main className="relative flex min-h-screen flex-col overflow-hidden bg-gradient-to-br from-white via-emerald-50/60 to-white px-6 py-6 sm:px-10">

                {/* Glow lembut yang bergerak pelan, serasi dengan sisi kiri */}
                <div className="pointer-events-none absolute inset-0">
                    <div className="auth-drift-b absolute -top-24 -right-24 h-72 w-72 rounded-full bg-emerald-200/40 blur-3xl" />
                    <div className="auth-drift-a absolute -bottom-28 -left-20 h-72 w-72 rounded-full bg-teal-200/30 blur-3xl" />
                </div>

                <div className="auth-fade-up relative flex justify-end" style={delay(100)}>
                    <Link
                        href="/"
                        className="group inline-flex items-center gap-1.5 rounded-xl border border-transparent px-3 py-1.5 text-xs font-medium text-emerald-700 transition hover:border-white hover:bg-white/70 hover:text-emerald-900"
                    >
                        <ArrowLeft size={14} className="transition-transform duration-300 group-hover:-translate-x-0.5" /> Beranda
                    </Link>
                </div>

                <div className="relative flex flex-1 flex-col items-center justify-center py-8">
                    <div className="auth-fade-up" style={delay(150)}>
                        <div className="auth-float flex h-20 w-20 items-center justify-center rounded-3xl border border-white/20 bg-gradient-to-br from-[#0a2b23] to-[#0f4a39] p-3.5 shadow-xl shadow-emerald-900/25 ring-1 ring-emerald-500/30">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src="/logo.png" alt="VERIDIX Logo" className="h-full w-full object-contain" />
                        </div>
                    </div>
                    <p className="auth-fade-up mt-3 text-lg font-extrabold tracking-[0.25em] text-emerald-950 lg:hidden" style={delay(220)}>
                        VERIDIX
                    </p>

                    <div className="auth-fade-up mt-8 w-full max-w-md" style={delay(300)}>
                        {children}
                    </div>
                </div>

                <p className="auth-fade-up relative pt-2 text-center text-xs text-slate-400" style={delay(450)}>
                    © 2026 VERIDIX · Hasil AI bukan pengganti verifikasi faktual.
                </p>
            </main>
        </div>
    );
}