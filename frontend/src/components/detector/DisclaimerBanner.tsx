export default function DisclaimerBanner() {
    return (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 space-y-1">
            <p className="font-semibold text-slate-300">Catatan Sistem:</p>
            <p>
                Hasil berbasis pola bahasa AI (IndoBERT). Bukan pengganti verifikasi faktual absolut. Rujuk ke <a href="https://cekfakta.com" target="_blank" className="text-emerald-400 underline">CekFakta.com</a> atau TurnBackHoax.id untuk validasi mendalam.
            </p>
        </div>
    );
}