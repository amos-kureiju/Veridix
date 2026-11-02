"use client";

import { useState, useRef, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
    Bell,
    ChevronDown,
    UserCircle,
    Settings,
    LogOut,
    Cpu,
    RefreshCw,
    CheckCheck,
    Newspaper,
    MessageSquareQuote,
    Info,
} from "lucide-react";

export type UserNotification = {
    id: string;
    type: "result" | "feedback" | "system";
    title: string;
    desc: string;
    time: string; // teks siap tampil, contoh: "2 menit lalu"
    read: boolean;
    href?: string; // tujuan saat notifikasi diklik
};

interface UserTopbarProps {
    title?: string;
    subtitle?: string;
    userName?: string;
    userRole?: string;
    guest?: boolean;
    aiStatus?: "ready" | "syncing";
    onToggleSidebar?: () => void;
    onLogout?: () => void;
    // Notifikasi dinamis: kirim dari parent (hasil fetch API). Kalau tidak dikirim, memakai data contoh lokal.
    notifications?: UserNotification[];
    onMarkAsRead?: (id: string) => void;
    onMarkAllAsRead?: () => void;
    // true = topbar menumpuk di atas konten (parent harus `relative`, konten diberi pt-[95px]) supaya blur terlihat
    overlay?: boolean;
}

// Data contoh bila parent belum mengirim notifikasi
const SAMPLE_NOTIFICATIONS: UserNotification[] = [
    { id: "n1", type: "result", title: "Hasil deteksi sudah siap", desc: "Analisis 4 lapis untuk berita yang Anda kirim telah selesai.", time: "2 menit lalu", read: false, href: "/history" },
    { id: "n2", type: "feedback", title: "Sanggahan Anda diproses", desc: "Feedback Anda sedang dievaluasi sebagai kandidat retraining.", time: "1 jam lalu", read: false, href: "/feedback" },
    { id: "n3", type: "system", title: "Model AI diperbarui", desc: "IndoBERT terbaru aktif untuk meningkatkan akurasi deteksi.", time: "Kemarin", read: true },
];

