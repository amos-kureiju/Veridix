import { LogOut } from "lucide-react";
import type { User } from "@/types/user";
import { cn } from "@/lib/utils";

interface Props {
    user: User | null;   // null = tamu
    collapsed: boolean;
    onLogout: () => void;
}

export default function SidebarUserCard({ user, collapsed, onLogout }: Props) {
    const avatar = user?.avatar ? (
        <img src={user.avatar} alt="" className="h-9 w-9 shrink-0 rounded-full object-cover" />
    ) : (
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-emerald-500 text-sm font-bold text-white">
            {user ? user.name.slice(0, 2).toUpperCase() : "T"}
        </span>
    );

    return (
        <div className={cn("flex items-center gap-3 rounded-xl bg-white/5 p-2.5 ring-1 ring-white/10", collapsed && "justify-center p-2")}>
            {avatar}
            {!collapsed && (
                <>
                    <div className="min-w-0 flex-1 text-sm leading-tight">
                        <p className="truncate font-medium text-white">{user?.name ?? "Tamu"}</p>
                        <p className="text-xs text-emerald-200/60">{user ? "User terdaftar" : "Belum masuk"}</p>
                    </div>
                    {user ? (
                        <button onClick={onLogout} aria-label="Keluar" className="rounded-lg p-1.5 text-emerald-100/80 hover:bg-white/10">
                            <LogOut size={16} />
                        </button>
                    ) : (
                        <a href="/auth/login" className="text-xs font-medium text-emerald-300 underline">Masuk</a>
                    )}
                </>
            )}
        </div>
    );
}