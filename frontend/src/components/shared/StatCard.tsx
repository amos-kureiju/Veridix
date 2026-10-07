import { ArrowRight, type LucideIcon } from "lucide-react";
import Pill from "./Pill";
import { IconBox } from "./Card";

interface Props {
    label: string;
    value: string | number;
    pill?: { tone: "up" | "down" | "info"; text: string };
    footStrong: string;
    footText: string;
    href: string;
    icon: LucideIcon;
}

export default function StatCard({ label, value, pill, footStrong, footText, href, icon }: Props) {
    return (
        <div className="space-y-1 rounded-2xl bg-slate-100/70 p-1 ring-1 ring-slate-200/70">
            <div className="flex items-start justify-between rounded-xl bg-white p-4 ring-1 ring-slate-100">
                <div>
                    <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
                    <div className="mt-1.5 flex items-center gap-2">
                        <span className="text-2xl font-semibold text-slate-900">{value}</span>
                        {pill && <Pill tone={pill.tone}>{pill.text}</Pill>}
                    </div>
                </div>
                <IconBox icon={icon} />
            </div>
            <a href={href} className="flex items-center justify-between rounded-xl bg-white px-4 py-2.5 text-xs text-slate-500 ring-1 ring-slate-100 transition hover:text-emerald-700">
                <span><b className="font-semibold text-slate-800">{footStrong}</b> {footText}</span>
                <ArrowRight size={14} />
            </a>
        </div>
    );
}