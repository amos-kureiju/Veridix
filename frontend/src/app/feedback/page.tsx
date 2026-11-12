"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import FeedbackCard from "@/components/detector/FeedbackCard";
import { FeedbackItem } from "@/types/detector";
import { Search, Send, Lock, AlertCircle, RefreshCw, Loader2 } from "lucide-react";
import UserShell from "@/components/layout/UserShell";

export default function UserFeedbackPage() {
    const { isGuest, user, token, logout } = useAuth();
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedStatus, setSelectedStatus] = useState("ALL");

    // --- State Riil Pengganti Dummy ---
    const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [fetchError, setFetchError] = useState<string | null>(null);

    const displayName = user?.name || (isGuest ? "Tamu" : "Pengguna");

    // Fungsi fetch feedback khusus milik akun aktif
    const fetchUserFeedbacks = useCallback(async () => {
        if (isGuest) {
            setFeedbacks([]);
            return;
        }

        setIsLoading(true);
        setFetchError(null);

        try {
            const authToken = token || (typeof window !== "undefined" ? localStorage.getItem("token") : null);
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/feedback/my`, {
                headers: {
                    "Content-Type": "application/json",
                    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
                },
            });

            if (!res.ok) {
                throw new Error(`Gagal memuat feedback (Status: ${res.status})`);
            }

            const data = await res.json();
            // Sesuaikan jika payload backend terbungkus misal { data: [...] } atau array langsung
            setFeedbacks(Array.isArray(data) ? data : data.data || []);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Terjadi kesalahan saat memuat data feedback.";
            setFetchError(message);
            setFeedbacks([]);
        } finally {
            setIsLoading(false);
        }
    }, [isGuest, token]);

    useEffect(() => {
        fetchUserFeedbacks();
    }, [fetchUserFeedbacks]);

    // Filter data riil berdasarkan input search dan filter status
    const filteredFeedbacks = useMemo(() => {
        return feedbacks.filter((item) => {
            const matchSearch =
                (item.news_snippet ?? "").toLowerCase().includes(searchTerm.toLowerCase()) ||
                (item.user_note ?? "").toLowerCase().includes(searchTerm.toLowerCase());
            const matchStatus = selectedStatus === "ALL" || item.status === selectedStatus;
            return matchSearch && matchStatus;
        });
    }, [feedbacks, searchTerm, selectedStatus]);

    return (
        <UserShell
            guest={isGuest}
            userName={displayName}
            userRole={user?.role || "USER"}
            onLogout={logout}
        >
            {/* Tombol Buat Deteksi Baru */}
            <div className="flex justify-end pb-2">
                <Link
                    href="/"
                    className="flex items-center gap-2 bg-[#0b2520] hover:bg-[#133730] text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-xs transition"
                >
                    <span>Deteksi Berita Baru</span>
                    <Send className="w-3.5 h-3.5" />
                </Link>
            </div>

            {/* Guest Banner */}
            {isGuest && (
                <div className="bg-amber-50/80 border border-amber-200 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Lock className="w-4 h-4 text-amber-700" />
                        <p className="text-xs text-amber-800">
                            Mode Tamu Aktif: Masuk akun untuk melihat sanggahan riil Anda.
                        </p>
                    </div>
                    <Link href="/auth/login" className="px-3 py-1 bg-amber-600 text-white text-xs font-semibold rounded-xl">
                        Masuk
                    </Link>
                </div>
            )}

            {/* Search & Filter Bar */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-3 shadow-xs flex gap-3">
                <div className="relative flex-1">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Cari cuplikan atau catatan..."
                        className="w-full bg-[#f8fafc] border border-slate-200 pl-8 pr-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none focus:border-emerald-500"
                    />
                </div>
                <select
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    className="bg-[#f8fafc] border border-slate-200 px-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none focus:border-emerald-500"
                >
                    <option value="ALL">Semua Status</option>
                    <option value="PENDING">Menunggu Tinjauan</option>
                    <option value="REVIEWED">Sudah Ditinjau</option>
                    <option value="RETRAINED">Masuk Retraining</option>
                </select>
            </div>

            {/* Daftar Komponen Modular FeedbackCard & Handling State */}
            <div className="space-y-4">
                {/* 1. Kondisi Loading */}
                {isLoading && (
                    <div className="bg-white border border-slate-200/80 rounded-2xl p-12 text-center text-xs text-slate-500 flex flex-col items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 text-emerald-600 animate-spin" />
                        <span>Memuat riwayat feedback Anda...</span>
                    </div>
                )}

                {/* 2. Kondisi Gagal Fetch */}
                {!isLoading && fetchError && (
                    <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center text-xs text-rose-700 flex flex-col items-center justify-center gap-3">
                        <div className="flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 text-rose-600" />
                            <span>{fetchError}</span>
                        </div>
                        <button
                            onClick={fetchUserFeedbacks}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-medium transition"
                        >
                            <RefreshCw className="w-3 h-3" />
                            Coba Lagi
                        </button>
                    </div>
                )}

                {/* 3. Kondisi Sukses tetapi Belum Ada Data Sama Sekali */}
                {!isLoading && !fetchError && feedbacks.length === 0 && (
                    <div className="bg-white border border-slate-200/80 rounded-2xl p-12 text-center text-xs text-slate-400">
                        {isGuest
                            ? "Silakan masuk dengan akun terdaftar untuk melihat riwayat feedback Anda."
                            : "Belum ada riwayat feedback yang Anda kirimkan."}
                    </div>
                )}

                {/* 4. Kondisi Filter/Pencarian Tidak Menemukan Hasil */}
                {!isLoading && !fetchError && feedbacks.length > 0 && filteredFeedbacks.length === 0 && (
                    <div className="bg-white border border-slate-200/80 rounded-2xl p-12 text-center text-xs text-slate-400">
                        Tidak ada feedback yang cocok dengan filter atau kata kunci pencarian.
                    </div>
                )}

                {/* 5. Render Daftar Feedback Riil */}
                {!isLoading && !fetchError && filteredFeedbacks.map((fb) => (
                    <FeedbackCard key={fb.id} item={fb} />
                ))}
            </div>
        </UserShell>
    );
}