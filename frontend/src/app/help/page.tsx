"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import UserShell from "@/components/layout/UserShell";
import {
  HelpCircle,
  Layers,
  UploadCloud,
  MessageSquareQuote,
  ExternalLink,
  ChevronDown,
  ShieldAlert,
  CheckCircle,
  AlertTriangle
} from "lucide-react";

export default function HelpPage() {
  const { user, isGuest, logout } = useAuth();

  // State untuk Akordion FAQ
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const toggleFaq = (idx: number) => {
    setOpenFaq(openFaq === idx ? null : idx);
  };

  const faqs = [
    {
      q: "Mengapa sistem menolak berita non-politik?",
      a: "Model IndoBERT pada VERIDIX secara khusus dilatih dengan dataset korpus disinformasi politik Indonesia (Pemilu, DPR, Pilpres, KPU, dan Kebijakan). Sistem memiliki filter Guardrail yang akan menolak input di luar domain politik untuk mencegah prediksi halusinasi (out-of-distribution)."
    },
    {
      q: "Apa arti status 'PERLU VERIFIKASI' / 'PERLU KONFIRMASI'?",
      a: "Status ini muncul jika sistem tidak mencapai kesepakatan bulat pada voting ensemble 3-seed IndoBERT (terjadi suara terbelah 1/3 atau 2/3 seed). Artinya naskah memiliki sinyal ambigu antara fakta dan disinformasi, sehingga verifikasi silang secara manual sangat direkomendasikan."
    },
    {
      q: "Bagaimana cara kerja ekstraksi teks gambar (OCR)?",
      a: "Sistem menggunakan mesin PaddleOCR untuk membaca teks dari tangkapan layar. Setelah teks diekstrak, Anda dapat memeriksa dan mengeditnya terlebih dahulu (Human-in-the-Loop) sebelum mengirimkannya ke model IndoBERT."
    },
    {
      q: "Apa yang terjadi setelah saya menekan 'Ini Salah?' (Feedback)?",
      a: "Sanggahan Anda disimpan ke basis data dan diteruskan ke Admin Panel. Administrator akan memvalidasi apakah klaim Anda valid untuk dijadikan dataset pelatihan ulang (continuous retraining) model berikutnya."
    }
  ];

  return (
    <UserShell
      guest={isGuest}
      userName={user?.name?.trim() || (isGuest ? "Tamu" : "Pengguna")}
      userRole={user?.role || "USER"}
      onLogout={logout}
    >
      {/* 1. KARTU PANDUAN: MEMAHAMI OUTPUT 4 LAPIS */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-5">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-800">Cara Membaca Hasil Analisis 4 Lapis</h2>
            <p className="text-xs text-slate-400">Arsitektur berlapis untuk menjamin transparansi keputusan AI.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Lapis 1: Diperbarui ke kesepakatan bulat 3/3 seed (Unanimous Rule) */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/60 space-y-2">
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-md bg-[#0b2520] text-white flex items-center justify-center text-[10px]">L1</span>
              Vonis & Konsensus Multi-Seed
            </span>
            <p className="text-slate-600 leading-relaxed">
              Keputusan agregat dari ensemble 3-seed IndoBERT dengan aturan kesepakatan bulat (*unanimous*):
            </p>
            <div className="space-y-1 pt-1">
              {/* PERBAIKAN: Ganti 'mayoritas' dengan '3/3' dan '0/3' */}
              <span className="flex items-center gap-1.5 text-rose-600 font-semibold text-[11px]">
                <ShieldAlert className="w-3.5 h-3.5" /> HOAKS (Kesepakatan bulat 3 dari 3 seed)
              </span>
              <span className="flex items-center gap-1.5 text-amber-600 font-semibold text-[11px]">
                <AlertTriangle className="w-3.5 h-3.5" /> PERLU VERIFIKASI (Suara terbelah 1/3 atau 2/3 seed)
              </span>
              <span className="flex items-center gap-1.5 text-emerald-600 font-semibold text-[11px]">
                <CheckCircle className="w-3.5 h-3.5" /> FAKTA (Kesepakatan bulat 0 dari 3 seed / ketiga model sepakat fakta)
              </span>
            </div>
          </div>

          {/* Lapis 2 */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/60 space-y-2">
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-md bg-[#0b2520] text-white flex items-center justify-center text-[10px]">L2</span>
              Narasi Karakteristik Bahasa
            </span>
            <p className="text-slate-600 leading-relaxed">
              Penjelasan linguistik otomatis yang mengidentifikasi gaya retorika teks, seperti adanya diksi manipulatif, hiperbola, tuduhan sepihak, atau struktur jurnalistik baku.
            </p>
          </div>

          {/* Lapis 3: Diperbarui penjelasan fungsi warna LIME */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/60 space-y-2">
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-md bg-[#0b2520] text-white flex items-center justify-center text-[10px]">L3</span>
              Transparansi XAI (LIME Explainer)
            </span>
            <p className="text-slate-600 leading-relaxed">
              Menghapus sifat "Black Box" model AI dengan kontribusi bobot lokal setiap kata:
            </p>
            <div className="flex gap-2 pt-1">
              <span className="bg-rose-100 text-rose-800 px-2 py-0.5 rounded font-medium text-[11px]">Kata Merah</span>
              <span className="text-slate-500 text-[11px] self-center">menaikkan skor probabilitas hoaks (bobot positif)</span>
            </div>
            <div className="flex gap-2">
              <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-medium text-[11px]">Kata Hijau</span>
              <span className="text-slate-500 text-[11px] self-center">menurunkan skor probabilitas hoaks (bobot negatif)</span>
            </div>
          </div>

          {/* Lapis 4 */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/60 space-y-2">
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-md bg-[#0b2520] text-white flex items-center justify-center text-[10px]">L4</span>
              Disclaimer Mandatori & Mitra Resmi
            </span>
            <p className="text-slate-600 leading-relaxed">
              Pernyataan wajib bahwa sistem mendeteksi kesamaan pola, bukan memvalidasi kebenaran riil di lapangan. Dilengkapi tautan rujukan cek fakta terverifikasi Dewan Pers.
            </p>
          </div>
        </div>
      </div>

      {/* 2. KARTU FITUR KHUSUS: OCR & HUMAN-IN-THE-LOOP */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
              <UploadCloud className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-slate-800">Ekstraksi Gambar (PaddleOCR)</h3>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Mendukung screenshot media sosial (Twitter/X, WhatsApp, Facebook). Pastikan resolusi gambar tajam dan teks tidak terpotong agar hasil OCR akurat.
          </p>
        </div>

        <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-amber-50 text-amber-600 rounded-xl">
              <MessageSquareQuote className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-slate-800">Human-in-the-Loop & Koreksi</h3>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Jika model salah memprediksi, gunakan tombol <strong>"Ini Salah?"</strong>. Masukan Anda akan ditinjau tim admin untuk dijadikan materi retraining model berikutnya.
          </p>
        </div>
      </div>

      {/* 3. KARTU PERTANYAAN UMUM (FAQ) */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
        <h2 className="text-sm font-bold text-slate-800 pb-2 border-b border-slate-100 flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-emerald-600" />
          Pertanyaan yang Sering Diajukan (FAQ)
        </h2>

        <div className="divide-y divide-slate-100 text-xs">
          {faqs.map((faq, idx) => {
            const isOpen = openFaq === idx;
            return (
              <div key={idx} className="py-3">
                <button
                  type="button"
                  onClick={() => toggleFaq(idx)}
                  className="w-full flex items-center justify-between text-left font-semibold text-slate-800 hover:text-emerald-700 transition"
                >
                  <span>{faq.q}</span>
                  <ChevronDown className={`w-4 h-4 text-slate-400 transform transition-transform duration-200 ${isOpen ? "rotate-180 text-emerald-600" : ""}`} />
                </button>
                {isOpen && (
                  <p className="mt-2 text-slate-600 leading-relaxed bg-[#f8fafc] p-3 rounded-xl border border-slate-100">
                    {faq.a}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. TAUTAN MITRA CEK FAKTA RESMI */}
      <div className="bg-emerald-950 text-emerald-100 border border-emerald-900/60 rounded-2xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xs pb-6">
        <div>
          <h3 className="text-xs font-bold text-white">Butuh Verifikasi Faktual Independen?</h3>
          <p className="text-[11px] text-emerald-300/80 mt-0.5">
            Kunjungi mitra cek fakta resmi Indonesia yang telah terakreditasi IFCN (International Fact-Checking Network).
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <a
            href="https://cekfakta.com"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs font-semibold bg-emerald-800/80 hover:bg-emerald-800 text-white px-3.5 py-2 rounded-xl transition"
          >
            <span>CekFakta.com</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          <a
            href="https://turnbackhoax.id"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs font-semibold bg-emerald-800/80 hover:bg-emerald-800 text-white px-3.5 py-2 rounded-xl transition"
          >
            <span>TurnBackHoax.id</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </UserShell>
  );
}