export const cn = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");
export const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
export const fmtDate = (iso: string) =>
    new Date(iso).toLocaleString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export const inputCls =
    "w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/15";
export const btnPrimary =
    "inline-flex items-center justify-center gap-2 rounded-xl bg-[#14392f] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1c4d40] disabled:cursor-not-allowed disabled:opacity-50";
export const btnGhost =
    "inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40";