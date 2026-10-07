import { LayoutDashboard, History, MessageSquare, User, Settings, HelpCircle, type LucideIcon } from "lucide-react";

export type NavKey = "deteksi" | "riwayat" | "feedback" | "profil" | "pengaturan" | "bantuan";

export interface NavItem {
    key: NavKey;
    label: string;
    href?: string;      // tanpa href = belum tersedia (tampil nonaktif)
    icon: LucideIcon;
    badge?: boolean;    // tampilkan jumlah feedback yang sedang diproses
}

export const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
    {
        title: "Menu utama",
        items: [
            { key: "deteksi", label: "Deteksi berita", href: "/", icon: LayoutDashboard },
            { key: "riwayat", label: "Riwayat saya", href: "/history", icon: History },
            { key: "feedback", label: "Feedback saya", href: "/history?tab=feedback", icon: MessageSquare, badge: true },
        ],
    },
    {
        title: "Akun",
        items: [
            { key: "profil", label: "Profil saya", href: "/profile", icon: User },
            { key: "pengaturan", label: "Pengaturan", href: "/profile#keamanan", icon: Settings },
            { key: "bantuan", label: "Bantuan", icon: HelpCircle },
        ],
    },
];