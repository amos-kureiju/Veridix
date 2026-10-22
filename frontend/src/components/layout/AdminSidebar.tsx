"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    FileText,
    MessageSquare,
    Sliders,
    Users,
    Download,
    LogOut,
    Sparkles,
    Search,
    ExternalLink
} from "lucide-react";

interface AdminSidebarProps {
    onLogout?: () => void;
}

export default function AdminSidebar({ onLogout }: AdminSidebarProps) {
    const pathname = usePathname();

    const adminMenu = [
        { label: "Dashboard", href: "/admin", icon: LayoutDashboard },
        { label: "Log Deteksi Global", href: "/admin/logs", icon: FileText },
        { label: "Kelola Masukan", href: "/admin/feedback", icon: MessageSquare, badge: "8" },
        { label: "Kontrol Threshold", href: "/admin/threshold", icon: Sliders },
        { label: "Kelola Pengguna", href: "/admin/users", icon: Users },
        { label: "Ekspor Laporan", href: "/admin/export", icon: Download },
    ];

    return (
        <aside className="relative z-20 w-64 h-screen flex flex-col justify-between p-3.5 border-r border-emerald-900/10 text-slate-600 select-none shrink-0 font-sans shadow-[4px_0_24px_-12px_rgba(6,78,59,0.25)]">

            {/* Latar: dasar putih kehijauan + glow berwarna yang jelas, lalu lapisan kaca tipis yang membuat blur terlihat */}
            <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-gradient-to-b from-emerald-50 via-teal-50 to-emerald-100">
                <div className="absolute -top-16 -left-12 h-72 w-72 rounded-full bg-emerald-400/45 blur-3xl" />
                <div className="absolute top-1/3 -right-24 h-64 w-64 rounded-full bg-teal-300/45 blur-3xl" />
                <div className="absolute top-2/3 -left-20 h-60 w-60 rounded-full bg-lime-200/50 blur-3xl" />
                <div className="absolute -bottom-24 -right-10 h-72 w-72 rounded-full bg-emerald-500/30 blur-3xl" />
                <div className="absolute inset-0 bg-gradient-to-b from-white/35 via-white/15 to-white/25 backdrop-blur-2xl" />
                {/* Kilau tipis di tepi kiri */}
                <div className="absolute inset-y-0 left-0 w-px bg-gradient-to-b from-white via-white/40 to-white" />
            </div>

            {/* 1. BRAND LOGO & PENCARIAN */}
            <div className="space-y-5 overflow-y-auto pr-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">

                {/* Header Monogram VERIDIX */}
                <div className="flex items-center gap-2.5 px-1 pt-1 pb-4 border-b border-emerald-900/10">
                    <div className="w-9 h-9 rounded-xl bg-white/60 border border-white shadow-[0_2px_10px_-2px_rgba(5,150,105,0.35),inset_0_1px_0_rgba(255,255,255,0.9)] flex items-center justify-center p-1.5 shrink-0 backdrop-blur-md">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src="/logo.png" alt="VERIDIX Logo" className="w-full h-full object-contain drop-shadow-sm" />
                    </div>
                    <div className="leading-tight">
                        <div className="flex items-center gap-1.5">
                            <span className="text-sm font-extrabold text-emerald-950 tracking-wider">VERIDIX</span>
                            <span className="text-[10px] bg-emerald-950 text-emerald-100 font-mono px-1.5 py-0.5 rounded-md font-bold leading-none shadow-sm">
                                ADMIN
                            </span>
                        </div>
                        <p className="text-[10px] text-emerald-700/70 font-medium">Fact Intelligence Ops</p>
                    </div>
                </div>

                {/* Status AI Engine Banner */}
                <div className="bg-white/45 border border-white/80 rounded-2xl p-3 flex items-center gap-2.5 text-xs text-emerald-900 shadow-[0_4px_16px_-8px_rgba(5,150,105,0.35)] backdrop-blur-md">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 text-white flex items-center justify-center shrink-0 shadow-sm ring-1 ring-white/60">
                        <Sparkles className="w-3.5 h-3.5" strokeWidth={1.75} />
                    </div>
                    <div className="leading-tight truncate">
                        <p className="font-bold text-emerald-950 truncate">IndoBERT Engine v2</p>
                        <p className="text-[10px] text-emerald-700 truncate">Status: Siap Inferensi</p>
                    </div>
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] animate-pulse shrink-0" />
                </div>

                {/* Navigasi Utama Panel Admin */}
                <div>
                    <p className="text-[11px] font-semibold text-emerald-800/50 tracking-wide px-3 mb-2">
                        Main Management
                    </p>
                    <nav className="space-y-1">
                        {adminMenu.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`relative overflow-hidden flex items-center justify-between px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-200 group ${isActive
                                        ? "bg-gradient-to-r from-white/70 via-emerald-200/40 to-emerald-400/50 text-emerald-950 ring-1 ring-white/80 shadow-[0_4px_14px_-6px_rgba(5,150,105,0.4)]"
                                        : "text-slate-600 hover:bg-white/55 hover:text-emerald-950"
                                        }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <Icon
                                            strokeWidth={1.75}
                                            className={`w-[18px] h-[18px] shrink-0 transition-colors ${isActive ? "text-emerald-700" : "text-slate-400 group-hover:text-emerald-700"}`}
                                        />
                                        <span>{item.label}</span>
                                    </div>

                                    {item.badge && !isActive && (
                                        <span className="text-[10px] min-w-[20px] text-center px-1.5 py-0.5 bg-emerald-500/15 text-emerald-700 font-semibold rounded-full ring-1 ring-emerald-500/20">
                                            {item.badge}
                                        </span>
                                    )}

                                    {/* Garis aksen di sisi kanan untuk menu aktif */}
                                    {isActive && (
                                        <span className="absolute right-0 top-0 h-full w-[3px] bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.6)]" />
                                    )}
                                </Link>
                            );
                        })}
                    </nav>
                </div>

                {/* Tautan Kembali ke Sisi Pengguna */}
                <div className="pt-4 border-t border-emerald-900/10">
                    <Link
                        href="/"
                        className="group flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium text-slate-500 hover:text-emerald-950 hover:bg-white/55 transition"
                    >
                        <ExternalLink strokeWidth={1.75} className="w-[18px] h-[18px] shrink-0 text-slate-400 group-hover:text-emerald-700 transition-colors" />
                        <span>Kembali ke Beranda User</span>
                    </Link>
                </div>

            </div>

            {/* 2. FOOTER KARTU ADMIN */}
            <div className="pt-3">
                <div className="bg-white/45 border border-white/80 rounded-2xl p-2.5 flex items-center justify-between shadow-[0_4px_16px_-8px_rgba(5,150,105,0.35)] backdrop-blur-md">
                    <div className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 border border-white/80 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">
                            A
                        </div>
                        <div className="leading-tight truncate max-w-[110px]">
                            <p className="text-xs font-semibold text-emerald-950 truncate">Administrator</p>
                            <p className="text-[10px] text-slate-500 truncate">Super Admin</p>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={onLogout}
                        className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50/90 rounded-lg transition"
                        title="Keluar Admin"
                    >
                        <LogOut className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

        </aside>
    );
}