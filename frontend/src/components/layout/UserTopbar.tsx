import { Bell, Info, Plus } from "lucide-react";
import { btnGhost, btnPrimary } from "@/lib/utils";

interface Props { title: string; subtitle: string; guest: boolean; notif?: number }

export default function UserTopbar({ title, subtitle, guest, notif = 0 }: Props) {
    return (
        <header className="no-print flex items-center justify-between gap-4 border-b border-slate-200/80 bg-white px-6 py-4">
            <div>
                <h1 className="text-base font-semibold text-slate-900">{title}</h1>
                <p className="text-xs text-slate-500">{subtitle}</p>
            </div>
            <div className="flex items-center gap-2">
                <a href="https://turnbackhoax.id" target="_blank" rel="noreferrer" aria-label="Info" className={btnGhost + " !rounded-full !p-2"}>
                    <Info size={16} />
                </a>
                <a href="/history?tab=feedback" aria-label="Notifikasi feedback" className={btnGhost + " relative !rounded-full !p-2"}>
                    <Bell size={16} />
                    {notif > 0 && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-white" />}
                </a>
                <span className="mx-1 h-6 w-px bg-slate-200" />
                {guest ? (
                    <a href="/auth/login" className={btnPrimary}>Masuk</a>
                ) : (
                    <a href="/" className={btnPrimary}><Plus size={16} />Deteksi baru</a>
                )}
            </div>
        </header>
    );
}