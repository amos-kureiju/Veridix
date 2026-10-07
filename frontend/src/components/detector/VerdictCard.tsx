export default function VerdictCard() {
    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">Hasil Analisis</h2>
                <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-bold px-3 py-1 rounded-full">
                    HOAKS &bull; 93.4%
                </span>
            </div>
            <div className="space-y-4 text-sm text-slate-300">
                <p className="text-slate-400 italic">
                    Belum ada teks yang dianalisis. Masukkan berita di kolom sebelah kiri dan klik Analisis Sekarang.
                </p>
            </div>
        </div>
    );
}