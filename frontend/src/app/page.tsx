import UserSidebar from "@/components/layout/UserSidebar";
import HeaderStats from "@/components/layout/HeaderStats";
import NewsInputForm from "@/components/detector/NewsInputForm";
import ImageUploadForm from "@/components/detector/ImageUploadForm";
import VerdictCard from "@/components/detector/VerdictCard";
import DisclaimerBanner from "@/components/detector/DisclaimerBanner";
import GuestBanner from "@/components/shared/GuestBanner";

export default function UserDashboardPage() {
    return (
        <div className="flex h-screen bg-slate-950 text-white overflow-hidden">

            {/* 1. Sidebar Navigasi User (Hijau Tua) */}
            <UserSidebar />

            {/* 2. Konten Utama Dashboard */}
            <main className="flex-1 overflow-y-auto p-8 lg:p-10">

                {/* Banner untuk Tamu (Jika belum login) */}
                <GuestBanner remainingFreeDetections={3} />

                {/* Header Title & 4 Kartu Statistik Pribadi */}
                <div className="mb-8">
                    <h1 className="text-2xl font-bold tracking-tight text-white mb-2">
                        Deteksi Berita Politik
                    </h1>
                    <p className="text-sm text-slate-400">
                        Masukkan teks berita atau unggah tangkapan layar (*screenshot*) untuk dianalisis oleh IndoBERT & LIME.
                    </p>
                </div>

                <HeaderStats />

                {/* Grid Utama: Form Input (Teks / Gambar) di Kiri, Hasil Analisis di Kanan */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">

                    {/* Kolom Kiri: Pilihan Tab Input (Teks Langsung / Upload Gambar) */}
                    <div className="space-y-6">
                        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
                            <h2 className="text-lg font-semibold text-white mb-4">
                                Masukkan Berita
                            </h2>

                            {/* Komponen Form Teks & Gambar (Bisa di-tab atau dipisah) */}
                            <NewsInputForm />
                            <div className="my-6 border-t border-slate-800" />
                            <ImageUploadForm />
                        </div>
                    </div>

                    {/* Kolom Kanan: Kartu Hasil 4 Lapis (Verdict, Skor, LIME, Disclaimer) */}
                    <div className="space-y-6">
                        <VerdictCard />
                        <DisclaimerBanner />
                    </div>

                </div>
            </main>
        </div>
    );
}