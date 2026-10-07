export default function ImageUploadForm() {
    return (
        <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-6 text-center cursor-pointer transition">
            <div className="space-y-2">
                <div className="mx-auto w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center text-slate-400">
                    📁
                </div>
                <p className="text-sm font-medium text-slate-300">
                    Klik untuk unggah screenshot berita <span className="text-slate-500">(PNG, JPG, WEBP)</span>
                </p>
                <p className="text-xs text-slate-500">Ekstraksi teks otomatis via PaddleOCR</p>
            </div>
        </div>
    );
}