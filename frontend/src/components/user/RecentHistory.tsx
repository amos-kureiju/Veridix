"use client";
import { History, RefreshCw } from "lucide-react";
import Card from "@/components/shared/Card";
import Pill from "@/components/shared/Pill";
import HistoryTable from "@/components/user/HistoryTable";
import type { useHistory } from "@/hooks/useHistory";
import { btnGhost } from "@/lib/utils";

interface Props { guest: boolean; history: ReturnType<typeof useHistory> }

export default function RecentHistory({ guest, history: h }: Props) {
    return (
        <Card
            title="Riwayat terbaru"
            value={guest ? "-" : h.items.length}
            pill={guest ? undefined : <Pill tone="info">tersimpan</Pill>}
            icon={History}
        >
            {guest ? (
                <p className="py-8 text-center text-sm text-slate-600">
                    Masuk untuk menyimpan riwayat deteksi. <a className="text-emerald-700 underline" href="/auth/login">Masuk</a>
                </p>
            ) : (
                <>
                        <div className="mb-3 flex justify-end">
                            <button className={btnGhost} onClick={h.reload}>
                                <RefreshCw size={14} className={h.loading ? "animate-spin" : ""} />Refresh
                            </button>
                        </div>
                        <HistoryTable items={h.items.slice(0, 5)} loading={h.loading} />
                    <a href="/history" className="mt-3 block text-right text-sm font-medium text-emerald-700">Lihat semua</a>
                </>
            )}
        </Card>
    );
}