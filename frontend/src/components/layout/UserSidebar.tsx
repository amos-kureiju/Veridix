"use client";
import { useEffect, useRef, useState } from "react";
import { PanelLeftClose, PanelLeftOpen, Search, ShieldCheck } from "lucide-react";
import { NAV_GROUPS, type NavKey } from "@/lib/navigation";
import type { User } from "@/types/user";
import { cn } from "@/lib/utils";
import SidebarNavItem from "./SidebarNavItem";
import SidebarUserCard from "./SidebarUserCard";

interface Props {
    user: User | null;
    active: NavKey;
    feedbackBadge?: number;
    onLogout: () => void;
}

export default function UserSidebar({ user, active, feedbackBadge = 0, onLogout }: Props) {
    const [collapsed, setCollapsed] = useState(false);
    const searchRef = useRef<HTMLInputElement>(null);

    // Pintasan Ctrl/Cmd + K untuk fokus ke kolom cari
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                setCollapsed(false);
                setTimeout(() => searchRef.current?.focus(), 0);
            }
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, []);// di atas return, tambahkan:
    const lastGroup = NAV_GROUPS[NAV_GROUPS.length - 1];
    const topGroups = NAV_GROUPS.slice(0, -1);

    const renderGroup = (group: (typeof NAV_GROUPS)[number]) => (
        <div key={group.title}>
            {!collapsed && <p className="mb-1.5 px-2 text-xs font-medium text-emerald-200/50">{group.title}</p>}
            <ul className="space-y-0.5">
                {group.items.map((item) => (
                    <li key={item.key}>
                        <SidebarNavItem item={item} active={item.key === active} collapsed={collapsed} badgeCount={feedbackBadge} />
                    </li>
                ))}
            </ul>
        </div>
    );

    return (
        <aside
            className={cn(
                "hidden shrink-0 flex-col bg-[#14392f] p-4 text-emerald-50 transition-[width] duration-200 lg:flex",
                collapsed ? "w-[76px]" : "w-64"
            )}
        >
            {/* Logo + tombol ciutkan */}
            <div className={cn("flex items-center pb-4", collapsed ? "flex-col gap-3" : "justify-between px-1")}>
                <div className="flex items-center gap-2.5">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-emerald-400/15 text-emerald-300">
                        <ShieldCheck size={20} />
                    </span>
                    {!collapsed && (
                        <div className="leading-tight">
                            <p className="font-semibold text-white">INSPECT-AI</p>
                            <p className="text-xs text-emerald-200/60">Deteksi hoaks politik</p>
                        </div>
                    )}
                </div>
                <button
                    onClick={() => setCollapsed((v) => !v)}
                    aria-label={collapsed ? "Perluas sidebar" : "Ciutkan sidebar"}
                    className="rounded-lg border border-white/10 p-1.5 text-emerald-100/80 hover:bg-white/10"
                >
                    {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
                </button>
            </div>

            <div className="mb-4 border-t border-dashed border-white/10" />

            {/* Cari riwayat (diarahkan ke /history?q=...) */}
            {collapsed ? (
                <a href="/history" aria-label="Cari riwayat" className="mb-5 grid h-10 place-items-center rounded-xl border border-white/10 bg-white/5 hover:bg-white/10">
                    <Search size={16} />
                </a>
            ) : (
                <form action="/history" className="relative mb-5">
                    <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-emerald-200/60" />
                    <input
                        ref={searchRef}
                        name="q"
                        placeholder="Cari berita…"
                        className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-9 pr-12 text-sm text-white placeholder:text-emerald-200/50 focus:border-emerald-300/50 focus:outline-none"
                    />
                    <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md border border-white/10 px-1.5 py-0.5 text-[10px] text-emerald-200/70">
                        ⌘K
                    </kbd>
                </form>
            )}

            // ganti blok <nav>...</nav> lama dengan:
            <nav className="flex-1 space-y-5 overflow-y-auto">{topGroups.map(renderGroup)}</nav>
            <div className="mb-3 mt-4 border-t border-dashed border-white/10 pt-4">{renderGroup(lastGroup)}</div>

            {/* Profil + keluar */}
            <SidebarUserCard user={user} collapsed={collapsed} onLogout={onLogout} />
        </aside>
    );
}