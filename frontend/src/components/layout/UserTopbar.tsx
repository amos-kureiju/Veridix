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
        // Tinggi 71px disamakan dengan header sidebar supaya garis pemisah keduanya sejajar
        <header className="relative z-30 w-full h-[71px] px-6 flex items-center justify-between select-none shrink-0 border-b border-emerald-900/10 text-slate-600 font-sans shadow-[0_4px_24px_-14px_rgba(6,78,59,0.3)]">

            {/* Latar: dasar putih kehijauan tipis + glow lembut + lapisan kaca putih blur (sama dengan sidebar) */}
            <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-gradient-to-r from-white via-emerald-50 to-white">
                <div className="absolute -top-20 left-8 h-40 w-64 rounded-full bg-emerald-300/35 blur-3xl" />
                <div className="absolute -top-16 right-1/3 h-36 w-64 rounded-full bg-teal-200/40 blur-3xl" />
                <div className="absolute -bottom-20 right-0 h-40 w-64 rounded-full bg-emerald-300/30 blur-3xl" />
                <div className="absolute inset-0 bg-white/50 backdrop-blur-2xl" />
                {/* Kilau tipis di tepi atas */}
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-white via-white to-white" />
            </div>

            {/* Sisi Kiri: Menu + Pembatas + Judul Halaman */}
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-4">
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
            </div>

            {/* Sisi Kanan: Status AI + Notifikasi + Profil */}
            <div className="flex items-center gap-3 sm:gap-4">

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

                {/* Lonceng Notifikasi */}
                <button
                    type="button"
                    className="relative p-2 text-slate-500 hover:text-emerald-800 bg-white/60 hover:bg-white/90 border border-emerald-900/10 rounded-xl transition"
                    title="Notifikasi"
                >
                    <Bell className="w-4 h-4" />
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-white" />
                </button>

                <div className="h-6 w-px bg-emerald-900/10 hidden sm:block" />

                {/* Profil User */}
                <div className="relative" ref={accountRef}>
                    <button
                        type="button"
                        onClick={() => setAccountOpen(!accountOpen)}
                        className="flex items-center gap-2.5 p-1 pr-2.5 rounded-xl hover:bg-white/70 border border-transparent hover:border-white transition group"
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