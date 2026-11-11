"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    ArrowRight,
    BookOpen,
    History,
    LogIn,
    MessageSquareQuote,
    Settings2,
    UserRound,
} from "lucide-react";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";

const PAGE_INFO: Record<
    string,
    { title: string; description: string }
> = {
    "/": {
        title: "Memahami hasil analisis",
        description:
            "Periksa hasil OCR sebelum analisis. Hasil model menunjukkan kemiripan pola penulisan; bandingkan dengan sumber asli dan konteks lengkap.",
    },
    "/history": {
        title: "Mengelola riwayat",
        description:
            "Cocokkan naskah, sumber masukan, dan hasil pada detail riwayat. Penghapusan riwayat mencakup feedback yang terkait.",
    },
    "/feedback": {
        title: "Pratinjau feedback",
        description:
            "Halaman ini masih menampilkan data contoh untuk memperkenalkan status peninjauan feedback.",
    },
    "/profile": {
        title: "Mengelola informasi akun",
        description:
            "Periksa kembali informasi akun sebelum menyimpan perubahan profil atau kata sandi.",
    },
    "/settings": {
        title: "Penyimpanan preferensi",
        description:
            "Preferensi pada halaman ini disimpan di browser yang sedang digunakan dan dapat hilang ketika data browser dibersihkan.",
    },
    "/help": {
        title: "Membaca penjelasan model",
        description:
            "LIME menjelaskan pengaruh kata terhadap keluaran model. Periksa kebenaran klaim melalui sumber asli dan konteks lengkap.",
    },
};

type IconType = ComponentType<{ className?: string }>;

type NavItem = {
    href: string;
    label: string;
    icon: IconType;
};

type NavGroup = {
    title: string;
    items: NavItem[];
};

const FOCUS_RING =
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50";

