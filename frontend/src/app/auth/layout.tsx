import type { CSSProperties } from "react";
import Link from "next/link";
import { ArrowLeft, Eye, ScanLine, UserRound, ShieldCheck } from "lucide-react";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";

const FEATURES = [
    { icon: AIAnalysisIcon, label: "Analisis pola IndoBERT", desc: "Klasifikasi pola disinformasi pada teks politik." },
    { icon: Eye, label: "Penjelasan kata dengan LIME", desc: "Telusuri kata yang memengaruhi keluaran model." },
    { icon: ScanLine, label: "Ekstraksi teks PaddleOCR", desc: "Baca gambar, lalu periksa dan sunting hasilnya." },
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
@keyframes auth-fade-up {
  from { opacity: 0; transform: translate3d(0, 18px, 0); filter: blur(6px); }
  to   { opacity: 1; transform: none; filter: blur(0); }
}
@keyframes auth-float { 0%, 100% { transform: translate3d(0, 0, 0); } 50% { transform: translate3d(0, -8px, 0); } }
@keyframes auth-drift-a { 0%, 100% { transform: translate3d(0, 0, 0) scale(1); } 50% { transform: translate3d(28px, 20px, 0) scale(1.1); } }
@keyframes auth-drift-b { 0%, 100% { transform: translate3d(0, 0, 0) scale(1); } 50% { transform: translate3d(-24px, -18px, 0) scale(1.08); } }
@keyframes auth-shimmer { to { background-position: 200% center; } }
@keyframes auth-orbit { to { transform: rotate(360deg); } }
@keyframes auth-pulse-dot { 0%, 100% { opacity: .5; transform: scale(1); } 50% { opacity: 1; transform: scale(1.35); } }
@keyframes auth-sheen {
  0%   { transform: translateX(-150%) skewX(-20deg); opacity: 0; }
  25%  { opacity: 1; }
  100% { transform: translateX(450%) skewX(-20deg); opacity: 0; }
}

.auth-fade-up { opacity: 0; animation: auth-fade-up .9s cubic-bezier(.22, 1, .36, 1) forwards; animation-delay: var(--d, 0ms); }
.auth-float { animation: auth-float 5s ease-in-out infinite; }
.auth-drift-a { animation: auth-drift-a 14s ease-in-out infinite; }
.auth-drift-b { animation: auth-drift-b 18s ease-in-out infinite; }
.auth-orbit { animation: auth-orbit 60s linear infinite; }
.auth-shimmer { background-size: 200% auto; animation: auth-shimmer 7s linear infinite; }
.auth-dot { animation: auth-pulse-dot 2.4s ease-in-out infinite; }

.auth-card {
  transition: transform .45s cubic-bezier(.22, 1, .36, 1), box-shadow .45s ease, border-color .35s ease, background-color .35s ease;
}
.auth-card:hover, .auth-card:focus-visible { transform: translateY(-3px); }
.auth-card:active { transform: translateY(0) scale(.985); transition-duration: .12s; }
.auth-sheen { transform: translateX(-150%) skewX(-20deg); opacity: 0; }
.auth-card:hover .auth-sheen { animation: auth-sheen 1s ease-out; }

@media (prefers-reduced-motion: reduce) {
  .auth-fade-up { opacity: 1; animation: none; filter: none; }
  .auth-float, .auth-drift-a, .auth-drift-b, .auth-orbit, .auth-shimmer, .auth-dot { animation: none; }
  .auth-card, .auth-card:hover, .auth-card:focus-visible, .auth-card:active { transition: none; transform: none; }
  .auth-card:hover .auth-sheen { animation: none; }
}
`;

export default function AuthLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="grid min-h-screen grid-cols-1 bg-slate-50 lg:grid-cols-2">
            <style>{ANIMATION_CSS}</style>

            {/* ============ PANEL KIRI (informasi, hijau) ============ */}
            <aside className="relative isolate hidden overflow-hidden bg-gradient-to-br from-emerald-600 via-emerald-700 to-emerald-900 text-white lg:sticky lg:top-0 lg:block lg:h-screen">
                {/* Dekorasi: cahaya lembut, kisi tipis, orbit & ikon samar */}
                <div aria-hidden="true" className="pointer-events-none absolute inset-0">
                    <div className="auth-drift-a absolute -left-24 -top-24 h-96 w-96 rounded-full bg-emerald-400/25 blur-3xl" />
                    <div className="auth-drift-b absolute -bottom-32 -right-16 h-96 w-96 rounded-full bg-emerald-300/15 blur-3xl" />
                    <div
                        className="absolute inset-0"
                        style={{
                            backgroundImage:
                                "linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px)",
                            backgroundSize: "48px 48px",
                            maskImage: "radial-gradient(ellipse at 30% 20%, black, transparent 75%)",
                            WebkitMaskImage: "radial-gradient(ellipse at 30% 20%, black, transparent 75%)",
                        }}
                    />
                    <div className="absolute -right-32 top-[18%] h-[26rem] w-[26rem] text-white/[0.07]">
                        <span className="absolute inset-0 rounded-full border border-white/10" />
                        <span className="auth-orbit absolute -inset-8 rounded-full border border-dashed border-white/15" />
                        <AIAnalysisIcon className="h-full w-full p-14" />
                    </div>
                </div>

                <div className="relative flex h-full flex-col justify-between gap-8 overflow-y-auto p-10 xl:p-14 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                    {/* Identitas */}
                    <header className="auth-fade-up flex shrink-0 items-center justify-between gap-4" style={delay(0)}>
                        <div className="flex items-center gap-3.5">
                            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#0a2b23] p-2.5 shadow-lg shadow-emerald-950/30 ring-1 ring-white/20">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src="/logo.png" alt="" className="h-full w-full object-contain" />
                            </span>
                            <div className="leading-tight">
                                <span className="block text-lg font-bold tracking-[0.2em] text-white">VERIDIX</span>
                                <span className="mt-1 block text-[10px] font-medium uppercase tracking-[0.18em] text-emerald-100/80">
                                    Analisis disinformasi politik
                                </span>
                            </div>
                        </div>
                        <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald-50 backdrop-blur-md">
                            <span aria-hidden="true" className="auth-dot h-1.5 w-1.5 rounded-full bg-emerald-300" />
                            Teks &amp; gambar
                        </span>
                    </header>

                    {/* Pesan utama + kemampuan */}
                    <section className="shrink-0">
                        <p className="auth-fade-up flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-emerald-200" style={delay(100)}>
                            <span aria-hidden="true" className="h-px w-8 bg-emerald-300/70" />
                            IndoBERT · LIME · OCR
                        </p>

                        <h2 className="auth-fade-up mt-5 text-4xl font-semibold leading-[1.1] tracking-[-0.03em] text-white xl:text-5xl" style={delay(180)}>
                            Baca polanya.
                            <span className="auth-shimmer mt-1 block bg-gradient-to-r from-emerald-200 via-white to-emerald-200 bg-clip-text text-transparent">
                                Telusuri alasannya.
                            </span>
                        </h2>

                        <p className="auth-fade-up mt-5 max-w-md text-sm leading-7 text-emerald-50/80 [@media(max-height:760px)]:hidden" style={delay(260)}>
                            Mulai dari teks atau gambar. Periksa hasilnya dan telusuri kata yang memengaruhi keputusan model.
                        </p>

                        <ul className="mt-7 max-w-md space-y-3 [@media(max-height:700px)]:mt-5 [@media(max-height:700px)]:space-y-2">
                            {FEATURES.map(({ icon: Icon, label, desc }, i) => (
                                <li
                                    key={label}
                                    tabIndex={0}
                                    className="auth-fade-up auth-card group relative flex cursor-default items-center gap-3.5 overflow-hidden rounded-2xl border border-white/15 bg-white/10 p-3.5 backdrop-blur-md hover:border-white/40 hover:bg-white/[0.16] hover:shadow-xl hover:shadow-emerald-950/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
                                    style={delay(340 + i * 90)}
                                >
                                    <span aria-hidden="true" className="auth-sheen pointer-events-none absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                                    <span
                                        aria-hidden="true"
                                        className="relative grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white/15 text-emerald-50 ring-1 ring-white/20 transition-colors duration-300 group-hover:bg-white group-hover:text-emerald-700 group-hover:ring-white"
                                    >
                                        <Icon className={Icon === AIAnalysisIcon ? "h-7 w-7" : "h-5 w-5 stroke-[1.6]"} />
                                    </span>
                                    <div className="relative min-w-0 flex-1">
                                        <p className="text-sm font-semibold leading-5 text-white">{label}</p>
                                        <p className="mt-0.5 text-xs leading-5 text-emerald-100/75 [@media(max-height:820px)]:hidden">{desc}</p>
                                    </div>
                                    <span aria-hidden="true" className="relative font-mono text-[10px] tracking-wider text-emerald-200/60 transition-colors duration-300 group-hover:text-white">
                                        {String(i + 1).padStart(2, "0")}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </section>

                    {/* Peran akun */}
                    <section className="auth-fade-up max-w-md shrink-0" style={delay(650)}>
                        <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-200/90">
                            Akses sesuai peran akun
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                            {ROLES.map(({ icon: Icon, label, desc }) => (
                                <div
                                    key={label}
                                    tabIndex={0}
                                    className="auth-card group flex cursor-default items-start gap-2.5 rounded-2xl border border-white/15 bg-white/[0.07] p-3.5 hover:border-white/35 hover:bg-white/[0.14] hover:shadow-lg hover:shadow-emerald-950/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
                                >
                                    <Icon
                                        aria-hidden="true"
                                        className="mt-0.5 h-4 w-4 shrink-0 text-emerald-200 transition-transform duration-300 group-hover:scale-110 group-hover:text-white"
                                        strokeWidth={1.8}
                                    />
                                    <div className="min-w-0">
                                        <p className="text-xs font-semibold text-white">{label}</p>
                                        <p className="mt-0.5 text-[11px] leading-5 text-emerald-100/75">{desc}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>
            </aside>

            {/* ============ PANEL KANAN (form, tidak diubah) ============ */}
            <main className="relative flex min-h-screen flex-col overflow-hidden bg-gradient-to-br from-white via-emerald-50/60 to-white px-6 py-6 sm:px-10">

                {/* Glow lembut yang bergerak pelan */}
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