import Link from "next/link";

export default function GuestBanner() {
    return (
        <div className="bg-emerald-950/50 border border-emerald-800/50 rounded-xl p-4 mb-6 flex items-center justify-between">
            <div className="flex items-center space-x-3">
                <span className="bg-emerald-600 text-white text-xs font-bold px-2.5 py-1 rounded-full">
                    MODE TAMU
                </span>
                <p className="text-sm text-emerald-200">
                    Anda dapat menjelajahi tampilan web. Masuk untuk menjalankan deteksi dan menyimpan riwayat pribadi.
                </p>
            </div>
            <Link href="/auth/login" className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-4 py-2 rounded-lg transition">
                Masuk Akun
            </Link>
        </div>
    );
}