export default function Footer({
    guest = false,
}: {
    guest?: boolean;
}) {
    const pathname = usePathname();

    const info =
        pathname === "/history" && guest
            ? {
                title: "Pratinjau riwayat",
                description:
                    "Mode tamu menampilkan contoh riwayat. Masuk ke akun untuk melakukan analisis dan mengelola riwayat Anda.",
            }
            : PAGE_INFO[pathname] ?? PAGE_INFO["/"];

    // Tamu hanya melihat halaman yang memang dapat diakses tanpa login
    const groups: NavGroup[] = [
        {
            title: "Jelajahi",
            items: [
                {
                    href: "/",
                    label: "Deteksi berita",
                    icon: AIAnalysisIcon,
                },
                {
                    href: "/history",
                    label: guest ? "Pratinjau riwayat" : "Riwayat analisis",
                    icon: History,
                },
                ...(guest
                    ? []
                    : [
                        {
                            href: "/feedback",
                            label: "Feedback",
                            icon: MessageSquareQuote,
                        },
                    ]),
            ],
        },
        {
            title: "Akun & bantuan",
            items: [
                ...(guest
                    ? [
                        {
                            href: "/auth/login",
                            label: "Masuk akun",
                            icon: LogIn,
                        },
                    ]
                    : [
                        {
                            href: "/profile",
                            label: "Profil saya",
                            icon: UserRound,
                        },
                        {
                            href: "/settings",
                            label: "Pengaturan",
                            icon: Settings2,
                        },
                    ]),
                {
                    href: "/help",
                    label: "Panduan penggunaan",
                    icon: BookOpen,
                },
            ],
        },
    ];

    return (
        <footer className="mt-8 shrink-0 overflow-hidden rounded-[28px] border-2 border-white bg-gradient-to-br from-emerald-100 via-emerald-50 to-teal-100 p-2 shadow-[0_20px_60px_-32px_rgba(5,150,105,0.35)] sm:rounded-[32px] sm:p-3">
            {/* Informasi sesuai halaman */}
            <section
                aria-labelledby="footer-info-title"
                className="px-4 py-9 text-center sm:px-8 sm:py-12"
            >
                <h2
                    id="footer-info-title"
                    className="mx-auto max-w-xl text-2xl font-semibold leading-tight tracking-tight text-emerald-950 sm:text-3xl"
                >
                    {info.title}
                </h2>

                <p className="mx-auto mt-3 max-w-xl text-xs leading-relaxed text-slate-600 sm:text-sm">
                    {info.description}
                </p>

                <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                    <Link
                        href={guest ? "/auth/login" : "/"}
                        className={`inline-flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-xs font-semibold text-white shadow-md shadow-emerald-700/25 transition hover:bg-emerald-700 ${FOCUS_RING}`}
                    >
                        {guest ? "Masuk untuk analisis" : "Buka deteksi berita"}
                        <ArrowRight aria-hidden="true" className="h-4 w-4" />
                    </Link>

                    <Link
                        href="/help"
                        className={`inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-xs font-semibold text-slate-700 shadow-md shadow-emerald-900/10 ring-4 ring-white/50 transition hover:text-emerald-700 ${FOCUS_RING}`}
                    >
                        <BookOpen aria-hidden="true" className="h-4 w-4" />
                        Panduan penggunaan
                    </Link>
                </div>
            </section>

            {/* Panel identitas & navigasi */}
            <div className="rounded-3xl bg-white/75 p-5 backdrop-blur-sm sm:p-7">
                <div className="grid gap-8 lg:grid-cols-[1.3fr_1fr_1fr] lg:gap-10">
                    {/* Identitas aplikasi */}
                    <div className="max-w-sm">
                        <Link
                            href="/"
                            className={`inline-flex items-center gap-3 rounded-xl ${FOCUS_RING}`}
                        >
                            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-800 text-emerald-50">
                                <AIAnalysisIcon className="h-6 w-6" />
                            </span>
                            <span className="text-base font-bold tracking-wide text-emerald-950">
                                VERIDIX
                            </span>
                        </Link>

                        <p className="mt-4 text-xs leading-relaxed text-slate-600">
                            Membantu memahami pola penulisan berita politik dan
                            pengaruh kata terhadap hasil model.
                        </p>
                        <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
                            Gunakan hasil analisis sebagai pendamping
                            pemeriksaan informasi, bukan satu-satunya dasar
                            kesimpulan.
                        </p>
                    </div>

                    {/* Kelompok tautan */}
                    {groups.map(group => (
                        <nav
                            key={group.title}
                            aria-label={group.title}
                            className="min-w-0"
                        >
                            <h3 className="mb-3 text-xs font-semibold text-slate-800">
                                {group.title}
                            </h3>

                            <ul className="space-y-1">
                                {group.items.map(item => {
                                    const Icon = item.icon;
                                    const active = pathname === item.href;

                                    return (
                                        <li key={item.href}>
                                            <Link
                                                href={item.href}
                                                aria-current={
                                                    active ? "page" : undefined
                                                }
                                                className={`flex items-center gap-2.5 rounded-xl px-2 py-2 text-xs transition ${FOCUS_RING} ${active
                                                        ? "bg-emerald-50 font-semibold text-emerald-800"
                                                        : "text-slate-600 hover:bg-emerald-50/70 hover:text-emerald-800"
                                                    }`}
                                            >
                                                <span
                                                    aria-hidden="true"
                                                    className="flex h-5 w-5 shrink-0 items-center justify-center"
                                                >
                                                    <Icon
                                                        className={
                                                            item.href === "/"
                                                                ? "h-5 w-5"
                                                                : "h-4 w-4"
                                                        }
                                                    />
                                                </span>
                                                <span>{item.label}</span>
                                            </Link>
                                        </li>
                                    );
                                })}
                            </ul>
                        </nav>
                    ))}
                </div>

                {/* Informasi bawah */}
                <div className="mt-7 flex flex-col items-center justify-between gap-1.5 border-t border-slate-200/70 pt-4 text-center text-[11px] text-slate-500 sm:flex-row sm:text-left">
                    <span>© {new Date().getUTCFullYear()} VERIDIX</span>
                    <span>
                        {guest ? "Mode Tamu" : "Area Pengguna"}
                        {" · "}Analisis pola berita politik
                    </span>
                </div>
            </div>
        </footer>
    );
}