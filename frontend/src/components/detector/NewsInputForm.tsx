export default function NewsInputForm() {
    return (
        <div>
            <textarea
                rows={5}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                placeholder="Tempelkan teks berita di sini, minimal 30 karakter..."
            />
            <div className="flex items-center justify-between mt-3">
                <span className="text-xs text-slate-500">Min 30 karakter &bull; Domain politik saja</span>
                <button className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm px-6 py-2.5 rounded-xl transition shadow-lg shadow-emerald-900/20">
                    Analisis Sekarang
                </button>
            </div>
        </div>
    );
}