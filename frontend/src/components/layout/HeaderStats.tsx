import { Activity, Gauge, MessageSquare, ShieldAlert } from "lucide-react";
import StatCard from "@/components/shared/StatCard";
import type { UserStats } from "@/types/user";

interface Props { stats: UserStats | null; guest: boolean; guestLeft: number }

export default function HeaderStats({ stats, guest, guestLeft }: Props) {
    const total = stats?.total ?? 0;
    const hoax = stats?.hoax ?? 0;
    const hoaxPct = total ? Math.round((hoax / total) * 100) : 0;
    const dash = guest ? "-" : undefined;

    return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
                label="Total deteksi saya" icon={Activity} href="/history"
                value={dash ?? total}
                pill={guest ? undefined : { tone: "up", text: `+${stats?.today ?? 0}` }}
                footStrong={guest ? "Masuk" : `+${stats?.today ?? 0}`}
                footText={guest ? "untuk melihat statistik" : "hari ini"}
            />
            <StatCard
                label="Hoaks ditemukan" icon={ShieldAlert} href="/history"
                value={dash ?? hoax}
                pill={guest || !total ? undefined : { tone: "down", text: `${hoaxPct}%` }}
                footStrong={guest ? "-" : `${hoax}`}
                footText={guest ? "belum ada data" : `dari ${total} deteksi`}
            />
            <StatCard
                label="Feedback dikirim" icon={MessageSquare} href="/history?tab=feedback"
                value={dash ?? stats?.feedback_sent ?? 0}
                pill={stats?.feedback_processing ? { tone: "info", text: `${stats.feedback_processing} diproses` } : undefined}
                footStrong={guest ? "-" : `${stats?.feedback_sent ?? 0}`}
                footText="feedback terkirim"
            />
            <StatCard
                label="Sisa kuota hari ini" icon={Gauge}
                href={guest ? "/auth/register" : "/profile"}
                value={guest ? guestLeft : "∞"}
                pill={{ tone: "info", text: guest ? "Tamu" : "Aktif" }}
                footStrong={guest ? "Daftar" : "Akun"}
                footText={guest ? "untuk kuota tanpa batas" : "aktif"}
            />
        </div>
    );
}