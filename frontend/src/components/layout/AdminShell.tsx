"use client";

import { usePathname } from "next/navigation";
import AdminSidebar from "./AdminSidebar";
import { Search, Bell, Cpu } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface AdminShellProps {
    children: React.ReactNode;
}

export default function AdminShell({ children }: AdminShellProps) {
    const pathname = usePathname();
    const { user, logout } = useAuth();

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

            {/* 1. Sidebar Khusus Admin (Menetap permanen di kiri) */}
            <AdminSidebar onLogout={logout} />

            {/* 2. Kompartemen Kanan */}
            <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">

                {/* TOPBAR ADMIN CAZURA (STICKY / FIXED DI ATAS) */}
                <header className="w-full bg-white border-b border-slate-200/80 px-8 py-3.5 flex items-center justify-between select-none shrink-0 shadow-2xs z-30">

                    {/* Sisi Kiri: Breadcrumb / Judul Halaman */}
                    <div className="flex items-center gap-3">
                        <span className="text-slate-300 font-light text-lg">|</span>
                        <h1 className="text-sm font-extrabold tracking-wider uppercase text-slate-800 italic">
                            {getPageTitle()}
                        </h1>
                    </div>

                    {/* Sisi Kanan: Search Bar + Model Status + Profil Admin */}
                    <div className="flex items-center gap-4">

                        {/* Input Pencarian Global Admin */}
                        <div className="relative hidden md:block w-64">
                            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                            <input
                                type="text"
                                placeholder="Cari log atau pengguna..."
                                className="w-full bg-[#f8fafc] border border-slate-200 pl-8 pr-3 py-1.5 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-slate-400 transition"
                            />
                        </div>

                        {/* Model Badge */}
                        <div className="flex items-center gap-1.5 bg-slate-100 text-slate-700 px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-200">
                            <Cpu className="w-3.5 h-3.5 text-slate-500" />
                            <span>IndoBERT Focal Loss</span>
                        </div>

                        {/* Notifikasi Lonceng */}
                        <button
                            type="button"
                            className="p-2 text-slate-400 hover:text-slate-800 rounded-xl transition relative"
                            title="Notifikasi"
                        >
                            <Bell className="w-4 h-4" />
                            <span className="w-2 h-2 bg-emerald-500 rounded-full absolute top-2 right-2" />
                        </button>

                        <div className="h-6 w-px bg-slate-200" />

                        {/* Profil Admin Kanan */}
                        <div className="flex items-center gap-2 pl-1">
                            <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                                {user?.name?.charAt(0) || "A"}
                            </div>
                            <div className="hidden lg:block text-left leading-tight">
                                <p className="text-xs font-bold text-slate-800">{user?.name || "Administrator"}</p>
                                <p className="text-[10px] text-slate-400 font-mono">admin@veridix.id</p>
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