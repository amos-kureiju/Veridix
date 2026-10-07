import type { NavItem } from "@/lib/navigation";
import { cn } from "@/lib/utils";

interface Props {
    item: NavItem;
    active: boolean;
    collapsed: boolean;
    badgeCount?: number;
}

export default function SidebarNavItem({ item, active, collapsed, badgeCount = 0 }: Props) {
    const { label, href, icon: Icon, badge } = item;

    const cls = cn(
        "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
        collapsed && "justify-center px-0",
        active
            ? "bg-gradient-to-r from-white/15 to-white/5 font-medium text-emerald-300"
            : "text-emerald-50/70 hover:bg-white/5 hover:text-emerald-50",
        !href && "cursor-not-allowed opacity-50 hover:bg-transparent"
    );

    const content = (
        <>
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span className="flex-1 truncate">{label}</span>}
            {!collapsed && badge && badgeCount > 0 && (
                <span className="rounded-full bg-emerald-400/20 px-2 py-0.5 text-xs font-medium text-emerald-200">
                    {badgeCount}
                </span>
            )}
            {!collapsed && !href && <span className="text-[10px] text-emerald-200/60">segera</span>}
            {active && <span className="absolute right-0 top-2 h-6 w-0.5 rounded-full bg-emerald-300" />}
        </>
    );

    return href ? (
        <a href={href} className={cls} title={collapsed ? label : undefined} aria-current={active ? "page" : undefined}>
            {content}
        </a>
    ) : (
        <span className={cls} title="Segera hadir">{content}</span>
    );
}