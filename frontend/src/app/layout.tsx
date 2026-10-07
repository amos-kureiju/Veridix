import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "INSPECT-AI — Deteksi Hoaks Politik Indonesia",
    description: "Sistem deteksi disinformasi politik berbasis IndoBERT, LIME, dan PaddleOCR.",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="id">
            <body className={`${inter.className} bg-slate-950 text-slate-100 antialiased`}>
                {children}
            </body>
        </html>
    );
}