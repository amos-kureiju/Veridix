"use client";

import { useState, useRef, useEffect } from "react";
import { Info, Bell, Download, ChevronDown, UserCircle, Settings, LogOut } from "lucide-react";

interface UserTopbarProps {
    title?: string;
    subtitle?: string;
    userName?: string;
    guest?: boolean;
    showExport?: boolean;
    onExport?: () => void;
    onProfile?: () => void;
    onSettings?: () => void;
    onLogout?: () => void;
}

export default function UserTopbar({
    title = "Deteksi Berita",
    subtitle = "Masukkan teks atau upload gambar untuk dianalisis",
    userName = "Amos Manurung",
    guest = false,
    showExport = false,
    onExport,
    onProfile,
    onSettings,
    onLogout,
}: UserTopbarProps) {
    const [accountOpen, setAccountOpen] = useState(false);
    const accountRef = useRef<HTMLDivElement>(null);

    // Tutup dropdown akun saat klik di luar area
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (accountRef.current && !accountRef.current.contains(event.target as Node)) {
                setAccountOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleExport = () => {
        if (onExport) {
            onExport();
        } else {
            alert("Fitur Export Laporan (PDF/CSV) siap dihubungkan!");
        }
    };

    return (
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 mb-5 border-b border-slate-200">
            {/* Sisi Kiri: Judul Halaman & Subtitle */}
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-slate-900 leading-tight">
                    {title}
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">
                    {subtitle}
                </p>
            </div>

            {/* Sisi Kanan: Info + Notifikasi + Export (opsional) + Akun */}
            <div className="flex items-center gap-3">

                {/* Ikon Info */}
                <button
                    type="button"
                    title="Informasi Sistem"
                    className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-200/50 rounded-xl transition"
                >
                    <Info className="w-4 h-4" />
                </button>

                {/* Ikon Lonceng Notifikasi dengan Dot Aktif */}
                <button
                    type="button"
                    title="Notifikasi"
                    className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-200/50 rounded-xl transition relative"
                >
                    <Bell className="w-4 h-4" />
                    <span className="w-2 h-2 bg-emerald-500 rounded-full absolute top-2 right-2 ring-2 ring-white" />
                </button>

                {/* Tombol Export — hanya tampil kalau halaman memang butuh (mis. Riwayat) */}
                {showExport && (
                    <button
                        type="button"
                        onClick={handleExport}
                        className="flex items-center gap-2 bg-[#0b2520] hover:bg-[#133730] text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-xs transition"
                    >
                        <span>Export</span>
                        <Download className="w-3.5 h-3.5" />
                    </button>
                )}

                {/* Separator Garis Tipis */}
                <div className="h-5 w-px bg-slate-200 mx-1" />

                {/* Tombol Akun */}
                <div className="relative" ref={accountRef}>
                    <button
                        type="button"
                        onClick={() => setAccountOpen((prev) => !prev)}
                        className="flex items-center gap-2 pl-1.5 pr-2.5 py-1.5 rounded-xl hover:bg-slate-200/50 transition"
                        title="Akun saya"
                    >
                        <div className="w-7 h-7 rounded-full bg-emerald-600 border-2 border-white flex items-center justify-center text-[10px] font-bold text-white shadow-xs shrink-0">
                            {guest ? "G" : userName.charAt(0)}
                        </div>
                        <span className="text-xs font-semibold text-slate-700 hidden sm:inline max-w-[90px] truncate">
                            {guest ? "Mode Tamu" : userName}
                        </span>
                        <ChevronDown
                            className={`w-3.5 h-3.5 text-slate-400 transition-transform ${accountOpen ? "rotate-180" : ""
                                }`}
                        />
                    </button>

                    {/* Dropdown Akun */}
                    {accountOpen && (
                        <div className="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-xl shadow-lg py-1.5 z-50">
                            <div className="px-3 py-2 border-b border-slate-100">
                                <p className="text-xs font-semibold text-slate-800 truncate">
                                    {guest ? "Mode Tamu" : userName}
                                </p>
                                <p className="text-[10px] text-slate-400 truncate">
                                    {guest ? "3 Kuota Tersisa" : "User Terdaftar"}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => {
                                    setAccountOpen(false);
                                    onProfile?.();
                                }}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
                            >
                                <UserCircle className="w-4 h-4" />
                                Profil Saya
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setAccountOpen(false);
                                    onSettings?.();
                                }}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
                            >
                                <Settings className="w-4 h-4" />
                                Pengaturan
                            </button>
                            <div className="my-1 border-t border-slate-100" />
                            <button
                                type="button"
                                onClick={() => {
                                    setAccountOpen(false);
                                    onLogout?.();
                                }}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-500 hover:bg-red-50 transition"
                            >
                                <LogOut className="w-4 h-4" />
                                {guest ? "Masuk ke Akun" : "Keluar"}
                            </button>
                        </div>
                    )}
                </div>

            </div>
        </header>
    );
}