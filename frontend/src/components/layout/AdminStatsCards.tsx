export default function HeaderStats() {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <p className="text-xs text-slate-400">Total Deteksi Saya</p>
                <h3 className="text-2xl font-bold text-white mt-1">47</h3>
                <span className="text-xs text-emerald-400 font-medium">+3 hari ini</span>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <p className="text-xs text-slate-400">Hoaks Ditemukan</p>
                <h3 className="text-2xl font-bold text-white mt-1">31</h3>
                <span className="text-xs text-rose-400 font-medium">66% dari total</span>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <p className="text-xs text-slate-400">Feedback Dikirim</p>
                <h3 className="text-2xl font-bold text-white mt-1">5</h3>
                <span className="text-xs text-blue-400 font-medium">2 diproses</span>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <p className="text-xs text-slate-400">Sisa Kuota Hari Ini</p>
                <h3 className="text-2xl font-bold text-white mt-1">∞</h3>
                <span className="text-xs text-purple-400 font-medium">Akun Aktif</span>
            </div>
        </div>
    );
}