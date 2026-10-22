"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import AdminSidebar from "./AdminSidebar";
import { Search, Bell, Cpu, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface AdminShellProps {
    children: React.ReactNode;
}

export default function AdminShell({ children }: AdminShellProps) {
    const pathname = usePathname();
    const { user, logout } = useAuth();
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    // Otomatis tentukan judul header admin berdasarkan rute aktif
    const getPageTitle = () => {
        if (pathname === "/admin") return "OVERVIEW";
        if (pathname.startsWith("/admin/logs")) return "LOG DETEKSI GLOBAL";
        if (pathname.startsWith("/admin/feedback")) return "KELOLA MASUKAN (RETRAINING)";
        if (pathname.startsWith("/admin/threshold")) return "KONTROL THRESHOLD MODEL";
        if (pathname.startsWith("/admin/users")) return "MANAJEMEN PENGGUNA";
        if (pathname.startsWith("/admin/export")) return "EKSPOR LAPORAN SISTEM";
        return "ADMIN PANEL";
    };

    return (
        // Mengunci layar 100vh agar topbar admin tidak tenggelam saat di-scroll
        <div className="flex h-screen w-full bg-[#f8fafc] text-slate-800 overflow-hidden font-sans select-none">

            {/* 1. Sidebar Khusus Admin (state collapse dikontrol dari sini) */}
            <AdminSidebar
                onLogout={logout}
                collapsed={sidebarCollapsed}
                onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
            />

            {/* 2. Kompartemen Kanan */}
            <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">

                {/* TOPBAR ADMIN — kaca putih kehijauan, tinggi 71px agar sejajar dengan header sidebar */}
                <header className="relative z-30 w-full h-[71px] px-8 flex items-center justify-between select-none shrink-0 border-b border-emerald-900/10 text-slate-600 shadow-[0_4px_24px_-14px_rgba(6,78,59,0.3)]">

                    {/* Latar: dasar putih kehijauan tipis + glow lembut + lapisan kaca blur (sama dengan UserTopbar) */}
                    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-gradient-to-r from-white via-emerald-50 to-white">
                        <div className="absolute -top-20 left-8 h-40 w-64 rounded-full bg-emerald-300/35 blur-3xl" />
                        <div className="absolute -top-16 right-1/3 h-36 w-64 rounded-full bg-teal-200/40 blur-3xl" />
                        <div className="absolute -bottom-20 right-0 h-40 w-64 rounded-full bg-emerald-300/30 blur-3xl" />
                        <div className="absolute inset-0 bg-white/50 backdrop-blur-2xl" />
                        {/* Kilau tipis di tepi atas */}
                        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-white via-white to-white" />
                    </div>

                    {/* Sisi Kiri: Tombol Sidebar + Pembatas + Judul Halaman */}
                    <div className="flex items-center gap-4">
                        <button
                            type="button"
                            onClick={() => setSidebarCollapsed((prev) => !prev)}
                            className="p-2 rounded-xl border border-emerald-900/10 bg-white/60 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10 hover:border-emerald-400/30 active:scale-90 outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/50 transition-all duration-200"
                            title={sidebarCollapsed ? "Besarkan sidebar" : "Kecilkan sidebar"}
                            aria-label={sidebarCollapsed ? "Besarkan sidebar" : "Kecilkan sidebar"}
                        >
                            {sidebarCollapsed ? (
                                <PanelLeftOpen className="w-[18px] h-[18px]" />
                            ) : (
                                <PanelLeftClose className="w-[18px] h-[18px]" />
                            )}
                        </button>

                        <span className="h-8 w-px bg-emerald-900/10" />
                        <h1 className="text-sm sm:text-base font-extrabold tracking-wider uppercase text-emerald-950 italic">
                            {getPageTitle()}
                        </h1>
                    </div>

                    {/* Sisi Kanan: Search Bar + Model Status + Profil Admin */}
                    <div className="flex items-center gap-3 sm:gap-4">

                        {/* Input Pencarian Global Admin */}
                        <div className="relative hidden md:block w-64">
                            <Search className="w-3.5 h-3.5 text-emerald-600/70 absolute left-3 top-1/2 -translate-y-1/2" />
                            <input
                                type="text"
                                placeholder="Cari log atau pengguna..."
                                className="w-full bg-white/60 border border-emerald-900/10 pl-8 pr-3 py-2 rounded-xl text-xs text-slate-800 placeholder-slate-400 backdrop-blur-md focus:outline-none focus:border-emerald-500/50 focus:bg-white/90 focus:ring-2 focus:ring-emerald-400/20 transition"
                            />
                        </div>

                        {/* Model Badge */}
                        <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-700 border border-emerald-500/25 px-3 py-1.5 rounded-xl text-xs font-bold tracking-wide shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] backdrop-blur-md">
                            <Cpu className="w-3.5 h-3.5 text-emerald-600" />
                            <span>IndoBERT Focal Loss</span>
                        </div>

                        {/* Notifikasi Lonceng */}
                        <button
                            type="button"
                            className="relative p-2 text-slate-500 hover:text-emerald-800 bg-white/60 hover:bg-white/90 border border-emerald-900/10 rounded-xl transition"
                            title="Notifikasi"
                        >
                            <Bell className="w-4 h-4" />
                            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-white" />
                        </button>

                        <div className="h-6 w-px bg-emerald-900/10" />

                        {/* Profil Admin Kanan */}
                        <div className="flex items-center gap-2.5 pl-1">
                            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 border border-white/80 text-white flex items-center justify-center font-bold text-xs shadow-sm">
                                {user?.name?.charAt(0) || "A"}
                            </div>
                            <div className="hidden lg:block text-left leading-tight">
                                <p className="text-xs font-bold text-emerald-950">{user?.name || "Administrator"}</p>
                                <p className="text-[10px] text-emerald-600 font-mono">admin@veridix.id</p>
                            </div>
                        </div>

                    </div>
                </header>

                {/* 3. AREA KONTEN (HANYA INI YANG BERGULIR SAAT HALAMAN DI-SCROLL) */}
                <main className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
                    {children}
                </main>

            </div>
        </div>
    );
}