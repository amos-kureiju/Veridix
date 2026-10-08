    "use client";

    import Link from "next/link";
    import { usePathname } from "next/navigation";
    import {
        LayoutDashboard,
        FileText,
        MessageSquare,
        Sliders,
        Users,
        Download,
        LogOut,
        Sparkles,
        Search,
        ExternalLink
    } from "lucide-react";

    interface AdminSidebarProps {
        onLogout?: () => void;
    }

    export default function AdminSidebar({ onLogout }: AdminSidebarProps) {
        const pathname = usePathname();

        const adminMenu = [
            { label: "Dashboard", href: "/admin", icon: LayoutDashboard },
            { label: "Log Deteksi Global", href: "/admin/logs", icon: FileText },
            { label: "Kelola Masukan", href: "/admin/feedback", icon: MessageSquare, badge: "8" },
            { label: "Kontrol Threshold", href: "/admin/threshold", icon: Sliders },
            { label: "Kelola Pengguna", href: "/admin/users", icon: Users },
            { label: "Ekspor Laporan", href: "/admin/export", icon: Download },
        ];

        return (
            <aside className="w-64 bg-white border-r border-slate-200/80 h-screen flex flex-col justify-between p-4 select-none shrink-0 font-sans">

                {/* 1. BRAND LOGO & PENCARIAN */}
                <div className="space-y-5">

                    {/* Header Monogram VERIDIX */}
                    <div className="flex items-center gap-3 px-2 pt-1">
                        <div className="w-9 h-9 rounded-xl bg-[#0b2520] border border-[#173f36] flex items-center justify-center p-1.5 shadow-sm shrink-0">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src="/logo.png" alt="VERIDIX Logo" className="w-full h-full object-contain" />
                        </div>
                        <div>
                            <div className="flex items-center gap-1.5">
                                <span className="text-sm font-extrabold text-slate-900 tracking-wider">VERIDIX</span>
                                <span className="text-[10px] bg-slate-900 text-white font-mono px-1.5 py-0.2 rounded-md font-bold">
                                    ADMIN
                                </span>
                            </div>
                            <p className="text-[10px] text-slate-400 font-medium">Fact Intelligence Ops</p>
                        </div>
                    </div>

                    {/* Status AI Engine Banner (Ala Cazura AI Assistant) */}
                    <div className="bg-emerald-50/70 border border-emerald-200/60 rounded-2xl p-3 flex items-center gap-2.5 text-xs text-emerald-800">
                        <div className="w-7 h-7 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                            <Sparkles className="w-3.5 h-3.5" />
                        </div>
                        <div className="leading-tight truncate">
                            <p className="font-bold truncate">IndoBERT Engine v2</p>
                            <p className="text-[10px] text-emerald-600 truncate">Status: Siap Inferensi</p>
                        </div>
                    </div>

                    {/* Navigasi Utama Panel Admin */}
                    <div className="space-y-1">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 mb-2">
                            Main Management
                        </p>
                        <nav className="space-y-0.5">
                            {adminMenu.map((item) => {
                                const Icon = item.icon;
                                const isActive = pathname === item.href;
                                return (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition group ${isActive
                                                ? "bg-[#0b2520] text-white shadow-sm"
                                                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                                            }`}
                                    >
                                        <div className="flex items-center gap-2.5">
                                            <Icon className={`w-4 h-4 ${isActive ? "text-emerald-400" : "text-slate-400 group-hover:text-slate-700"}`} />
                                            <span>{item.label}</span>
                                        </div>

                                        {item.badge && !isActive && (
                                            <span className="text-[10px] px-1.5 py-0.2 bg-slate-900 text-white rounded-md font-bold">
                                                {item.badge}
                                            </span>
                                        )}
                                    </Link>
                                );
                            })}
                        </nav>
                    </div>

                    {/* Tautan Kembali ke Sisi Pengguna */}
                    <div className="pt-2 border-t border-slate-100">
                        <Link
                            href="/"
                            className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
                        >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span>Kembali ke Beranda User</span>
                        </Link>
                    </div>

                </div>

                {/* 2. FOOTER KARTU ADMIN (Ala Kartu Akun Cazura) */}
                <div className="pt-3 border-t border-slate-100">
                    <div className="bg-[#f8fafc] border border-slate-200/80 rounded-2xl p-3 flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs shrink-0">
                                A
                            </div>
                            <div className="leading-tight truncate max-w-[110px]">
                                <p className="text-xs font-bold text-slate-800 truncate">Administrator</p>
                                <p className="text-[10px] text-slate-400 truncate">Super Admin</p>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={onLogout}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition"
                            title="Keluar Admin"
                        >
                            <LogOut className="w-4 h-4" />
                        </button>
                    </div>
                </div>

            </aside>
        );
    }