"use client";

import { useState, useRef, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
    Menu,
    Bell,
    ChevronDown,
    UserCircle,
    Settings,
    LogOut,
    Cpu,
    RefreshCw
} from "lucide-react";

interface UserTopbarProps {
    title?: string;
    subtitle?: string;
    userName?: string;
    userRole?: string;
    guest?: boolean;
    aiStatus?: "ready" | "syncing";
    onToggleSidebar?: () => void;
    onLogout?: () => void;
}

export default function UserTopbar({
    title,
    subtitle,
    userName = "Amos Manurung",
    userRole = "USER",
    guest = false,
    aiStatus = "ready",
    onToggleSidebar,
    onLogout,
}: UserTopbarProps) {
    const pathname = usePathname();
    const router = useRouter();
    const [accountOpen, setAccountOpen] = useState(false);
    const accountRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (accountRef.current && !accountRef.current.contains(event.target as Node)) {
                setAccountOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

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
        <header className="w-full bg-white border-b border-slate-200/80 px-6 py-3.5 flex items-center justify-between select-none shrink-0 shadow-2xs">

            {/* Sisi Kiri: Menu + Pembatas + Judul Halaman */}
            <div className="flex items-center gap-3">
                <button
                    type="button"
                    onClick={onToggleSidebar}
                    className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition"
                    title="Toggle Menu"
                >
                    <Menu className="w-5 h-5" />
                </button>

                <div className="flex items-center gap-2.5">
                    <span className="text-slate-300 font-light text-lg">|</span>
                    <div className="leading-tight">
                        <h1 className="text-sm sm:text-base font-extrabold tracking-wider uppercase text-slate-800 italic">
                            {routeInfo.heading}
                        </h1>
                        {routeInfo.sub && (
                            <p className="text-[10px] text-slate-400 font-medium hidden md:block">
                                {routeInfo.sub}
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Sisi Kanan: Status AI + Notifikasi + Profil */}
            <div className="flex items-center gap-3 sm:gap-4">

                {/* Status AI Badge */}
                <div className="hidden sm:flex items-center gap-2 bg-emerald-50 text-emerald-700 border border-emerald-300/60 px-3 py-1.5 rounded-xl text-xs font-bold tracking-wide shadow-2xs">
                    {aiStatus === "syncing" ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                    ) : (
                        <Cpu className="w-3.5 h-3.5 text-emerald-600" />
                    )}
                    <span>SYNC AI</span>
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                </div>

                {/* Lonceng Notifikasi */}
                <button
                    type="button"
                    className="relative p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition"
                    title="Notifikasi"
                >
                    <Bell className="w-4 h-4" />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-white" />
                </button>

                <div className="h-6 w-px bg-slate-200 hidden sm:block" />

                {/* Profil User */}
                <div className="relative" ref={accountRef}>
                    <button
                        type="button"
                        onClick={() => setAccountOpen(!accountOpen)}
                        className="flex items-center gap-2.5 p-1 pr-2 rounded-xl hover:bg-slate-100 transition group"
                    >
                        <div className="w-8 h-8 rounded-full bg-emerald-800 border border-slate-200 text-emerald-100 flex items-center justify-center font-bold text-xs shrink-0 shadow-xs">
                            {guest ? "G" : userName.charAt(0)}
                        </div>

                        <div className="hidden md:flex flex-col text-left leading-tight">
                            <span className="text-xs font-bold text-slate-800 uppercase tracking-tight">
                                {guest ? "MODE TAMU" : userName}
                            </span>
                            <span className="text-[10px] font-bold text-emerald-600 tracking-wider uppercase">
                                {guest ? "TAMU" : userRole}
                            </span>
                        </div>

                        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 group-hover:text-slate-700 transition-transform ${accountOpen ? "rotate-180" : ""}`} />
                    </button>

                    {accountOpen && (
                        <div className="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-2xl shadow-xl p-1.5 text-xs text-slate-700 z-50 animate-in fade-in zoom-in-95">
                            <div className="px-3 py-2 border-b border-slate-100 mb-1">
                                <p className="font-bold text-slate-800 truncate">{guest ? "Mode Tamu" : userName}</p>
                                <p className="text-[10px] text-slate-400">{guest ? "3 Kuota Tersisa" : userRole}</p>
                            </div>

                            <button
                                type="button"
                                onClick={() => { setAccountOpen(false); router.push("/profile"); }}
                                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-slate-50 transition text-left"
                            >
                                <UserCircle className="w-4 h-4 text-slate-400" />
                                <span>Profil Saya</span>
                            </button>

                            <button
                                type="button"
                                onClick={() => { setAccountOpen(false); router.push("/settings"); }}
                                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-slate-50 transition text-left"
                            >
                                <Settings className="w-4 h-4 text-slate-400" />
                                <span>Pengaturan</span>
                            </button>

                            <div className="my-1 border-t border-slate-100" />

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