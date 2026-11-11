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