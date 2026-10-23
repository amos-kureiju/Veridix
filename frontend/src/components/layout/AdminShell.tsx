"use client";

import { useState, useRef, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import AdminSidebar from "./AdminSidebar";
import {
    Search,
    Bell,
    Cpu,
    ChevronDown,
    UserCircle,
    KeyRound,
    LogOut,
    CheckCheck,
    MessageSquare,
    Users,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface AdminShellProps {
    children: React.ReactNode;
}

type AdminNotification = {
    id: string;
    type: "feedback" | "user" | "system";
    title: string;
    desc: string;
    time: string;
    read: boolean;
    href?: string;
};

// Format role dari backend (mis. "super_admin") menjadi label rapi ("Super Admin")
const formatRole = (role?: string) =>
    (role || "admin").replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export default function AdminShell({ children }: AdminShellProps) {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [notifOpen, setNotifOpen] = useState(false);
    const [accountOpen, setAccountOpen] = useState(false);
    const notifRef = useRef<HTMLDivElement>(null);
    const accountRef = useRef<HTMLDivElement>(null);

    // Data admin dinamis dari useAuth (field yang belum ada di tipe user tetap aman)
    const u = user as { name?: string; email?: string; role?: string } | null;
    const adminName = u?.name || "Administrator";
    const adminEmail = u?.email || "";
    const adminRole = formatRole(u?.role);
    const adminInitial = adminName.charAt(0).toUpperCase();

    // TODO: ganti data contoh ini dengan hasil fetch dari API notifikasi admin
    const [notifications, setNotifications] = useState<AdminNotification[]>([
        { id: "n1", type: "feedback", title: "Masukan baru menunggu review", desc: "Ada kandidat dataset baru dari sanggahan pengguna.", time: "2 menit lalu", read: false, href: "/admin/feedback" },
        { id: "n2", type: "user", title: "Pengguna baru mendaftar", desc: "Akun baru terdaftar dalam 24 jam terakhir.", time: "1 jam lalu", read: false, href: "/admin/users" },
        { id: "n3", type: "system", title: "IndoBERT Engine siap", desc: "Sinkronisasi model selesai, status siap inferensi.", time: "Kemarin", read: true, href: "/admin" },
    ]);
    const unreadCount = notifications.filter((n) => !n.read).length;

    // Tutup dropdown saat klik di luar
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            const target = event.target as Node;
            if (notifRef.current && !notifRef.current.contains(target)) setNotifOpen(false);
            if (accountRef.current && !accountRef.current.contains(target)) setAccountOpen(false);
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const markAllRead = () => setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));

    const openNotification = (n: AdminNotification) => {
        setNotifications((prev) => prev.map((item) => (item.id === n.id ? { ...item, read: true } : item)));
        setNotifOpen(false);
        if (n.href) router.push(n.href);
    };

    const notifIcon = (type: AdminNotification["type"]) => {
        if (type === "feedback") return MessageSquare;
        if (type === "user") return Users;
        return Cpu;
    };

    // Otomatis tentukan judul header admin berdasarkan rute aktif
    const getPageTitle = () => {
        if (pathname === "/admin") return "OVERVIEW";
        if (pathname.startsWith("/admin/logs")) return "LOG DETEKSI GLOBAL";
        if (pathname.startsWith("/admin/feedback")) return "KELOLA MASUKAN (RETRAINING)";
        if (pathname.startsWith("/admin/threshold")) return "KONTROL THRESHOLD MODEL";
        if (pathname.startsWith("/admin/users")) return "MANAJEMEN PENGGUNA";
        if (pathname.startsWith("/admin/export")) return "EKSPOR LAPORAN SISTEM";
        if (pathname.startsWith("/admin/profile")) return "PROFIL ADMIN";
        return "ADMIN PANEL";
    };

    return (
        // Mengunci layar 100vh agar topbar admin tidak tenggelam saat di-scroll
        <div className="flex h-screen w-full bg-[#f8fafc] text-slate-800 overflow-hidden font-sans select-none">

            {/* 1. Sidebar Khusus Admin (tombol kecilkan ada di sidebar, state dikontrol dari sini) */}
            <AdminSidebar
                onLogout={logout}
                collapsed={sidebarCollapsed}
                onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
                userName={adminName}
                userRole={adminRole}
            />

            {/* 2. Kompartemen Kanan (relative: topbar menumpuk di atas konten supaya blur terlihat) */}
            <div className="relative flex-1 flex flex-col h-screen min-w-0 overflow-hidden">

                {/* TOPBAR ADMIN — kaca bening + blur kuat */}
                <header className="absolute top-0 inset-x-0 z-30 h-[71px] px-8 flex items-center justify-between select-none text-slate-600 border-b border-white/50 bg-gradient-to-r from-emerald-200/45 via-white/20 to-emerald-200/45 backdrop-blur-xl backdrop-saturate-150 shadow-[0_8px_32px_-12px_rgba(6,78,59,0.35),inset_0_1px_0_rgba(255,255,255,0.7)]">

                    {/* Kilau kaca: terang di atas, memudar ke bawah */}
                    <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/40 via-white/5 to-transparent" />

                    {/* Sisi Kiri: Pembatas + Judul Halaman */}
                    <div className="relative flex items-center gap-4">
                        <span className="h-8 w-px bg-emerald-900/10" />
                        <h1 className="text-sm sm:text-base font-extrabold tracking-wider uppercase text-emerald-950 italic">
                            {getPageTitle()}
                        </h1>
                    </div>

                    {/* Sisi Kanan: Search Bar + Model Status + Notifikasi + Profil Admin */}
                    <div className="relative flex items-center gap-3 sm:gap-4">

                        {/* Input Pencarian Global Admin */}
                        <div className="relative hidden md:block w-64">
                            <Search className="w-3.5 h-3.5 text-emerald-600/70 absolute left-3 top-1/2 -translate-y-1/2" />
                            <input
                                type="text"
                                placeholder="Cari log atau pengguna..."
                                className="w-full bg-white/40 border border-white/60 pl-8 pr-3 py-2 rounded-xl text-xs text-slate-800 placeholder-slate-500 backdrop-blur-md focus:outline-none focus:border-emerald-500/50 focus:bg-white/70 focus:ring-2 focus:ring-emerald-400/20 transition"
                            />
                        </div>

                        {/* Model Badge */}
                        <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-700 border border-emerald-500/25 px-3 py-1.5 rounded-xl text-xs font-bold tracking-wide shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] backdrop-blur-md">
                            <Cpu className="w-3.5 h-3.5 text-emerald-600" />
                            <span>IndoBERT Focal Loss</span>
                        </div>

                        {/* Notifikasi Admin */}
                        <div className="relative" ref={notifRef}>
                            <button
                                type="button"
                                onClick={() => { setNotifOpen((prev) => !prev); setAccountOpen(false); }}
                                className="relative p-2 text-slate-500 hover:text-emerald-800 bg-white/40 hover:bg-white/70 border border-white/60 rounded-xl backdrop-blur-md transition"
                                title="Notifikasi"
                                aria-label="Notifikasi"
                            >
                                <Bell className="w-4 h-4" />
                                {unreadCount > 0 && (
                                    <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 flex items-center justify-center text-[9px] font-bold bg-rose-500 text-white rounded-full ring-2 ring-white">
                                        {unreadCount > 9 ? "9+" : unreadCount}
                                    </span>
                                )}
                            </button>

                            {notifOpen && (
                                <div className="absolute right-0 mt-2 w-80 bg-white/90 backdrop-blur-2xl border border-white rounded-2xl shadow-xl shadow-emerald-900/15 ring-1 ring-emerald-900/5 text-xs text-slate-700 z-50 overflow-hidden">
                                    <div className="flex items-center justify-between px-4 py-3 border-b border-emerald-900/10">
                                        <p className="font-bold text-emerald-950">Notifikasi</p>
                                        <button
                                            type="button"
                                            onClick={markAllRead}
                                            disabled={unreadCount === 0}
                                            className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 hover:text-emerald-800 disabled:opacity-40 disabled:hover:text-emerald-600 transition"
                                        >
                                            <CheckCheck className="w-3.5 h-3.5" />
                                            Tandai dibaca
                                        </button>
                                    </div>

                                    <div className="max-h-80 overflow-y-auto p-1.5">
                                        {notifications.length === 0 ? (
                                            <p className="text-center text-slate-400 py-8">Belum ada notifikasi</p>
                                        ) : (
                                            notifications.map((n) => {
                                                const NIcon = notifIcon(n.type);
                                                return (
                                                    <button
                                                        key={n.id}
                                                        type="button"
                                                        onClick={() => openNotification(n)}
                                                        className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-xl text-left transition hover:bg-emerald-50 ${n.read ? "" : "bg-emerald-50/60"}`}
                                                    >
                                                        <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center shrink-0">
                                                            <NIcon className="w-4 h-4" strokeWidth={1.75} />
                                                        </div>
                                                        <div className="min-w-0 flex-1 leading-snug">
                                                            <p className="font-semibold text-emerald-950 truncate">{n.title}</p>
                                                            <p className="text-[11px] text-slate-500 line-clamp-2">{n.desc}</p>
                                                            <p className="text-[10px] text-emerald-600/80 mt-0.5">{n.time}</p>
                                                        </div>
                                                        {!n.read && <span className="w-2 h-2 mt-1.5 rounded-full bg-emerald-500 shrink-0" />}
                                                    </button>
                                                );
                                            })
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="h-6 w-px bg-emerald-900/10" />

                        {/* Profil Admin — klik untuk detail akun */}
                        <div className="relative" ref={accountRef}>
                            <button
                                type="button"
                                onClick={() => { setAccountOpen((prev) => !prev); setNotifOpen(false); }}
                                className="flex items-center gap-2.5 p-1 pr-2.5 rounded-xl hover:bg-white/60 border border-transparent hover:border-white transition group"
                            >
                                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 border border-white/80 text-white flex items-center justify-center font-bold text-xs shadow-sm">
                                    {adminInitial}
                                </div>
                                <div className="hidden lg:block text-left leading-tight">
                                    <p className="text-xs font-bold text-emerald-950">{adminName}</p>
                                    {adminEmail && <p className="text-[10px] text-emerald-600 font-mono">{adminEmail}</p>}
                                </div>
                                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-800 transition-transform ${accountOpen ? "rotate-180" : ""}`} />
                            </button>

                            {accountOpen && (
                                <div className="absolute right-0 mt-2 w-64 bg-white/90 backdrop-blur-2xl border border-white rounded-2xl shadow-xl shadow-emerald-900/15 ring-1 ring-emerald-900/5 p-1.5 text-xs text-slate-700 z-50">
                                    {/* Detail akun admin */}
                                    <div className="flex items-center gap-3 px-3 py-3 border-b border-emerald-900/10 mb-1">
                                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 border border-white/80 text-white flex items-center justify-center font-bold text-sm shadow-sm shrink-0">
                                            {adminInitial}
                                        </div>
                                        <div className="min-w-0 leading-tight">
                                            <p className="font-bold text-emerald-950 truncate">{adminName}</p>
                                            {adminEmail && <p className="text-[10px] text-slate-500 truncate">{adminEmail}</p>}
                                            <span className="inline-block mt-1 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-emerald-500/10 text-emerald-700 ring-1 ring-emerald-500/20">
                                                {adminRole}
                                            </span>
                                        </div>
                                    </div>

                                    <button
                                        type="button"
                                        onClick={() => { setAccountOpen(false); router.push("/admin/profile"); }}
                                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-emerald-50 hover:text-emerald-900 transition text-left"
                                    >
                                        <UserCircle className="w-4 h-4 text-emerald-600" />
                                        <span>Profil Admin</span>
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => { setAccountOpen(false); router.push("/admin/profile#password"); }}
                                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-emerald-50 hover:text-emerald-900 transition text-left"
                                    >
                                        <KeyRound className="w-4 h-4 text-emerald-600" />
                                        <span>Ganti Password</span>
                                    </button>

                                    <div className="my-1 border-t border-emerald-900/10" />

                                    <button
                                        type="button"
                                        onClick={() => { setAccountOpen(false); logout(); }}
                                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-rose-50 text-rose-600 transition text-left"
                                    >
                                        <LogOut className="w-4 h-4" />
                                        <span>Keluar Admin</span>
                                    </button>
                                </div>
                            )}
                        </div>

                    </div>
                </header>

                {/* 3. AREA KONTEN — pt diberi ruang setinggi topbar; konten bergulir di bawah kaca */}
                <main className="flex-1 overflow-y-auto px-8 pt-[95px] pb-6 space-y-6">
                    {children}
                </main>

            </div>
        </div>
    );
}