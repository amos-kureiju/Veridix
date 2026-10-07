import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "VERIDIX — AI Political Disinformation Intelligence",
    description: "Sistem deteksi disinformasi politik berbasis IndoBERT, LIME XAI, dan PaddleOCR.",
    icons: {
        icon: "/logo.png",
    },
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="id">
            <body className="bg-[#f1f5f5] text-slate-800 antialiased min-h-screen">
                {children}
            </body>
        </html>
    );
}