import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export const IconBox = ({ icon: Icon }: { icon: LucideIcon }) => (
    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white text-emerald-600 shadow-sm ring-1 ring-slate-200">
        <Icon size={18} />
    </span>
);

interface Props {
    title?: string;
    value?: React.ReactNode;
    pill?: React.ReactNode;
    icon?: LucideIcon;
    action?: React.ReactNode;
    className?: string;
    bodyClass?: string;
    children: React.ReactNode;
}

export default function Card({ title, value, pill, icon, action, className, bodyClass, children }: Props) {
    const hasHead = title || value || pill || icon || action;
    return (
        <section className={cn("space-y-1 rounded-2xl bg-slate-100/70 p-1 ring-1 ring-slate-200/70", className)}>
            {hasHead && (
                <header className="flex items-start justify-between gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-100">
                    <div className="min-w-0">
                        {title && <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{title}</p>}
                        {(value || pill) && (
                            <div className="mt-1 flex items-center gap-2">
                                <span className="text-xl font-semibold text-slate-900">{value}</span>
                                {pill}
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        {action}
                        {icon && <IconBox icon={icon} />}
                    </div>
                </header>
            )}
            <div className={cn("rounded-xl bg-white p-4 ring-1 ring-slate-100", bodyClass)}>{children}</div>
        </section>
    );
}