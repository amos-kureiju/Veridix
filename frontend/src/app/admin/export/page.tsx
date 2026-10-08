"use client";

import { useState } from "react";
import { Download, FileSpreadsheet, FileText, Calendar, CheckCircle2 } from "lucide-react";

export default function AdminExportPage() {
    const [dateRange, setDateRange] = useState("30days");
    const [format, setFormat] = useState("CSV");
    const [downloading, setDownloading] = useState(false);

    const handleGenerate = async () => {
        setDownloading(true);
        await new Promise((r) => setTimeout(r, 1200));
        setDownloading(false);
        alert(`Laporan rekapitulasi sistem periode ${dateRange} dalam format ${format} berhasil diunduh.`);
    };

    return (
        <div className="space-y-6 pb-6">
            <div>
                <h2 className="text-xl font-bold tracking-tight text-slate-900">Ekspor Laporan & Dokumen Audit</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                    Unduh data analitik disinformasi politik, log deteksi, dan metrik kinerja IndoBERT untuk kebutuhan pelaporan formal.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Panel Generator Ekspor */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 shadow-2xs space-y-5">
                    <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
                        <Download className="w-4 h-4 text-emerald-600" />
                        <h3 className="text-sm font-bold text-slate-900">Konfigurasi Ekspor Laporan</h3>
                    </div>

                    <div className="space-y-4 text-xs">
                        <div>
                            <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                Rentang Periode Data:
                            </label>
                            <select
                                value={dateRange}
                                onChange={(e) => setDateRange(e.target.value)}
                                className="w-full bg-[#f8fafc] border border-slate-200 p-2.5 rounded-xl text-slate-800 focus:outline-none"
                            >
                                <option value="today">Hari Ini (24 Jam Terakhir)</option>
                                <option value="7days">7 Hari Terakhir</option>
                                <option value="30days">30 Hari Terakhir (Bulan Ini)</option>
                                <option value="all">Seluruh Riwayat Sistem</option>
                            </select>
                        </div>

                        <div>
                            <label className="block font-bold text-slate-500 uppercase tracking-wider text-[10px] mb-1.5">
                                Format File Unduhan:
                            </label>
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    type="button"
                                    onClick={() => setFormat("CSV")}
                                    className={`flex items-center justify-center gap-2 p-3 rounded-2xl border text-xs font-bold transition ${format === "CSV" ? "bg-emerald-50 border-emerald-400 text-emerald-800 ring-2 ring-emerald-200" : "border-slate-200 text-slate-600"
                                        }`}
                                >
                                    <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                                    Spreadsheet (CSV)
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setFormat("PDF")}
                                    className={`flex items-center justify-center gap-2 p-3 rounded-2xl border text-xs font-bold transition ${format === "PDF" ? "bg-emerald-50 border-emerald-400 text-emerald-800 ring-2 ring-emerald-200" : "border-slate-200 text-slate-600"
                                        }`}
                                >
                                    <FileText className="w-4 h-4 text-emerald-600" />
                                    Dokumen Resmi (PDF)
                                </button>
                            </div>
                        </div>

                        <div className="pt-3">
                            <button
                                type="button"
                                onClick={handleGenerate}
                                disabled={downloading}
                                className="w-full flex items-center justify-center gap-2 py-3 bg-[#0b2520] hover:bg-[#133730] text-white font-semibold rounded-xl shadow-xs transition"
                            >
                                <Download className="w-4 h-4" />
                                <span>{downloading ? "Menyiapkan Berkas..." : "Generate & Unduh Laporan"}</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Ringkasan Isi Laporan Audit */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 shadow-2xs space-y-4">
                    <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
                        Komponen Isi Dokumen Laporan
                    </h3>
                    <ul className="space-y-3 text-xs text-slate-600">
                        <li className="flex items-start gap-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                            <span><strong>Metrik Distribusi:</strong> Perbandingan rasio vonis Hoaks vs Fakta pada isu KPU, DPR, Pilpres, dan Kebijakan.</span>
                        </li>
                        <li className="flex items-start gap-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                            <span><strong>Audit XAI LIME:</strong> Rekap kata-kata agitatif dan retorika bias yang paling sering memicu prediksi hoaks.</span>
                        </li>
                        <li className="flex items-start gap-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                            <span><strong>Log Kurasi Active Learning:</strong> Sanggahan pengguna yang telah divalidasi sebagai kandidat retraining model berikutnya.</span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    );
}