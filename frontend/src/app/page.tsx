"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useDetection } from "@/hooks/useDetection";
import { useHistory } from "@/hooks/useHistory";
import { useState as useReactState } from "react";

// Komponen Layout & Shared yang sudah ada
import UserSidebar from "@/components/layout/UserSidebar";
import HeaderStats from "@/components/layout/HeaderStats";
import GuestBanner from "@/components/shared/GuestBanner";

// Komponen Detector
import NewsInputForm from "@/components/detector/NewsInputForm";
import VerdictCard from "@/components/detector/VerdictCard";

export default function Home() {
    const { user, isGuest, logout } = useAuth();
    const d = useDetection();
    const history = useHistory(!!user);

    // State sederhana untuk kuota tamu (jika belum ada hook khusus, kita kelola lokal)
    const [guestQuota, setGuestQuota] = useState(3);
    const blocked = isGuest && guestQuota === 0;

    const analyze = async (text: string) => {
        if (blocked) return;
        await d.detectText(text);
        if (isGuest) {
            setGuestQuota((prev) => Math.max(0, prev - 1));
        } else {
            history.reload();
        }
    };

    return (
        <div className="flex h-screen bg-slate-950 text-white overflow-hidden">
            {/* Sidebar Navigasi User */}
            <UserSidebar />

            {/* Konten Utama */}
            <main className="flex-1 overflow-y-auto p-8 lg:p-10 space-y-6">

                {/* Banner Tamu jika belum login */}
                {isGuest && <GuestBanner remainingFreeDetections={guestQuota} />}

                {/* Header Statistik */}
                <HeaderStats />

                {/* Pesan Error jika ada */}
                {d.error && (
                    <div className="rounded-xl bg-rose-500/10 border border-rose-500/20 p-4 text-sm text-rose-400">
                        {d.error}
                    </div>
                )}

                {/* Grid Utama: Form Input di Kiri, Hasil Analisis di Kanan */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                    <NewsInputForm
                        loading={d.loading}
                        blocked={blocked}
                        onAnalyze={analyze}
                    />
                    <VerdictCard
                        result={d.result}
                        loading={d.loading}
                    />
                </div>
            </main>
        </div>
    );
}