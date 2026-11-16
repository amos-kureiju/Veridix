"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";
import {
    LayoutDashboard,
    FileText,
    MessageSquare,
    Sliders,
    Users,
    Download,
    LogOut,
    Search,
    ExternalLink,
    PanelLeftClose,
    PanelLeftOpen,
} from "lucide-react";

interface AdminSidebarProps {
    onLogout?: () => void;
    // Opsional: kalau diisi, state collapse dikontrol dari luar (AdminShell)
    collapsed?: boolean;
    onToggleCollapse?: () => void;
    // Data admin dinamis (dari useAuth lewat AdminShell)
    userName?: string;
    userRole?: string;
}

export default function AdminSidebar({
    onLogout,
    collapsed: collapsedProp,
    onToggleCollapse,
    userName = "Administrator",
    userRole = "Admin",
}: AdminSidebarProps) {
    const pathname = usePathname();
    const [internalCollapsed, setInternalCollapsed] = useState(false);
    const collapsed = collapsedProp ?? internalCollapsed;
    const toggleCollapsed = () => {
        if (onToggleCollapse) onToggleCollapse();
        else setInternalCollapsed((prev) => !prev);
    };

    const adminMenu = [
        { label: "Dashboard", href: "/admin", icon: LayoutDashboard },
        { label: "Log Deteksi Global", href: "/admin/logs", icon: FileText },
        { label: "Kelola Masukan", href: "/admin/feedback", icon: MessageSquare, badge: "8" },
        { label: "Kontrol Threshold", href: "/admin/threshold", icon: Sliders },
        { label: "Kelola Pengguna", href: "/admin/users", icon: Users },
        { label: "Ekspor Laporan", href: "/admin/export", icon: Download },
    ];

    return (
        <aside
            className={`${collapsed ? "w-20" : "w-64"
                } relative z-20 h-screen flex flex-col justify-between p-3.5 border-r border-slate-900/[0.08] text-slate-600 select-none shrink-0 font-sans shadow-[4px_0_28px_-14px_rgba(15,23,42,0.22)] transition-[width] duration-300 ease-in-out`}
        >

            {/* Latar: putih bening dengan glow sangat tipis, lalu lapisan kaca blur */}
            <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-gradient-to-b from-white via-slate-50/80 to-white">
                <div className="absolute -top-20 -left-16 h-64 w-64 rounded-full bg-slate-200/60 blur-3xl" />
                <div className="absolute top-1/2 -right-24 h-56 w-56 rounded-full bg-emerald-100/40 blur-3xl" />
                <div className="absolute -bottom-24 -left-10 h-64 w-64 rounded-full bg-slate-300/30 blur-3xl" />
                <div className="absolute inset-0 bg-white/50 backdrop-blur-2xl" />
                {/* Kilau tipis di tepi kiri */}
                <div className="absolute inset-y-0 left-0 w-px bg-gradient-to-b from-white via-white/50 to-white" />
            </div>

            {/* 1. BRAND LOGO & MENU */}
            <div
                className={`space-y-5 pr-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden ${collapsed ? "overflow-visible" : "overflow-y-auto overflow-x-hidden"
                    }`}
            >

                {/* Header Monogram VERIDIX & Tombol Kecilkan Sidebar */}
                <div
                    className={`flex items-center pt-1 pb-4 border-b border-slate-900/[0.08] ${collapsed ? "flex-col gap-3" : "justify-between px-1"
                        }`}
                >
                    <div className={`flex items-center ${collapsed ? "" : "gap-2.5"}`}>
                        <div className="w-9 h-9 rounded-xl bg-white/70 border border-white shadow-[0_2px_10px_-2px_rgba(15,23,42,0.18),inset_0_1px_0_rgba(255,255,255,0.9)] flex items-center justify-center p-1.5 shrink-0 backdrop-blur-md">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src="/logo.png" alt="VERIDIX Logo" className="w-full h-full object-contain drop-shadow-sm" />
                        </div>
                        {!collapsed && (
                            <div className="leading-tight">
                                <div className="flex items-center gap-1.5">
                                    <span className="text-sm font-extrabold text-slate-900 tracking-wider">VERIDIX</span>
                                    <span className="text-[10px] bg-slate-900 text-white font-mono px-1.5 py-0.5 rounded-md font-bold leading-none shadow-sm">
                                        ADMIN
                                    </span>
                                </div>
                                <p className="text-[10px] text-slate-500 font-medium">Fact Intelligence Ops</p>
                            </div>
                        )}
                    </div>

                    <button
                        type="button"
                        onClick={toggleCollapsed}
                        className="p-1.5 rounded-lg border border-emerald-900/10 bg-white/50 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10 hover:border-emerald-400/30 active:scale-90 outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/50 transition-all duration-200 shrink-0"
                        title={collapsed ? "Perluas sidebar" : "Sembunyikan sidebar"}
                        aria-label={collapsed ? "Perluas sidebar" : "Sembunyikan sidebar"}
                    >
                        {collapsed ? (
                            <PanelLeftOpen className="w-4 h-4" />
                        ) : (
                            <PanelLeftClose className="w-4 h-4" />
                        )}
                    </button>
                </div>

                {/* Status AI Engine Banner */}
                <div
                    title={collapsed ? "IndoBERT Engine v2 — Siap Inferensi" : undefined}
                    className={`group bg-white/60 border border-white/90 rounded-2xl flex items-center text-xs text-slate-700 shadow-[0_4px_16px_-8px_rgba(15,23,42,0.22)] backdrop-blur-md transition-all duration-300 hover:border-emerald-300/60 hover:shadow-[0_6px_20px_-8px_rgba(16,185,129,0.35)] ${collapsed ? "justify-center p-2.5" : "p-3 gap-2.5"
                        }`}
                >
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 text-white flex items-center justify-center shrink-0 shadow-sm transition-all duration-300 group-hover:from-emerald-400 group-hover:to-emerald-600">
                        <AIAnalysisIcon className="h-6 w-6" />
                    </div>
                    {!collapsed && (
                        <>
                            <div className="leading-tight truncate">
                                <p className="font-bold text-slate-900 truncate">IndoBERT Engine v2</p>
                                <p className="text-[10px] text-slate-500 truncate">Status: Siap Inferensi</p>
                            </div>
                            <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] animate-pulse shrink-0" />
                        </>
                    )}
                </div>

                {/* Navigasi Utama Panel Admin */}
                <div>
                    {!collapsed ? (
                        <p className="text-[11px] font-semibold text-emerald-700/60 tracking-wide px-3 mb-2">
                            Main Management
                        </p>
                    ) : (
                        <div className="mx-auto mb-2 h-px w-6 bg-slate-900/10" />
                    )}
                    <nav className="space-y-1">
                        {adminMenu.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    title={collapsed ? item.label : undefined}
                                    className={`relative flex items-center rounded-xl text-[13px] font-medium transition-all duration-300 ease-out group outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/50 active:scale-[0.98] ${collapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
                                        } ${isActive
                                            ? "bg-gradient-to-r from-white/70 via-emerald-200/35 to-emerald-400/45 text-emerald-950 ring-1 ring-emerald-300/40 shadow-[0_4px_16px_-6px_rgba(16,185,129,0.45)]"
                                            : "text-emerald-700 hover:bg-emerald-500/[0.09] hover:text-emerald-900 hover:ring-1 hover:ring-emerald-400/20 active:bg-emerald-500/20"
                                        }`}
                                >
                                    <div className={`flex items-center ${collapsed ? "" : "gap-3"}`}>
                                        <Icon
                                            strokeWidth={1.75}
                                            className={`w-[18px] h-[18px] shrink-0 transition-all duration-300 ${isActive
                                                ? "text-emerald-600 drop-shadow-[0_0_6px_rgba(16,185,129,0.55)]"
                                                : "text-emerald-600 group-hover:text-emerald-500 group-hover:scale-110 group-hover:drop-shadow-[0_0_6px_rgba(16,185,129,0.4)] group-active:scale-95"
                                                }`}
                                        />
                                        {!collapsed && <span>{item.label}</span>}
                                    </div>

                                    {!collapsed && item.badge && !isActive && (
                                        <span className="text-[10px] min-w-[20px] text-center px-1.5 py-0.5 bg-slate-900 text-white rounded-full font-bold shadow-sm transition-colors duration-300 group-hover:bg-emerald-600">
                                            {item.badge}
                                        </span>
                                    )}

                                    {/* Garis aksen di sisi kanan untuk menu aktif */}
                                    {isActive && (
                                        <span className="absolute right-0 top-0 h-full w-[3px] rounded-r-xl bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.7)]" />
                                    )}

                                    {/* Badge kecil di pojok saat collapsed */}
                                    {collapsed && item.badge && (
                                        <span className="absolute top-1 right-1 w-3.5 h-3.5 flex items-center justify-center text-[8px] bg-emerald-600 text-white font-bold rounded-full">
                                            {item.badge}
                                        </span>
                                    )}

                                    {/* Tooltip kaca saat collapsed */}
                                    {collapsed && (
                                        <span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-lg bg-white/90 backdrop-blur-xl ring-1 ring-emerald-900/10 px-2.5 py-1.5 text-[11px] font-medium text-emerald-900 opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 z-50">
                                            {item.label}
                                        </span>
                                    )}
                                </Link>
                            );
                        })}
                    </nav>
                </div>

                {/* Tombol Keluar & Kembali ke Sisi Pengguna */}
                <div className="pt-4 border-t border-slate-900/[0.08]">
                    <button
                        type="button"
                        onClick={onLogout}
                        title={collapsed ? "Keluar & ke Beranda" : undefined}
                        className={`w-full group relative flex items-center rounded-xl text-[13px] font-medium text-emerald-700 transition-all duration-300 outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/50 hover:bg-emerald-500/[0.09] hover:text-emerald-900 active:scale-[0.98] active:bg-emerald-500/20 ${collapsed ? "justify-center p-2.5" : "gap-3 px-3 py-2.5"
                            }`}
                    >
                        <ExternalLink
                            strokeWidth={1.75}
                            className="w-[18px] h-[18px] shrink-0 text-emerald-600 transition-all duration-300 group-hover:text-emerald-500 group-hover:scale-110 group-hover:drop-shadow-[0_0_6px_rgba(16,185,129,0.4)]"
                        />
                        {!collapsed && <span>Keluar & ke Beranda</span>}

                        {/* Tooltip kaca saat collapsed */}
                        {collapsed && (
                            <span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-lg bg-white/90 backdrop-blur-xl ring-1 ring-emerald-900/10 px-2.5 py-1.5 text-[11px] font-medium text-emerald-900 opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 z-50">
                                Keluar & ke Beranda
                            </span>
                        )}
                    </button>
                </div>

            </div>

            {/* 2. FOOTER KARTU ADMIN */}
            <div className="pt-3">
                <div
                    className={`group bg-white/60 border border-white/90 rounded-2xl flex items-center shadow-[0_4px_16px_-8px_rgba(15,23,42,0.22)] backdrop-blur-md transition-all duration-300 hover:border-emerald-300/60 hover:shadow-[0_6px_20px_-8px_rgba(16,185,129,0.35)] ${collapsed ? "flex-col gap-2 p-2" : "justify-between p-2.5"
                        }`}
                >
                    {/* Klik kartu → halaman profil admin */}
                    <Link
                        href="/admin/profile"
                        title={collapsed ? `${userName} — Profil Admin` : "Buka profil admin"}
                        className={`flex items-center min-w-0 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/50 ${collapsed ? "flex-col" : "gap-2.5"}`}
                    >
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 border border-white/80 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm transition-all duration-300 group-hover:from-emerald-400 group-hover:to-emerald-600">
                            {userName.charAt(0).toUpperCase()}
                        </div>
                        {!collapsed && (
                            <div className="leading-tight truncate max-w-[110px]">
                                <p className="text-xs font-semibold text-slate-900 truncate">{userName}</p>
                                <p className="text-[10px] text-slate-500 truncate">{userRole}</p>
                            </div>
                        )}
                    </Link>

                    <button
                        type="button"
                        onClick={onLogout}
                        className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50/90 active:scale-90 rounded-lg transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-rose-300/50"
                        title="Keluar Admin"
                    >
                        <LogOut className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

        </aside>
    );
}
