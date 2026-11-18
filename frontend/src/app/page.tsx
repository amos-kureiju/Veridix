"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useDetection } from "@/hooks/useDetection";
import { useHistory } from "@/hooks/useHistory";
import type { InputSourceType } from "@/types/detector";
import { DOCUMENT_SEGMENT_WORD_LIMIT, documentWordCount } from "@/types/document-analysis";
import type { DocumentPage } from "@/types/document-analysis";

import UserShell from "@/components/layout/UserShell";
import HeaderStats from "@/components/layout/HeaderStats";
import GuestBanner from "@/components/shared/GuestBanner";
import NewsInputForm from "@/components/detector/NewsInputForm";
import VerdictCard from "@/components/detector/VerdictCard";
import DocumentResultCard from "@/components/detector/DocumentResultCard";

export default function Home() {
    const router = useRouter();
    const { user, ready, logout, refreshUser } = useAuth();
    const isAdminUser = ready && user?.role === "ADMIN";
    const isRegularUser = ready && user?.role === "USER";
    const isGuest = !user;

    const userId = user?.id ?? null;
    const analysisOwnerId = isRegularUser ? userId : null;
    const d = useDetection(analysisOwnerId);
    const history = useHistory(isRegularUser);

    // Sesi berakhir atau pengguna berganti: bersihkan hasil dan permintaan aktif
    useEffect(() => {
        d.reset();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [analysisOwnerId]);

    // Alihkan ADMIN langsung ke /admin jika membuka beranda "/"
    useEffect(() => {
        if (isAdminUser) {
            router.replace("/admin");
        }
    }, [isAdminUser, router]);

    const requireLogin = () => router.push("/auth/login");

    const canAnalyze = () => {
        if (ready && !user) requireLogin();
        return isRegularUser;
    };

    const analyze = async (
        text: string,
        source: InputSourceType = "TEXT",
        imageUrl?: string | null,
        forceDocument = false,
    ) => {
        if (!canAnalyze()) return;
        if (forceDocument || documentWordCount(text) > DOCUMENT_SEGMENT_WORD_LIMIT) {
            await d.detectDocument(source === "IMAGE" ? { pages: [{ page_number: 1, text }] } : { text });
            return;
        }
        const result = await d.detectText(text, source, imageUrl);
        if (result) await Promise.all([history.reload(), refreshUser()]);
    };

    const analyzePages = async (pages: DocumentPage[]) => {
        if (canAnalyze()) await d.detectDocument({ pages });
    };

    const refreshAfterFeedback = async () => {
        if (!isRegularUser) return;
        await Promise.all([history.reload(), refreshUser()]);
    };

    // Tahan render UserShell hanya saat dialihkan ke /admin
    if (isAdminUser) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#f8fafc] text-xs text-slate-500">
                Mengalihkan ke Panel Admin...
            </div>
        );
    }

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
                hoaxCount={null}
                feedbackCount={user?.total_feedbacks ?? 0}
                isGuest={isGuest}
            />

            {/* Grid Formulir Input dan Hasil Deteksi */}
            <div className="grid grid-cols-1 items-start gap-6 pb-6 xl:grid-cols-2">
                <div className="space-y-3 xl:sticky xl:top-24 xl:self-start">
                    <NewsInputForm
                        key={userId ?? "guest"}
                        loading={d.loading}
                        ocrLoading={d.ocrLoading}
                        blocked={!ready}
                        loginRequired={isGuest}
                        onRequireLogin={requireLogin}
                        onAnalyze={analyze}
                        onAnalyzePages={analyzePages}
                        onExtractImage={d.extractTextFromImage}
                        ocrError={d.ocrError}
                    />
                    {d.error && <p role="alert" className="text-sm text-rose-600">{d.error}</p>}
                </div>
                {d.analysisMode === "document" && !d.loading ? (
                    <DocumentResultCard
                        result={d.documentResult}
                        explanations={d.documentExplanations}
                        explanationLoadingFor={d.documentExplanationLoadingFor}
                        explanationError={d.documentExplanationError}
                        onRequestExplanation={d.requestDocumentExplanation}
                    />
                ) : (
                    <VerdictCard
                        result={d.result}
                        loading={d.loading}
                        onRequestExplanation={d.requestExplanation}
                        limeLoading={d.limeLoading}
                        limeError={d.limeError}
                        canAct={isRegularUser}
                        onFeedbackSubmitted={refreshAfterFeedback}
                    />
                )}
            </div>
        </UserShell>
    );
}
