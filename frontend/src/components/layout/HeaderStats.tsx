"use client";

import { ShieldAlert, MessageSquare, Gauge, ArrowUpRight } from "lucide-react";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";

export interface HeaderStatsProps {
    totalDetections?: number;
    hoaxCount?: number | null;   // null = belum ada sumber data agregat
    feedbackCount?: number;
    isGuest?: boolean;
}

export default function HeaderStats({
    totalDetections = 0,
    hoaxCount = null,
    feedbackCount = 0,
    isGuest = true,
}: HeaderStatsProps) {
    const stats = [
        {
            title: "TOTAL DETEKSI SAYA",
            value: totalDetections.toString(),
            badgeText: null as string | null,
            badgePositive: true,
            footerText: isGuest ? "Masuk untuk melihat" : "Sejak akun dibuat",
            icon: AIAnalysisIcon,
            iconColor: "text-emerald-500",
            iconBg: "bg-emerald-50 border-emerald-100",
        },
        {
            title: "HOAKS DITEMUKAN",
            value: hoaxCount === null ? "—" : hoaxCount.toString(),
            badgeText: null as string | null,
            badgePositive: false,
            footerText: hoaxCount === null ? "Belum tersedia" : `${hoaxCount} dari ${totalDetections} deteksi`,
            icon: ShieldAlert,
            iconColor: "text-rose-500",
            iconBg: "bg-rose-50 border-rose-100",
        },
        {
            title: "FEEDBACK DIKIRIM",
            value: feedbackCount.toString(),
            badgeText: null as string | null,
            badgePositive: true,
            footerText: `${feedbackCount} feedback terkirim`,
            icon: MessageSquare,
            iconColor: "text-emerald-500",
            iconBg: "bg-emerald-50 border-emerald-100",
        },
        {
            title: "AKSES DETEKSI",
            value: isGuest ? "Tamu" : "Aktif",
            badgeText: (isGuest ? "Perlu login" : "Terdaftar") as string | null,
            badgePositive: true,
            footerText: isGuest ? "Masuk untuk mendeteksi" : "Akun aktif",
            icon: Gauge,
            iconColor: "text-emerald-600",
            iconBg: "bg-emerald-50 border-emerald-100",
        },
    ];

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {stats.map((item, idx) => {
                const Icon = item.icon;
                return (
                    <div
                        key={idx}
                        className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] flex flex-col justify-between"
                    >
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[11px] font-bold tracking-wider text-slate-400 uppercase">
                                {item.title}
                            </span>
                            <div className={`w-8 h-8 rounded-xl border flex items-center justify-center ${item.iconBg}`}>
                                <Icon
                                    className={`${Icon === AIAnalysisIcon ? "h-6 w-6" : "h-4 w-4"
                                        } ${item.iconColor}`}
                                />
                            </div>
                        </div>

                        <div className="flex items-baseline gap-2.5 my-1">
                            <span className="text-2xl font-bold tracking-tight text-slate-800">
                                {item.value}
                            </span>
                            {item.badgeText && (
                                <span
                                    className={`inline-flex items-center gap-0.5 text-[11px] font-semibold px-2 py-0.5 rounded-full ${item.badgePositive
                                        ? "bg-emerald-50 text-emerald-600 border border-emerald-200/50"
                                        : "bg-rose-50 text-rose-600 border border-rose-200/50"
                                        }`}
                                >
                                    <ArrowUpRight className="w-3 h-3 stroke-[2.5]" />
                                    {item.badgeText}
                                </span>
                            )}
                        </div>

                        <div className="pt-3 mt-3 border-t border-slate-100 text-xs text-slate-500">
                            <span className="truncate block max-w-[200px]">{item.footerText}</span>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}