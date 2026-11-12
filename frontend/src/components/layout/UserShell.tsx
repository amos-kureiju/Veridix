"use client";

import UserSidebar from "./UserSidebar";
import UserTopbar from "./UserTopbar";
import { useRouter } from "next/navigation";
import Footer from "@/components/shared/footer";

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
    userName = "Pengguna",
    userRole = "USER",
    title,
    subtitle,
    onLogout,
    children,
}: UserShellProps) {
    const router = useRouter();
    const handleAccountAction = guest ? () => router.push("/auth/login") : onLogout;
    return (
        // 1. Kunci layar total (h-screen overflow-hidden)
        <div className="flex h-screen w-full bg-[#f1f5f5] text-slate-800 overflow-hidden font-sans">

            {/* 2. Sidebar Kiri (Menetap permanen) */}
            <UserSidebar guest={guest} userName={userName} onLogout={handleAccountAction} />

            {/* 3. Kolom Kanan — "relative" supaya topbar overlay menempel di kolom ini */}
            <div className="relative flex-1 flex flex-col h-screen min-w-0 overflow-hidden">

                {/* TOPBAR KACA — menumpuk di atas konten agar blur terlihat */}
                <UserTopbar
                    overlay
                    title={title}
                    subtitle={subtitle}
                    userName={userName}
                    userRole={userRole}
                    guest={guest}
                    onLogout={handleAccountAction}
                />

                {/* AREA KONTEN — pt-[95px] memberi ruang setinggi topbar, konten tetap bergulir di bawah kaca */}
                <main className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 pb-6 pt-[95px] lg:px-8">
                    <div className="flex-1 space-y-6">
                        {children}
                    </div>
                    <Footer guest={guest} />
                </main>

            </div>
        </div>
    );
}