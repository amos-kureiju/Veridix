export default function GuestBanner({ remainingFreeDetections }: { remainingFreeDetections: number }) {
    return (
        <div className="bg-emerald-950/50 border border-emerald-800/50 rounded-xl p-4 mb-6 flex items-center justify-between">
            <div className="flex items-center space-x-3">
                <span className="bg-emerald-600 text-white text-xs font-bold px-2.5 py-1 rounded-full">
                    MODE TAMU
                </span>
                <p className="text-sm text-emerald-200">
                    Anda memiliki <strong className="text-white">{remainingFreeDetections} kali deteksi gratis</strong> tersisa. Daftar untuk akses penuh.
                </p>
            </div>
            <button className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-4 py-2 rounded-lg transition">
                Daftar Sekarang
            </button>
        </div>
    );
}
