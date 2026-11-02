"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect, useMemo } from "react";
import {
    Search,
    BrainCircuit,
    History,
    MessageSquareQuote,
    UserCircle,
    Settings,
    HelpCircle,
    LogOut,
    PanelLeftClose,
    PanelLeftOpen,
} from "lucide-react";

interface UserSidebarProps {
    onLogout?: () => void;
    guest?: boolean;
    userName?: string;
    feedbackCount?: number;
}

type MenuItem = {
    label: string;
    href: string;
    icon: typeof BrainCircuit;
    badge?: string;
};

export default function UserSidebar({
    onLogout,
    guest = false,
    userName = "Pengguna",
    feedbackCount = 0,
}: UserSidebarProps) {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);
    const [query, setQuery] = useState("");
    const searchInputRef = useRef<HTMLInputElement>(null);

    // Shortcut ⌘F / Ctrl+F -> buka sidebar (kalau lagi mengecil) & fokus ke search
    useEffect(() => {
        function handleKeyDown(e: KeyboardEvent) {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "f") {
                e.preventDefault();
                setCollapsed(false);
                setTimeout(() => searchInputRef.current?.focus(), 50);
            }
        }
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, []);

    // Menu Utama — fitur inti deteksi hoaks untuk user
    const mainMenuItems: MenuItem[] = [
        { label: "Deteksi Berita", href: "/", icon: BrainCircuit },
        { label: "Riwayat Saya", href: "/history", icon: History },
        {
            label: "Feedback Saya",
            href: "/feedback",
            icon: MessageSquareQuote,
            badge: feedbackCount > 0 ? String(feedbackCount) : undefined,
        },
    ];

    // Akun — pengaturan & bantuan user
    const accountMenuItems: MenuItem[] = [
        { label: "Profil Saya", href: "/profile", icon: UserCircle },
        { label: "Pengaturan", href: "/settings", icon: Settings },
        { label: "Bantuan", href: "/help", icon: HelpCircle },
    ];

    const filteredMain = useMemo(
        () => mainMenuItems.filter((item) => item.label.toLowerCase().includes(query.toLowerCase())),
        [query, feedbackCount]
    );
    const filteredAccount = useMemo(
        () => accountMenuItems.filter((item) => item.label.toLowerCase().includes(query.toLowerCase())),
        [query]
    );
    const noResults = query.trim() !== "" && filteredMain.length === 0 && filteredAccount.length === 0;

    const renderMenuGroup = (title: string, items: MenuItem[], withDivider = false) => {
        if (items.length === 0) return null;
        return (
            <div className={withDivider ? "border-t border-white/[0.08] pt-5" : ""}>
                {!collapsed && (
                    <p className="text-[11px] font-semibold text-emerald-100/45 tracking-wide px-3 mb-2">
                        {title}
                    </p>
                )}
                <nav className="space-y-1">
                    {items.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                title={collapsed ? item.label : undefined}
                                className={`group relative flex items-center overflow-hidden rounded-xl text-[13px] font-medium transition-all duration-200 ${collapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
                                    } ${isActive
                                        ? "bg-gradient-to-r from-white/[0.07] via-emerald-300/[0.12] to-emerald-400/35 text-white ring-1 ring-white/10"
                                        : "text-emerald-50/65 hover:bg-white/[0.06] hover:text-white"
                                    }`}
                            >
                                <div className={`flex items-center ${collapsed ? "" : "gap-3"}`}>
                                    <Icon
                                        strokeWidth={1.75}
                                        className={`w-[18px] h-[18px] shrink-0 transition-colors ${isActive
                                            ? "text-white"
                                            : "text-emerald-100/50 group-hover:text-emerald-100"
                                            }`}
                                    />
                                    {!collapsed && <span>{item.label}</span>}
                                </div>

                                {!collapsed && item.badge && !isActive && (
                                    <span className="text-[10px] min-w-[20px] text-center px-1.5 py-0.5 bg-emerald-300/15 text-emerald-100 font-semibold rounded-full ring-1 ring-emerald-200/20">
                                        {item.badge}
                                    </span>
                                )}

                                {/* Garis aksen di sisi kanan untuk menu aktif */}
                                {isActive && (
                                    <span className="absolute right-0 top-0 h-full w-[3px] bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.8)]" />
                                )}

                                {/* Badge kecil di pojok saat collapsed */}
                                {collapsed && item.badge && (
                                    <span className="absolute top-1 right-1 w-3.5 h-3.5 flex items-center justify-center text-[8px] bg-emerald-400 text-emerald-950 font-bold rounded-full">
                                        {item.badge}
                                    </span>
                                )}

                                {/* Tooltip kaca saat collapsed */}
                                {collapsed && (
                                    <span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-lg bg-[#0b2520]/90 backdrop-blur-xl ring-1 ring-white/15 px-2.5 py-1.5 text-[11px] font-medium text-white opacity-0 shadow-xl transition-opacity duration-150 group-hover:opacity-100 z-50">
                                        {item.label}
                                    </span>
                                )}
                            </Link>
                        );
                    })}
                </nav>
            </div>
        );
    };

    return (
        <aside
            className={`${collapsed ? "w-20" : "w-64"
                } relative z-20 flex flex-col justify-between h-screen border-r border-white/10 p-3.5 text-emerald-100/70 select-none shrink-0 font-sans transition-[width] duration-300 ease-in-out`}
        >
            {/* Latar: dasar hijau tua + glow lembut, lalu lapisan kaca blur di atasnya */}
            <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-[#071d19]">
                <div className="absolute -top-24 -left-20 h-72 w-72 rounded-full bg-emerald-500/30 blur-3xl" />
                <div className="absolute top-1/2 -right-24 h-64 w-64 rounded-full bg-teal-400/15 blur-3xl" />
                <div className="absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-emerald-300/15 blur-3xl" />
                <div className="absolute inset-0 bg-gradient-to-b from-white/[0.06] via-transparent to-black/20 backdrop-blur-2xl" />
            </div>

            {/* BAGIAN ATAS: LOGO + SEARCH + MENU */}
            <div
                className={`space-y-5 pr-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden ${collapsed ? "overflow-visible" : "overflow-y-auto overflow-x-hidden"
                    }`}
            >
                {/* Brand Header VERIDIX & Collapse Icon */}
                <div
                    className={`flex items-center pt-1 pb-4 border-b border-white/[0.08] ${collapsed ? "flex-col gap-3" : "justify-between px-1"
                        }`}
                >
                    <div className={`flex items-center ${collapsed ? "" : "gap-2.5"}`}>
                        {/* Wadah Logo Gambar Monogram V */}
                        <div className="w-9 h-9 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center p-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.15)] shrink-0 backdrop-blur-md">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                                src="/logo.png"
                                alt="VERIDIX Logo"
                                className="w-full h-full object-contain drop-shadow-sm"
                            />
                        </div>
                        {!collapsed && (
                            <div className="leading-tight">
                                <div className="flex items-center gap-1.5">
                                    <span className="text-sm font-extrabold text-white tracking-wider">VERIDIX</span>
                                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(103,232,249,0.9)] animate-pulse"></span>
                                </div>
                                <p className="text-[10px] text-emerald-200/65 font-medium">AI Fact Intelligence</p>
                            </div>
                        )}
                    </div>
                    <button
                        type="button"
                        onClick={() => setCollapsed((prev) => !prev)}
                        className="p-1.5 rounded-lg border border-white/10 text-emerald-100/60 hover:text-white hover:bg-white/10 transition shrink-0"
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

                {/* Input Pencarian */}
                {collapsed ? (
                    <button
                        type="button"
                        onClick={() => {
                            setCollapsed(false);
                            setTimeout(() => searchInputRef.current?.focus(), 50);
                        }}
                        className="w-full flex items-center justify-center p-2.5 bg-white/[0.04] rounded-xl border border-white/10 hover:border-emerald-300/40 hover:bg-white/[0.08] transition"
                        title="Cari berita"
                    >
                        <Search className="w-4 h-4 text-emerald-100/70" />
                    </button>
                ) : (
                    <div className="relative">
                        <Search className="w-3.5 h-3.5 text-emerald-100/50 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            ref={searchInputRef}
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Cari berita..."
                            className="w-full bg-white/[0.04] text-xs text-white placeholder-emerald-100/40 pl-8 pr-12 py-2.5 rounded-xl border border-white/10 focus:border-emerald-300/50 focus:bg-white/[0.08] focus:outline-none transition"
                        />
                        {query ? (
                            <button
                                type="button"
                                onClick={() => setQuery("")}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-emerald-100/70 hover:text-white bg-white/10 px-1.5 py-0.5 rounded-md"
                            >
                                ✕
                            </button>
                        ) : (
                            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-emerald-100/60 bg-white/[0.07] px-1.5 py-0.5 rounded-md border border-white/10 font-mono">
                                ⌘ F
                            </kbd>
                        )}
                    </div>
                )}

                {renderMenuGroup("Menu Utama", filteredMain)}
                {renderMenuGroup("Akun", filteredAccount, filteredMain.length > 0)}

                {!collapsed && noResults && (
                    <p className="text-[11px] text-emerald-100/50 text-center px-3 py-2">
                        Menu "{query}" tidak ditemukan.
                    </p>
                )}
            </div>

            {/* BAGIAN BAWAH: KARTU PROFIL USER */}
            <div className="pt-3">
                <div
                    className={`bg-white/[0.05] border border-white/10 rounded-2xl flex items-center backdrop-blur-md ${collapsed ? "flex-col gap-2 p-2" : "justify-between p-2.5"
                        }`}
                >
                    <div className={`flex items-center ${collapsed ? "flex-col" : "gap-2.5"}`}>
                        <div
                            title={collapsed ? (guest ? "Mode Tamu" : userName) : undefined}
                            className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-300/35 to-teal-500/25 border border-white/20 text-white flex items-center justify-center font-bold text-xs shrink-0"
                        >
                            {guest ? "G" : userName.charAt(0)}
                        </div>
                        {!collapsed && (
                            <div className="leading-tight truncate max-w-[110px]">
                                <p className="text-xs font-semibold text-white truncate">
                                    {guest ? "Mode Tamu" : userName}
                                </p>
                                <p className="text-[10px] text-emerald-100/55 truncate">
                                    {guest ? "Masuk untuk mendeteksi" : "User Terdaftar"}
                                </p>
                            </div>
                        )}
                    </div>

                    <button
                        type="button"
                        onClick={onLogout}
                        className="p-1.5 rounded-lg text-emerald-100/70 hover:text-white hover:bg-white/10 transition"
                        title={guest ? "Masuk ke Akun" : "Keluar"}
                    >
                        <LogOut className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>
        </aside>
    );
}