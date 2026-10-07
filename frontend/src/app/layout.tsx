import type { Metadata } from "next";
import "./globals.css"; // <-- Ini wajib ada dan mengarah ke ./globals.css

export const metadata: Metadata = {
    title: "INSPECT-AI — Deteksi Hoaks Politik",
    description: "Sistem deteksi disinformasi politik berbasis IndoBERT dan LIME",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="id">
            <body className="bg-[#f1f5f5] text-slate-800 antialiased min-h-screen">
                {children}
            </body>
        </html>
    );
}