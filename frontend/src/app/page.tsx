"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useDetection } from "@/hooks/useDetection";
import { useHistory } from "@/hooks/useHistory";

import UserShell from "@/components/layout/UserShell";
import HeaderStats from "@/components/layout/HeaderStats";
import GuestBanner from "@/components/shared/GuestBanner";
import NewsInputForm from "@/components/detector/NewsInputForm";
import VerdictCard from "@/components/detector/VerdictCard";

export default function Home() {
    const router = useRouter();
    const { user, ready, logout } = useAuth();
    const d = useDetection();
    const history = useHistory(ready && Boolean(user));
    const isGuest = !user;

    const requireLogin = () => router.push("/auth/login");

    const analyze = async (text: string) => {
        if (!ready) return;
        if (!user) {
            requireLogin();
            return;
        }
        const result = await d.detectText(text);
        if (result) await history.reload();
    };

    return (
        <UserShell
            guest={isGuest}
            userName={user?.name || "Pengunjung"}
            userRole={user?.role || "USER"}
            onLogout={logout}
        >
            {isGuest && <GuestBanner />}

            {/* 4 Kartu Metrik Ringkasan */}
            <HeaderStats
                totalDetections={user?.total_detections ?? 0}
                hoaxCount={0}
                feedbackCount={user?.total_feedbacks ?? 0}
                isGuest={isGuest}
            />

            {/* Grid Formulir Input dan Hasil Deteksi */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-6">
                <div className="space-y-3">
                    <NewsInputForm
                        loading={d.loading}
                        blocked={!ready}
                        loginRequired={isGuest}
                        onRequireLogin={requireLogin}
                        onAnalyze={analyze}
                    />
                    {d.error && <p role="alert" className="text-sm text-rose-600">{d.error}</p>}
                </div>
                <VerdictCard
                    result={d.result}
                    loading={d.loading}
                />
            </div>
        </UserShell>
    );
}
