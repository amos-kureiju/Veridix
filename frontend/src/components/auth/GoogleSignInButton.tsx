"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";

declare global {
    interface Window {
        google?: {
            accounts?: {
                id?: {
                    initialize: (config: {
                        client_id: string;
                        nonce?: string;
                        callback: (response: { credential?: string }) => void;
                        auto_select?: boolean;
                    }) => void;
                    renderButton: (
                        parent: HTMLElement,
                        options: {
                            theme?: "outline" | "filled_blue" | "filled_black";
                            size?: "large" | "medium" | "small";
                            text?: "signin_with" | "signup_with" | "continue_with" | "signin";
                            shape?: "rectangular" | "pill" | "circle" | "square";
                            width?: number;
                            locale?: string;
                        }
                    ) => void;
                };
            };
        };
    }
}

interface GoogleSignInButtonProps {
    purpose: "login" | "link";
    requestChallenge: (purpose: "login" | "link") => Promise<
        | { success: true; challenge_id: string; nonce: string; expires_at: string }
        | { success: false; message: string }
    >;
    onCredential: (challengeId: string, credential: string) => Promise<void> | void;
    disabled?: boolean;
    text?: "continue_with" | "signin_with" | "signup_with";
}

const GIS_SCRIPT_ID = "google-gsi-client-script";
const GIS_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

function loadGisScript(): Promise<void> {
    return new Promise((resolve, reject) => {
        if (typeof window === "undefined") return reject(new Error("Browser tidak tersedia."));
        if (window.google?.accounts?.id) return resolve();

        const existing = document.getElementById(GIS_SCRIPT_ID) as HTMLScriptElement | null;
        if (existing) {
            existing.addEventListener("load", () => resolve(), { once: true });
            existing.addEventListener("error", () => reject(new Error("Gagal memuat layanan Google.")), { once: true });
            return;
        }

        const script = document.createElement("script");
        script.id = GIS_SCRIPT_ID;
        script.src = GIS_SCRIPT_SRC;
        script.async = true;
        script.defer = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error("Gagal memuat skrip Google Identity Services."));
        document.head.appendChild(script);
    });
}

export default function GoogleSignInButton({
    purpose,
    requestChallenge,
    onCredential,
    disabled = false,
    text = "continue_with",
}: GoogleSignInButtonProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const activeChallengeIdRef = useRef<string | null>(null);
    const isMountedRef = useRef<boolean>(true);
    const initSeqRef = useRef<number>(0);

    const [initializing, setInitializing] = useState<boolean>(true);
    const [initError, setInitError] = useState<string | null>(null);

    const clientId = (process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "").trim();

    const setupGoogleButton = useCallback(async () => {
        if (!clientId) {
            setInitError("Login Google belum dikonfigurasi (NEXT_PUBLIC_GOOGLE_CLIENT_ID kosong).");
            setInitializing(false);
            return;
        }

        const seq = ++initSeqRef.current;
        setInitializing(true);
        setInitError(null);

        try {
            // 1. Muat skrip GIS dan minta tantangan nonce secara paralel
            const [, challengeRes] = await Promise.all([
                loadGisScript(),
                requestChallenge(purpose),
            ]);

            if (!isMountedRef.current || initSeqRef.current !== seq) return;

            if (!challengeRes.success) {
                setInitError(challengeRes.message || "Gagal menyiapkan verifikasi Google.");
                setInitializing(false);
                return;
            }

            if (!window.google?.accounts?.id || !containerRef.current) {
                setInitError("Layanan tombol Google tidak siap.");
                setInitializing(false);
                return;
            }

            const currentChallengeId = challengeRes.challenge_id;
            activeChallengeIdRef.current = currentChallengeId;

            // 2. Inisialisasi GIS dengan nonce dari backend
            window.google.accounts.id.initialize({
                client_id: clientId,
                nonce: challengeRes.nonce,
                auto_select: false,
                callback: async (response) => {
                    if (!isMountedRef.current || activeChallengeIdRef.current !== currentChallengeId) return;
                    if (!response?.credential) {
                        setInitError("Kredensial Google tidak diterima.");
                        return;
                    }
                    // Tantangan hanya 1x pakai: reset dan minta tantangan baru jika nanti perlu ulang
                    activeChallengeIdRef.current = null;
                    await onCredential(currentChallengeId, response.credential);
                    // Setelah percobaan selesai (jika komponen masih terpasang & gagal), muat tantangan baru
                    if (isMountedRef.current) {
                        setupGoogleButton();
                    }
                },
            });

            // 3. Render tombol resmi Google
            containerRef.current.innerHTML = "";
            window.google.accounts.id.renderButton(containerRef.current, {
                theme: "outline",
                size: "large",
                text,
                shape: "rectangular",
                width: 340,
                locale: "id",
            });

            setInitializing(false);
        } catch (err: any) {
            if (!isMountedRef.current || initSeqRef.current !== seq) return;
            setInitError(err?.message || "Gagal memuat tombol Google.");
            setInitializing(false);
        }
    }, [clientId, purpose, requestChallenge, onCredential, text]);

    useEffect(() => {
        isMountedRef.current = true;
        setupGoogleButton();
        return () => {
            isMountedRef.current = false;
            ++initSeqRef.current;
            activeChallengeIdRef.current = null;
        };
    }, [setupGoogleButton]);

    return (
        <div className="w-full space-y-2">
            {initializing && (
                <div className="w-full h-10 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-center gap-2 text-xs text-slate-500">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                    <span>Menyiapkan tombol Google...</span>
                </div>
            )}

            {initError && (
                <div className="w-full rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-800 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                        <span className="truncate">{initError}</span>
                    </div>
                    <button
                        type="button"
                        onClick={setupGoogleButton}
                        className="shrink-0 inline-flex items-center gap-1 font-semibold underline hover:text-amber-950 cursor-pointer"
                    >
                        <RefreshCw className="w-3 h-3" />
                        Ulangi
                    </button>
                </div>
            )}

            <div
                ref={containerRef}
                className={`flex justify-center transition-opacity ${initializing || initError ? "hidden" : disabled ? "opacity-50 pointer-events-none" : "opacity-100"
                    }`}
            />
        </div>
    );
}