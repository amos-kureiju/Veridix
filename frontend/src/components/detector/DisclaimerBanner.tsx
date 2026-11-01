export default function DisclaimerBanner() {
    return (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 space-y-1">
            <p className="font-semibold">Catatan penggunaan</p>
            <p className="leading-relaxed">
                Hasil ini menunjukkan <strong>kemiripan pola penulisan</strong> dengan klaim yang pernah dilabeli hoaks
                oleh pemeriksa fakta. Sistem bukan pemverifikasi kebenaran. Untuk kepastian, rujuk{" "}
                <a href="https://cekfakta.com" target="_blank" rel="noopener noreferrer" className="font-semibold text-emerald-700 underline">
                    CekFakta.com
                </a>{" "}
                atau{" "}
                <a href="https://turnbackhoax.id" target="_blank" rel="noopener noreferrer" className="font-semibold text-emerald-700 underline">
                    TurnBackHoax.id
                </a>.
            </p>
        </div>
    );
}