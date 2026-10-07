"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useDetection } from "@/hooks/useDetection";
import { useHistory } from "@/hooks/useHistory";

import UserShell from "@/components/layout/UserShell";
import HeaderStats from "@/components/layout/HeaderStats";
import GuestBanner from "@/components/shared/GuestBanner";
import NewsInputForm from "@/components/detector/NewsInputForm";
import VerdictCard from "@/components/detector/VerdictCard";

export default function Home() {
    const { user, isGuest, logout } = useAuth();
    const d = useDetection();
    const history = useHistory(!isGuest);

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
        <UserShell
            guest={isGuest}
            userName={user?.name || "Amos Manurung"}
            userRole={user?.role || "USER"}
            onLogout={logout}
        >
            {/* Banner Kuota jika Mode Tamu */}
            {isGuest && <GuestBanner remainingFreeDetections={guestQuota} />}

            {/* 4 Kartu Metrik Ringkasan */}
            <HeaderStats
                totalDetections={0}
                hoaxCount={0}
                feedbackCount={0}
                quotaLeft={guestQuota}
                isGuest={isGuest}
            />

            {/* Grid Formulir Input dan Hasil Deteksi */}
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
        </UserShell>
    );
}