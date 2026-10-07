"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import UserSidebar from "@/components/layout/UserShell";
import FeedbackCard from "@/components/detector/FeedbackCard";
import { FeedbackItem } from "@/types/detector";
import { Search, Send, Lock } from "lucide-react";
import UserShell from "@/components/layout/UserShell";

export default function UserFeedbackPage() {
    const { isGuest } = useAuth();
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedStatus, setSelectedStatus] = useState("ALL");

    const dummyFeedbacks: FeedbackItem[] = useMemo(() => [
        {
            id: "fb-101",
            detection_id: "det-8891",
            news_snippet: "KPU RI mengumumkan jadwal pencoblosan ulang serentak pada distrik tertentu di Papua...",
            model_verdict: "HOAKS",
            user_claim: "FAKTA",
            user_note: "Ini berita valid, sudah disiarkan langsung melalui konferensi pers resmi KPU RI.",
            status: "RETRAINED",
            created_at: "2026-10-06T11:20:00Z",
        },
        {
            id: "fb-102",
            detection_id: "det-8895",
            news_snippet: "Beredar dokumen PDF alokasi bansos tambahan menjelang akhir tahun...",
            model_verdict: "PERLU KONFIRMASI",
            user_claim: "HOAKS",
            user_note: "Kemensos sudah mengeluarkan stempel hoaks resmi.",
            status: "REVIEWED",
            created_at: "2026-10-05T08:45:00Z",
        },
        {
            id: "fb-103",
            detection_id: "det-8902",
            news_snippet: "Anggota DPR Fraksi X mengusulkan penambahan anggaran pengawasan pilkada...",
            model_verdict: "FAKTA",
            user_claim: "HOAKS",
            user_note: "Kutipan pernyataan dipelintir dari wawancara aslinya.",
            status: "PENDING",
            created_at: "2026-10-04T16:10:00Z",
        },
    ], []);

    const filteredFeedbacks = useMemo(() => {
        return dummyFeedbacks.filter((item) => {
            const matchSearch = item.news_snippet.toLowerCase().includes(searchTerm.toLowerCase()) ||
                item.user_note.toLowerCase().includes(searchTerm.toLowerCase());
            const matchStatus = selectedStatus === "ALL" || item.status === selectedStatus;
            return matchSearch && matchStatus;
        });
    }, [dummyFeedbacks, searchTerm, selectedStatus]);

    return (
        <UserShell guest={isGuest}>
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

                {/* Daftar Komponen Modular FeedbackCard */}
                <div className="space-y-4">
                    {filteredFeedbacks.length === 0 ? (
                        <div className="bg-white border border-slate-200/80 rounded-2xl p-12 text-center text-xs text-slate-400">
                            Tidak ada feedback yang cocok dengan pencarian Anda.
                        </div>
                    ) : (
                        filteredFeedbacks.map((fb) => (
                            <FeedbackCard key={fb.id} item={fb} />
                        ))
                    )}
                </div>
        </UserShell>
    );
}