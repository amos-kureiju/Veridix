import { ArrowDownCircle, ArrowUpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const tones = {
    up: "bg-emerald-50 text-emerald-700 ring-emerald-100",
    down: "bg-rose-50 text-rose-600 ring-rose-100",
    info: "bg-sky-50 text-sky-700 ring-sky-100",
};

export default function Pill({ tone = "up", children }: { tone?: keyof typeof tones; children: React.ReactNode }) {
    const Icon = tone === "up" ? ArrowUpCircle : tone === "down" ? ArrowDownCircle : null;
    return (
        <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1", tones[tone])}>
            {Icon && <Icon size={12} />}
            {children}
        </span>
    );
}