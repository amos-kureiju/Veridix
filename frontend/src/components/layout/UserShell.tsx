"use client";

import UserSidebar from "./UserSidebar";
import UserTopbar from "./UserTopbar";

interface UserShellProps {
    guest?: boolean;
    userName?: string;
    userRole?: string;
    title?: string;
    subtitle?: string;
    onLogout?: () => void;
    children: React.ReactNode;
}

export default function UserShell({
    guest = false,
    userName = "Amos Manurung",
    userRole = "USER",
    title,
    subtitle,
    onLogout,
    children,
}: UserShellProps) {
    return (
        // 1. Kunci layar total (h-screen overflow-hidden)
        <div className="flex h-screen w-full bg-[#f1f5f5] text-slate-800 overflow-hidden font-sans">

            {/* 2. Sidebar Kiri (Menetap permanen) */}
            <UserSidebar guest={guest} userName={userName} onLogout={onLogout} />

            {/* 3. Kolom Kanan Membentang Penuh */}
            <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">

                {/* TOPBAR MENEMPEL PENUH DI ATAS (TIDAK ADA CELAH / BORDER MELAYANG) */}
                <UserTopbar
                    title={title}
                    subtitle={subtitle}
                    userName={userName}
                    userRole={userRole}
                    guest={guest}
                    onLogout={onLogout}
                />

                {/* AREA KONTEN (HANYA INI YANG BERGULIR SAAT DI-SCROLL) */}
                <main className="flex-1 overflow-y-auto px-6 lg:px-8 py-6 space-y-6">
                    {children}
                </main>

            </div>
        </div>
    );
}