export default function UserTopbar({
    title,
    subtitle,
    userName = "Pengguna",
    userRole = "USER",
    guest = false,
    aiStatus = "ready",
    onToggleSidebar,
    onLogout,
    notifications: notificationsProp,
    onMarkAsRead,
    onMarkAllAsRead,
    overlay = false,
}: UserTopbarProps) {
    const pathname = usePathname();
    const router = useRouter();
    const [accountOpen, setAccountOpen] = useState(false);
    const [notifOpen, setNotifOpen] = useState(false);
    const accountRef = useRef<HTMLDivElement>(null);
    const notifRef = useRef<HTMLDivElement>(null);

    // Mode terkontrol (dari parent) atau mode lokal (data contoh)
    const [localNotifications, setLocalNotifications] = useState<UserNotification[]>([]);
    const notifications = guest ? [] : notificationsProp ?? localNotifications;
    const unreadCount = notifications.filter((n) => !n.read).length;

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            const target = event.target as Node;
            if (accountRef.current && !accountRef.current.contains(target)) setAccountOpen(false);
            if (notifRef.current && !notifRef.current.contains(target)) setNotifOpen(false);
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const markAsRead = (id: string) => {
        if (onMarkAsRead) onMarkAsRead(id);
        if (!notificationsProp) {
            setLocalNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
        }
    };

    const markAllAsRead = () => {
        if (onMarkAllAsRead) onMarkAllAsRead();
        if (!notificationsProp) {
            setLocalNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
        }
    };

    const openNotification = (n: UserNotification) => {
        if (!n.read) markAsRead(n.id);
        setNotifOpen(false);
        if (n.href) router.push(n.href);
    };

    const notifIcon = (type: UserNotification["type"]) => {
        if (type === "result") return Newspaper;
        if (type === "feedback") return MessageSquareQuote;
        return Info;
    };

    const getRouteInfo = () => {
        if (title) return { heading: title, sub: subtitle || "" };
        if (pathname === "/") return { heading: "DASHBOARD", sub: "Deteksi disinformasi teks & tangkapan layar politik" };
        if (pathname.startsWith("/history")) return { heading: "RIWAYAT DETEKSI", sub: "Histori verifikasi IndoBERT & LIME" };
        if (pathname.startsWith("/feedback")) return { heading: "FEEDBACK SAYA", sub: "Status evaluasi sanggahan & kandidat retraining" };
        if (pathname.startsWith("/profile")) return { heading: "PROFIL SAYA", sub: "Kelola profil akun dan keamanan" };
        if (pathname.startsWith("/settings")) return { heading: "PENGATURAN", sub: "Konfigurasi preferensi sistem" };
        if (pathname.startsWith("/help")) return { heading: "PUSAT BANTUAN", sub: "Panduan transparansi XAI 4 Lapis" };
        return { heading: "VERIDIX SYSTEM", sub: "AI Fact Intelligence Platform" };
    };

    const routeInfo = getRouteInfo();

    return (
        // Tinggi 71px disamakan dengan header sidebar supaya garis pemisah keduanya sejajar
        <header
            className={`${overlay ? "absolute top-0 inset-x-0" : "relative"} z-30 w-full h-[71px] px-6 flex items-center justify-between select-none shrink-0 text-slate-600 font-sans border-b border-white/50 bg-gradient-to-r from-emerald-200/45 via-white/20 to-emerald-200/45 backdrop-blur-xl backdrop-saturate-150 shadow-[0_8px_32px_-12px_rgba(6,78,59,0.35),inset_0_1px_0_rgba(255,255,255,0.7)]`}
        >
            {/* Kilau kaca: terang di atas, memudar ke bawah */}
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/40 via-white/5 to-transparent" />

            {/* Sisi Kiri: Pembatas + Judul Halaman */}
            <div className="relative flex items-center gap-4">
                <span className="h-8 w-px bg-emerald-900/10" />
                <div className="leading-tight">
                    <h1 className="text-sm sm:text-base font-extrabold tracking-wider uppercase text-emerald-950 italic">
                        {routeInfo.heading}
                    </h1>
                    {routeInfo.sub && (
                        <p className="text-[10px] text-slate-500 font-medium hidden md:block">
                            {routeInfo.sub}
                        </p>
                    )}
                </div>
            </div>

            {/* Sisi Kanan: Status AI + Notifikasi + Profil */}
            <div className="relative flex items-center gap-3 sm:gap-4">

                {/* Status AI Badge */}
                <div className="hidden sm:flex items-center gap-2 bg-emerald-500/10 text-emerald-700 border border-emerald-500/25 px-3 py-1.5 rounded-xl text-xs font-bold tracking-wide shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] backdrop-blur-md">
                    {aiStatus === "syncing" ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                    ) : (
                        <Cpu className="w-3.5 h-3.5 text-emerald-600" />
                    )}
                    <span>SYNC AI</span>
                    <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)] animate-pulse"></span>
                </div>

                {/* Notifikasi User */}
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
                        <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-white/90 backdrop-blur-2xl border border-white rounded-2xl shadow-xl shadow-emerald-900/15 ring-1 ring-emerald-900/5 text-xs text-slate-700 z-50 overflow-hidden animate-in fade-in zoom-in-95">
                            <div className="flex items-center justify-between px-4 py-3 border-b border-emerald-900/10">
                                <p className="font-bold text-emerald-950">Notifikasi</p>
                                {!guest && (
                                    <button
                                        type="button"
                                        onClick={markAllAsRead}
                                        disabled={unreadCount === 0}
                                        className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 hover:text-emerald-800 disabled:opacity-40 disabled:hover:text-emerald-600 transition"
                                    >
                                        <CheckCheck className="w-3.5 h-3.5" />
                                        Tandai dibaca
                                    </button>
                                )}
                            </div>

                            <div className="max-h-80 overflow-y-auto p-1.5">
                                {guest ? (
                                    <div className="text-center px-4 py-8">
                                        <p className="text-slate-500">Masuk untuk melihat notifikasi hasil deteksi dan feedback Anda.</p>
                                        <button
                                            type="button"
                                            onClick={() => { setNotifOpen(false); onLogout?.(); }}
                                            className="mt-3 px-3.5 py-1.5 rounded-lg text-[11px] font-semibold text-white bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 transition"
                                        >
                                            Masuk Akun
                                        </button>
                                    </div>
                                ) : notifications.length === 0 ? (
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

                <div className="h-6 w-px bg-emerald-900/10 hidden sm:block" />

                {/* Profil User */}
                <div className="relative" ref={accountRef}>
                    <button
                        type="button"
                        onClick={() => { setAccountOpen(!accountOpen); setNotifOpen(false); }}
                        className="flex items-center gap-2.5 p-1 pr-2.5 rounded-xl hover:bg-white/60 border border-transparent hover:border-white transition group"
                    >
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 border border-white/80 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">
                            {guest ? "G" : userName.charAt(0)}
                        </div>

                        <div className="hidden md:flex flex-col text-left leading-tight">
                            <span className="text-xs font-bold text-emerald-950 uppercase tracking-tight">
                                {guest ? "MODE TAMU" : userName}
                            </span>
                            <span className="text-[10px] font-bold text-emerald-600 tracking-wider uppercase">
                                {guest ? "TAMU" : userRole}
                            </span>
                        </div>

                        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-800 transition-transform ${accountOpen ? "rotate-180" : ""}`} />
                    </button>

                    {accountOpen && (
                        <div className="absolute right-0 mt-2 w-52 bg-white/85 backdrop-blur-2xl border border-white rounded-2xl shadow-xl shadow-emerald-900/15 ring-1 ring-emerald-900/5 p-1.5 text-xs text-slate-700 z-50 animate-in fade-in zoom-in-95">
                            <div className="px-3 py-2 border-b border-emerald-900/10 mb-1">
                                <p className="font-bold text-emerald-950 truncate">{guest ? "Mode Tamu" : userName}</p>
                                <p className="text-[10px] text-slate-500">{guest ? "Masuk untuk mendeteksi" : userRole}</p>
                            </div>

                            <button
                                type="button"
                                onClick={() => { setAccountOpen(false); router.push("/profile"); }}
                                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-emerald-50 hover:text-emerald-900 transition text-left"
                            >
                                <UserCircle className="w-4 h-4 text-slate-400" />
                                <span>Profil Saya</span>
                            </button>

                            <button
                                type="button"
                                onClick={() => { setAccountOpen(false); router.push("/settings"); }}
                                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-emerald-50 hover:text-emerald-900 transition text-left"
                            >
                                <Settings className="w-4 h-4 text-slate-400" />
                                <span>Pengaturan</span>
                            </button>

                            <div className="my-1 border-t border-emerald-900/10" />

                            <button
                                type="button"
                                onClick={() => { setAccountOpen(false); onLogout?.(); }}
                                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-rose-50 text-rose-600 transition text-left"
                            >
                                <LogOut className="w-4 h-4" />
                                <span>{guest ? "Masuk Akun" : "Keluar Akun"}</span>
                            </button>
                        </div>
                    )}
                </div>

            </div>
        </header>
    );
}