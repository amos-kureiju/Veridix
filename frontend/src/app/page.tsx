"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useDetection } from "@/hooks/useDetection";
import { useHistory } from "@/hooks/useHistory";

// Layout & Komponen Visual
import UserSidebar from "@/components/layout/UserSidebar";
import UserTopbar from "@/components/layout/UserTopbar";
import HeaderStats from "@/components/layout/HeaderStats";
import GuestBanner from "@/components/shared/GuestBanner";

// Komponen Deteksi
import NewsInputForm from "@/components/detector/NewsInputForm";
import VerdictCard from "@/components/detector/VerdictCard";

export default function Home() {
    const { user, isGuest } = useAuth();
    const d = useDetection();
    const history = useHistory(!!user);

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
        <div className="flex h-screen bg-[#f1f5f5] text-slate-800 overflow-hidden font-sans">

            {/* 1. Sidebar Hijau Vizora di Kiri */}
            <UserSidebar guest={isGuest} />

            {/* 2. Area Konten Utama di Kanan */}
            <main className="flex-1 overflow-y-auto px-8 py-6 space-y-5">

                {/* TOPBAR HEADER VIZORA DI PALING ATAS */}
                <UserTopbar
                    title="Dashboard"
                    subtitle={isGuest ? "Selamat datang di INSPECT-AI (Mode Tamu)" : `Welcome back ${user?.name || "Tony Robert"}`}
                />

                {/* Banner Tamu jika belum login */}
                {isGuest && <GuestBanner remainingFreeDetections={guestQuota} />}

                {/* 4 Kartu Mini Statistik */}
                <HeaderStats
                    totalDetections={0}
                    hoaxCount={0}
                    feedbackCount={0}
                    quotaLeft={guestQuota}
                    isGuest={isGuest}
                />

                {/* Alert Error jika ada kendala backend */}
                {d.error && (
                    <div className="rounded-2xl bg-rose-50 border border-rose-200 p-4 text-xs text-rose-600">
                        {d.error}
                    </div>
                )}

                {/* Grid Dua Kolom: Input & Hasil */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-6">
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