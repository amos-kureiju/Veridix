"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import AdminShell from "@/components/layout/AdminShell";
import { Loader2, ShieldAlert } from "lucide-react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const { user, ready, isAdmin, sessionError, retrySession } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!ready || sessionError) return;

        // 1. Tamu / Belum login: arahkan ke halaman login
        if (!user) {
            router.replace("/auth/login");
            return;
        }

        // 2. User biasa: tolak dan kembalikan ke beranda publik
        if (!isAdmin) {
            router.replace("/");
        }
    }, [user, ready, isAdmin, sessionError, router]);

    // Indikator Loading Saat Sesi Masih Diperiksa
    if (!ready) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-slate-50">
                <div className="flex flex-col items-center gap-3 text-slate-500">
                    <Loader2 size={32} className="animate-spin text-emerald-600" />
                    <p className="text-sm font-medium">Memverifikasi kredensial sesi…</p>
                </div>
            </div>
        );
    }

    // Penanganan Gangguan Jaringan (Bukan Logout Otomatis)
    if (sessionError) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
                <div className="max-w-md rounded-2xl border border-rose-200 bg-white p-6 text-center shadow-sm">
                    <ShieldAlert size={40} className="mx-auto text-rose-500 mb-3" />
                    <h2 className="text-lg font-bold text-slate-900">Gagal Menghubungi Server</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        Tidak dapat memverifikasi hak akses administrator. Pastikan backend aktif.
                    </p>
                    <button
                        onClick={retrySession}
                        className="mt-4 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
                    >
                        Coba Lagi
                    </button>
                </div>
            </div>
        );
    }

    // Blok konten jika bukan admin
    if (!user || !isAdmin) {
        return null;
    }

    return <>{children}</>;
}