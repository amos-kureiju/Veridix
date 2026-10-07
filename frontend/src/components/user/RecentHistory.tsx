"use client";
import { useState } from "react";
import { History, RefreshCw, Search } from "lucide-react";
import Card from "@/components/shared/Card";
import Pill from "@/components/shared/Pill";
import ConfirmDialog from "@/components/shared/ConfirmDialog";
import HistoryTable from "@/components/user/HistoryTable";
import type { useHistory } from "@/hooks/useHistory";
import { btnGhost, inputCls } from "@/lib/utils";

interface Props { guest: boolean; history: ReturnType<typeof useHistory> }

export default function RecentHistory({ guest, history: h }: Props) {
    const [del, setDel] = useState<string | null>(null);
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
                    <div className="mb-3 flex gap-3">
                        <div className="relative flex-1">
                            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input className={inputCls + " pl-9"} placeholder="Cari berita…" value={h.q} onChange={(e) => h.setQ(e.target.value)} />
                        </div>
                        <button className={btnGhost} onClick={h.reload}>
                            <RefreshCw size={14} className={h.loading ? "animate-spin" : ""} />Refresh
                        </button>
                    </div>
                    <HistoryTable items={h.items.slice(0, 5)} loading={h.loading} onDelete={setDel} />
                    <a href="/history" className="mt-3 block text-right text-sm font-medium text-emerald-700">Lihat semua</a>
                </>
            )}
            <ConfirmDialog
                open={!!del}
                title="Hapus riwayat ini?"
                desc="Hasil deteksi ini akan dihapus dari akun Anda."
                confirmLabel="Hapus"
                onCancel={() => setDel(null)}
                onConfirm={() => { h.remove(del!); setDel(null); }}
            />
        </Card>
    );
}