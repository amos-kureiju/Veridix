export default function AIAnalysisIcon({ className = "" }: { className?: string }) {
    return (
        <svg
            viewBox="0 0 64 64"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.4}
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
            aria-hidden="true"
            focusable="false"
        >
            {/* Kontur dan lipatan otak */}
            <path d="M34 14c0-5 4-8 8-8 4 0 7 2 8 6 5 0 9 4 9 9 0 2-1 4-2 5 4 3 5 8 3 12-1 2-2 4-4 5 2 6-2 12-8 12-1 4-4 6-7 6-4 0-7-3-7-7V14Z" />
            <path d="M43 16c-4 0-5 6-2 9M52 26c-5 0-9 4-9 9M34 34c6-3 12 1 12 7M54 43c-5 0-6 6-3 9M35 51c4 0 6 3 6 6" />

            {/* Chip dan jalur sirkuit */}
            <rect x="17" y="27" width="13" height="13" rx="2.5" />
            <rect x="21" y="31" width="5" height="5" rx="1" />
            <path d="M34 20h-6V10h-6M17 30h-5v-8H6M17 36H8M20 27v-6l-6-6M25 27v-5h9M21 40v6h-9M27 40v10l-5 5M30 31h4M30 36h4M34 46v9" />

            <circle cx="22" cy="10" r="2" />
            <circle cx="6" cy="22" r="2" />
            <circle cx="8" cy="36" r="2" />
            <circle cx="14" cy="15" r="2" />
            <circle cx="12" cy="46" r="2" />
            <circle cx="22" cy="55" r="2" />
        </svg>
    );
}

export function AIAnalysisLoading({ description }: { description: string }) {
    return (
        <div
            role="status"
            className="relative isolate overflow-hidden rounded-xl border border-emerald-800 bg-emerald-950 px-3.5 py-3 text-left shadow-sm sm:px-4"
        >
            <style>{`
                @media (prefers-reduced-motion: no-preference) {
                    .veridix-brain-sweep { animation: veridix-brain-sweep 2.2s ease-in-out infinite; }
                    .veridix-brain-glow { animation: veridix-brain-glow 2.2s ease-in-out infinite; }
                }
                @keyframes veridix-brain-sweep {
                    0%, 10% { opacity: 0; transform: translateY(-115%); }
                    27% { opacity: .8; }
                    75% { opacity: .65; }
                    90%, 100% { opacity: 0; transform: translateY(345%); }
                }
                @keyframes veridix-brain-glow {
                    0%, 100% { opacity: .3; }
                    50% { opacity: .75; }
                }
            `}</style>

            <div
                aria-hidden="true"
                className="veridix-brain-glow pointer-events-none absolute -left-6 -top-10 -z-10 h-36 w-40 rounded-full bg-emerald-500/20 opacity-40 blur-3xl"
            />
            <div className="flex items-center gap-3 sm:gap-4">
                <span
                    aria-hidden="true"
                    className="relative grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-xl border border-emerald-400/35 bg-gradient-to-br from-emerald-800 to-emerald-950 text-emerald-100 shadow-md shadow-black/15 sm:h-14 sm:w-14"
                >
                    <AIAnalysisIcon className="h-9 w-9 sm:h-10 sm:w-10" />
                    <span className="veridix-brain-sweep pointer-events-none absolute inset-x-0 top-0 h-1/3 bg-gradient-to-b from-transparent via-emerald-300/45 to-transparent opacity-0" />
                </span>
                <div className="min-w-0">
                    <p className="text-sm font-semibold leading-snug text-white">AI sedang menyusun penjelasan</p>
                    <p className="mt-1 text-xs leading-relaxed text-emerald-100/85">{description}</p>
                </div>
            </div>
        </div>
    );
}
