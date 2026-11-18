import { AlertCircle, FileText, LoaderCircle } from "lucide-react";
import type { DocumentAnalysisResult, DocumentSegment, DocumentStatus } from "@/types/document-analysis";

const documentStatus: Record<DocumentStatus, { label: string; color: string }> = {
    lengkap: { label: "Cakupan lengkap", color: "bg-emerald-50 text-emerald-800" },
    parsial: { label: "Cakupan sebagian", color: "bg-amber-50 text-amber-800" },
    gagal: { label: "Analisis gagal", color: "bg-rose-50 text-rose-800" },
    ditolak: { label: "Naskah ditolak", color: "bg-slate-100 text-slate-800" },
};

function segmentBadge(segment: DocumentSegment) {
    if (segment.status === "dinilai") {
        return segment.label === "BERPOLA HOAKS"
            ? { label: "Berpola hoaks", color: "bg-rose-50 text-rose-800" }
            : { label: "Tidak berpola hoaks", color: "bg-emerald-50 text-emerald-800" };
    }
    if (segment.status === "ambigu") return { label: "Perlu verifikasi", color: "bg-amber-50 text-amber-800" };
    if (segment.status === "ditolak") return { label: "Ditolak", color: "bg-slate-100 text-slate-800" };
    if (segment.status === "gagal") return { label: "Gagal dinilai", color: "bg-rose-50 text-rose-800" };
    return { label: "Belum dinilai", color: "bg-slate-100 text-slate-800" };
}

interface Props {
    result: DocumentAnalysisResult | null;
    loading: boolean;
}

export default function DocumentResultCard({ result, loading }: Props) {
    if (!loading && !result) return null;
    const status = result ? documentStatus[result.status] : null;

    return (
        <section aria-labelledby="document-result-title" aria-busy={loading}
            className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <header className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                    <span className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700" aria-hidden="true">
                        <FileText size={20} />
                    </span>
                    <h2 id="document-result-title" className="text-lg font-semibold text-slate-900">Analisis naskah</h2>
                </div>
                {status && <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status.color}`}>{status.label}</span>}
            </header>

            {loading && (
                <div role="status" className="mt-4 flex items-center gap-2 text-sm text-slate-700">
                    <LoaderCircle size={17} className="motion-safe:animate-spin" aria-hidden="true" />
                    Model sedang memeriksa segmen naskah.
                </div>
            )}

            {result && (
                <div className="mt-4 space-y-4">
                    <p role="status" className="text-sm text-slate-700">
                        <strong className="text-slate-900">{result.analyzed_words} dari {result.total_words} kata</strong> pada teks yang dikirim telah dinilai.
                    </p>
                    {result.reason && <p className="text-sm text-slate-700">{result.reason}</p>}
                    {result.missing_pages.length > 0 && (
                        <p className="flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
                            <AlertCircle size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
                            <span>Halaman {result.missing_pages.join(", ")} belum memiliki teks yang dikonfirmasi. Jumlah katanya belum diketahui.</span>
                        </p>
                    )}
                    {result.segments.length > 0 && (
                        <ol className="space-y-2">
                            {result.segments.map((segment, index) => {
                                const badge = segmentBadge(segment);
                                return (
                                    <li key={segment.start_char}>
                                        <details className="rounded-xl border border-slate-200 bg-slate-50">
                                            <summary className="cursor-pointer rounded-xl p-3 text-sm text-slate-800 focus-visible:outline-2 focus-visible:outline-emerald-600">
                                                <span className="ml-1 inline-flex flex-wrap items-center gap-x-2 gap-y-1">
                                                    <span className="font-semibold">Segmen {index + 1}</span>
                                                    <span className="text-slate-600">Kata {segment.start_word}–{segment.end_word}</span>
                                                    {segment.page_numbers.length > 0 && <span className="text-slate-600">Halaman {segment.page_numbers.join(", ")}</span>}
                                                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge.color}`}>{badge.label}</span>
                                                </span>
                                            </summary>
                                            <div className="space-y-2 border-t border-slate-200 p-3 text-sm text-slate-700">
                                                <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{segment.text}</p>
                                                {segment.votes_hoax && <p className="text-xs text-slate-600">Suara hoaks {segment.votes_hoax}</p>}
                                                {segment.status === "ambigu" && <p>Model antar-seed menghasilkan keputusan yang berbeda.</p>}
                                                {segment.reason && <p>{segment.reason}</p>}
                                            </div>
                                        </details>
                                    </li>
                                );
                            })}
                        </ol>
                    )}
                    <p className="border-t border-slate-200 pt-3 text-xs leading-relaxed text-slate-600">
                        Hasil pola bahasa berlaku per segmen. Verifikasi fakta tetap membutuhkan sumber independen.
                        Hasil mode uji coba ini tersedia selama halaman terbuka.
                    </p>
                </div>
            )}
        </section>
    );
}
