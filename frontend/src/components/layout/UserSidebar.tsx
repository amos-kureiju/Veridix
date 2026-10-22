"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect, useMemo } from "react";
import {
    Search,
    Newspaper,
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
    icon: typeof Newspaper;
    badge?: string;
};

export default function UserSidebar({
    onLogout,
    guest = false,
    userName = "Amos Manurung",
    feedbackCount = 2,
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
        { label: "Deteksi Berita", href: "/", icon: Newspaper },
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

    const renderMenuGroup = (title: string, items: MenuItem[]) => {
        if (items.length === 0) return null;
        return (
            <div>
                {!collapsed && (
                    <p className="text-[10px] uppercase font-bold text-emerald-400/60 tracking-wider px-3 mb-1.5">
                        {title}
                    </p>
                )}
                <nav className="space-y-0.5">
                    {items.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                title={collapsed ? item.label : undefined}
                                className={`group relative flex items-center rounded-xl text-[13px] font-medium transition-all ${collapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
                                    } ${isActive
                                        ? "bg-emerald-500/15 text-white ring-1 ring-emerald-400/30"
                                        : "text-emerald-100/70 hover:bg-[#12362f] hover:text-white"
                                    }`}
                            >
                                <div className={`flex items-center ${collapsed ? "" : "gap-2.5"}`}>
                                    <Icon
                                        strokeWidth={2}
                                        className={`w-[18px] h-[18px] shrink-0 ${isActive
                                                ? "text-emerald-400"
                                                : "text-emerald-300/60 group-hover:text-emerald-300"
                                            }`}
                                    />
                                    {!collapsed && <span>{item.label}</span>}
                                </div>

                                {!collapsed && item.badge && !isActive && (
                                    <span className="text-[10px] px-1.5 py-0.5 bg-[#061814] text-emerald-300 font-semibold rounded-md border border-[#163d34]">
                                        {item.badge}
                                    </span>
                                )}

                                {!collapsed && isActive && (
                                    <span className="w-1 h-4 bg-emerald-400 rounded-full" />
                                )}

                                {/* Badge kecil di pojok saat collapsed */}
                                {collapsed && item.badge && (
                                    <span className="absolute top-1 right-1 w-3.5 h-3.5 flex items-center justify-center text-[8px] bg-emerald-500 text-white font-bold rounded-full">
                                        {item.badge}
                                    </span>
                                )}

                                {/* Tooltip modern saat collapsed */}
                                {collapsed && (
                                    <span className="pointer-events-none absolute left-full ml-2 whitespace-nowrap rounded-lg bg-[#0b2520] border border-[#194038] px-2.5 py-1.5 text-[11px] font-medium text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 z-50">
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
                } bg-[#0b2520] text-emerald-100/70 flex flex-col justify-between h-screen border-r border-[#133730] p-3.5 select-none shrink-0 font-sans transition-[width] duration-300 ease-in-out`}
        >
            {/* BAGIAN ATAS: LOGO + SEARCH + MENU */}
            <div className="space-y-5 overflow-y-auto overflow-x-hidden pr-1">

                {/* Brand Header VERIDIX & Collapse Icon */}
                <div className={`flex items-center pt-1 ${collapsed ? "flex-col gap-2" : "justify-between px-2"}`}>
                    <div className={`flex items-center ${collapsed ? "" : "gap-2.5"}`}>
                        {/* Wadah Logo Gambar Monogram V */}
                        <div className="w-9 h-9 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center p-1.5 shadow-sm shrink-0 backdrop-blur-xs">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                                src="/logo.png"
                                alt="VERIDIX Logo"
                                className="w-full h-full object-contain drop-shadow-sm"
                            />
                        </div>
                        {!collapsed && (
                            <div className="leading-tight">
                                <div className="flex items-center gap-1">
                                    <span className="text-sm font-extrabold text-white tracking-wider">VERIDIX</span>
                                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                                </div>
                                <p className="text-[10px] text-emerald-400/80 font-medium">AI Fact Intelligence</p>
                            </div>
                        )}
                    </div>
                    <button
                        type="button"
                        onClick={() => setCollapsed((prev) => !prev)}
                        className="p-1.5 rounded-lg text-emerald-300/60 hover:text-white hover:bg-[#12362f] transition shrink-0"
                        title={collapsed ? "Perluas sidebar" : "Sembunyikan sidebar"}
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
                        className="w-full flex items-center justify-center p-2.5 bg-[#12332c] rounded-xl border border-transparent hover:border-emerald-500/30 transition"
                        title="Cari berita"
                    >
                        <Search className="w-4 h-4 text-emerald-400/70" />
                    </button>
                ) : (
                    <div className="relative">
                        <Search className="w-3.5 h-3.5 text-emerald-400/60 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            ref={searchInputRef}
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Cari berita..."
                            className="w-full bg-[#12332c] text-xs text-white placeholder-emerald-400/50 pl-8 pr-10 py-2.5 rounded-xl border border-transparent focus:border-emerald-500/40 focus:outline-none transition shadow-inner"
                        />
                        {query ? (
                            <button
                                type="button"
                                onClick={() => setQuery("")}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-emerald-300/60 hover:text-white bg-[#194038] px-1.5 py-0.5 rounded"
                            >
                                ✕
                            </button>
                        ) : (
                            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-emerald-300/60 bg-[#194038] px-1.5 py-0.5 rounded border border-emerald-500/20 font-mono">
                                ⌘ F
                            </kbd>
                        )}
                    </div>
                )}

                {renderMenuGroup("Menu Utama", filteredMain)}
                {renderMenuGroup("Akun", filteredAccount)}

                {!collapsed && noResults && (
                    <p className="text-[11px] text-emerald-400/50 text-center px-3 py-2">
                        Menu "{query}" tidak ditemukan.
                    </p>
                )}
            </div>

            {/* BAGIAN BAWAH: KARTU PROFIL USER */}
            <div className="pt-3 border-t border-[#133730]">
                <div
                    className={`bg-[#12332c] border border-[#184239] rounded-xl shadow-sm flex items-center ${collapsed ? "flex-col gap-2 p-2" : "justify-between p-2.5"
                        }`}
                >
                    <div className={`flex items-center ${collapsed ? "flex-col" : "gap-2.5"}`}>
                        <div
                            title={collapsed ? (guest ? "Mode Tamu" : userName) : undefined}
                            className="w-8 h-8 rounded-lg bg-emerald-700/50 border border-emerald-400/40 text-emerald-200 flex items-center justify-center font-bold text-xs shrink-0"
                        >
                            {guest ? "G" : userName.charAt(0)}
                        </div>
                        {!collapsed && (
                            <div className="leading-tight truncate max-w-[105px]">
                                <p className="text-xs font-semibold text-white truncate">
                                    {guest ? "Mode Tamu" : userName}
                                </p>
                                <p className="text-[10px] text-emerald-400/70 truncate">
                                    {guest ? "Masuk untuk mendeteksi" : "User Terdaftar"}
                                </p>
                            </div>
                        )}
                    </div>

                    <button
                        type="button"
                        onClick={onLogout}
                        className="p-1.5 rounded-lg text-emerald-300/70 hover:text-white hover:bg-[#1a443b] transition"
                        title={guest ? "Masuk ke Akun" : "Keluar"}
                    >
                        <LogOut className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>
        </aside>
    );
}
