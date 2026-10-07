import Image from "next/image";
import Link from "next/link";
import { Highlighter, History, ScanText } from "lucide-react";

export const metadata = { title: "VERIDIX · Deteksi Hoaks Politik" };

const features = [
    { icon: ScanText, title: "Teks dan screenshot", desc: "Tempel berita atau unggah gambar, teks dibaca otomatis." },
    { icon: Highlighter, title: "Penjelasan LIME", desc: "Lihat kata yang mendorong hasil hoaks atau fakta." },
    { icon: History, title: "Riwayat dan laporan", desc: "Simpan hasil, bagikan tautan, unduh PDF." },
];

function Logo({ onLight = false }: { onLight?: boolean }) {
    return (
        <span className="flex items-center gap-3">
            <span className={`grid h-11 w-11 place-items-center rounded-2xl p-1.5 ring-1 ${onLight ? "bg-[#0b2520] ring-emerald-900/40" : "bg-white/10 ring-white/20"}`}>
                <Image src="/logo.png" alt="Logo VERIDIX" width={44} height={44} priority className="h-full w-full object-contain" />
            </span>
            <span className="leading-tight">
                <span className={`block text-lg font-bold tracking-wide ${onLight ? "text-slate-900" : "text-white"}`}>VERIDIX</span>
                <span className={`block text-xs ${onLight ? "text-slate-500" : "text-emerald-200/70"}`}>Deteksi hoaks politik</span>
            </span>
        </span>
    );
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex min-h-dvh bg-[#f4f7f6]">
            {/* Panel merek: hanya tampil di layar lebar */}
            <aside className="relative hidden w-[46%] overflow-hidden bg-[#0b2520] text-emerald-50 lg:flex xl:w-1/2">
                <div aria-hidden className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-emerald-500/20 blur-3xl" />
                <div aria-hidden className="pointer-events-none absolute -bottom-32 -right-16 h-96 w-96 rounded-full bg-teal-400/10 blur-3xl" />
                <div aria-hidden className="absolute inset-0 opacity-[0.07] [background-image:radial-gradient(#fff_1px,transparent_1px)] [background-size:22px_22px]" />

                <div className="relative z-10 flex w-full flex-col justify-between p-10 xl:p-14">
                    <Logo />

                    <div className="max-w-md">
                        <h2 className="text-3xl font-semibold leading-tight text-white xl:text-4xl">
                            Periksa berita politik sebelum Anda membagikannya.
                        </h2>
                        <p className="mt-3 text-sm leading-relaxed text-emerald-100/70">
                            Deteksi hoaks berbasis IndoBERT dengan penjelasan kata pemicu, riwayat pribadi, dan laporan yang bisa dibagikan.
                        </p>

                        <div className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur">
                            <div className="mb-3 flex items-center justify-between">
                                <span className="text-xs font-medium text-emerald-200/70">Contoh hasil analisis</span>
                                <span className="rounded-full bg-rose-400/15 px-2.5 py-1 text-xs font-bold text-rose-300 ring-1 ring-rose-300/30">HOAKS · 93.4%</span>
                            </div>
                            <div className="mb-4 flex flex-wrap gap-1.5 text-xs">
                                {["viral", "bocor", "terbongkar"].map((w) => <span key={w} className="rounded-md bg-rose-400/20 px-2 py-1 text-rose-200">{w}</span>)}
                                {["resmi", "konferensi"].map((w) => <span key={w} className="rounded-md bg-emerald-400/20 px-2 py-1 text-emerald-200">{w}</span>)}
                            </div>
                            <div className="space-y-2 text-xs">
                                <div className="flex items-center gap-3"><span className="w-10">Hoaks</span><div className="h-1.5 flex-1 rounded-full bg-white/10"><div className="h-1.5 w-[93%] rounded-full bg-rose-400" /></div><span className="w-10 text-right">93.4%</span></div>
                                <div className="flex items-center gap-3"><span className="w-10">Fakta</span><div className="h-1.5 flex-1 rounded-full bg-white/10"><div className="h-1.5 w-[7%] rounded-full bg-emerald-400" /></div><span className="w-10 text-right">6.6%</span></div>
                            </div>
                        </div>
                    </div>

                    <ul className="space-y-3">
                        {features.map(({ icon: Icon, title, desc }) => (
                            <li key={title} className="flex items-start gap-3">
                                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-300/20"><Icon size={17} /></span>
                                <span className="text-sm"><b className="font-medium text-white">{title}</b><span className="block text-xs text-emerald-100/60">{desc}</span></span>
                            </li>
                        ))}
                    </ul>
                </div>
            </aside>

            {/* Area formulir */}
            <main className="flex min-w-0 flex-1 flex-col">
                <header className="flex items-center justify-between px-5 py-4 sm:px-8">
                    <Link href="/" className="lg:hidden"><Logo onLight /></Link>
                    <Link href="/" className="ml-auto text-sm font-medium text-slate-500 transition hover:text-emerald-700">
                        Lanjut sebagai tamu →
                    </Link>
                </header>
                <div className="flex flex-1 items-center justify-center px-5 pb-8 sm:px-8">
                    <div className="w-full max-w-md rounded-3xl border border-slate-200/80 bg-white p-6 shadow-xl shadow-emerald-900/5 sm:p-8">
                        {children}
                    </div>
                </div>
                <footer className="px-5 pb-5 text-center text-xs text-slate-400">
                    © VERIDIX · Hasil berbasis pola bahasa, bukan pengganti verifikasi faktual.
                </footer>
            </main>
        </div>
    );
}