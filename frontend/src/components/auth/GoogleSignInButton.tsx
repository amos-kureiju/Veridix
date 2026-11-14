"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Loader2, AlertCircle, X } from "lucide-react";

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
                            logo_alignment?: "left" | "center";
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
    onError?: (message: string) => void;
    disabled?: boolean;
    text?: "continue_with" | "signin_with" | "signup_with";
}

const GIS_SCRIPT_ID = "google-gsi-client-script";
const GIS_SCRIPT_SRC = "https://accounts.google.com/gsi/client";
let gisScriptPromise: Promise<void> | null = null;

function loadGisScript(): Promise<void> {
    if (typeof window === "undefined") return Promise.reject(new Error("Browser tidak tersedia."));
    if (window.google?.accounts?.id) return Promise.resolve();
    if (gisScriptPromise) return gisScriptPromise;

    gisScriptPromise = new Promise<void>((resolve, reject) => {
        const existing = document.getElementById(GIS_SCRIPT_ID) as HTMLScriptElement | null;
        const script = existing ?? document.createElement("script");
        if (!existing) {
            script.id = GIS_SCRIPT_ID;
            script.src = GIS_SCRIPT_SRC;
            script.async = true;
            script.defer = true;
        }
        const cleanup = () => {
            clearTimeout(timeout);
            script.removeEventListener("load", onLoad);
            script.removeEventListener("error", onError);
        };
        const onLoad = () => {
            cleanup();
            if (window.google?.accounts?.id) resolve();
            else reject(new Error("Layanan Google belum tersedia. Silakan coba lagi."));
        };
        const onError = () => {
            cleanup();
            reject(new Error("Tidak dapat memuat layanan Google. Periksa koneksi lalu coba lagi."));
        };
        const timeout = setTimeout(onError, 15000);
        script.addEventListener("load", onLoad, { once: true });
        script.addEventListener("error", onError, { once: true });
        if (!existing) document.head.appendChild(script);
    }).catch((error: unknown) => {
        gisScriptPromise = null;
        document.getElementById(GIS_SCRIPT_ID)?.remove();
        throw error;
    });
    return gisScriptPromise;
}

export default function GoogleSignInButton({
    purpose,
    requestChallenge,
    onCredential,
    onError,
    disabled = false,
    text = "continue_with",
}: GoogleSignInButtonProps) {
    const wrapperRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const activeChallengeRef = useRef<{ id: string; expiresAt: number } | null>(null);
    const isMountedRef = useRef<boolean>(true);
    const initSeqRef = useRef<number>(0);

    // Simpan callback di ref agar tidak memicu ulang fetch challenge saat user mengetik di form
    const requestChallengeRef = useRef(requestChallenge);
    const onCredentialRef = useRef(onCredential);
    const onErrorRef = useRef(onError);
    const disabledRef = useRef(disabled);

    useEffect(() => {
        requestChallengeRef.current = requestChallenge;
        onCredentialRef.current = onCredential;
        onErrorRef.current = onError;
        disabledRef.current = disabled;
    }, [requestChallenge, onCredential, onError, disabled]);

    const [initializing, setInitializing] = useState<boolean>(true);
    const [ready, setReady] = useState(false);
    const [notification, setNotification] = useState<string | null>(null);

    const clientId = (process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "").trim();

    const notifyError = useCallback((message: string) => {
        if (onErrorRef.current) onErrorRef.current(message);
        else setNotification(message);
    }, []);

    const setupGoogleButton = useCallback(async (notifyFailure = false) => {
        const seq = ++initSeqRef.current;
        activeChallengeRef.current = null;
        setReady(false);
        setInitializing(true);
        if (notifyFailure) setNotification(null);

        try {
            if (!clientId) {
                throw new Error("Login Google belum tersedia. Silakan coba lagi nanti.");
            }
            // 1. Muat skrip GIS dan minta tantangan nonce secara paralel
            const [, challengeRes] = await Promise.all([
                loadGisScript(),
                requestChallengeRef.current(purpose),
            ]);

            if (!isMountedRef.current || initSeqRef.current !== seq) return;

            if (!challengeRes.success) {
                throw new Error(challengeRes.message || "Tidak dapat menyiapkan login Google. Silakan coba lagi.");
            }

            if (!window.google?.accounts?.id || !containerRef.current) {
                throw new Error("Layanan Google belum tersedia. Silakan coba lagi.");
            }
            const expiresAt = Date.parse(challengeRes.expires_at);
            if (!challengeRes.challenge_id || !challengeRes.nonce || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
                throw new Error("Verifikasi Google tidak tersedia. Silakan coba lagi.");
            }

            const currentChallengeId = challengeRes.challenge_id;
            activeChallengeRef.current = { id: currentChallengeId, expiresAt };

            // 2. Inisialisasi GIS dengan nonce dari backend
            window.google.accounts.id.initialize({
                client_id: clientId,
                nonce: challengeRes.nonce,
                auto_select: false,
                callback: async (response) => {
                    const challenge = activeChallengeRef.current;
                    if (!isMountedRef.current || initSeqRef.current !== seq || disabledRef.current || challenge?.id !== currentChallengeId) return;
                    if (!response?.credential || challenge.expiresAt <= Date.now()) {
                        notifyError(challenge.expiresAt <= Date.now()
                            ? "Verifikasi Google kedaluwarsa. Silakan coba lagi."
                            : "Verifikasi Google tidak diterima. Silakan coba lagi.");
                        void setupGoogleButton();
                        return;
                    }

                    // Jangan menerima callback kedua saat kredensial pertama sedang diproses.
                    activeChallengeRef.current = null;
                    setReady(false);
                    setInitializing(true);
                    try {
                        await onCredentialRef.current(currentChallengeId, response.credential);
                    } catch (error: unknown) {
                        if (isMountedRef.current && initSeqRef.current === seq) {
                            notifyError(error instanceof Error ? error.message : "Login Google gagal. Silakan coba lagi.");
                        }
                    } finally {
                        if (isMountedRef.current && initSeqRef.current === seq) {
                            void setupGoogleButton();
                        }
                    }
                },
            });

            // 3. Render tombol resmi Google berbentuk pill & lebar mengikuti form (240–400px)
            const measuredWidth = wrapperRef.current?.getBoundingClientRect().width || 380;
            const buttonWidth = Math.round(Math.min(Math.max(measuredWidth, 240), 400));

            containerRef.current.innerHTML = "";
            window.google.accounts.id.renderButton(containerRef.current, {
                theme: "outline",
                size: "large",
                text,
                shape: "pill",
                logo_alignment: "center",
                width: buttonWidth,
                locale: "id",
            });

            setReady(true);
        } catch (err: unknown) {
            if (!isMountedRef.current || initSeqRef.current !== seq) return;
            activeChallengeRef.current = null;
            if (notifyFailure) {
                notifyError(err instanceof Error ? err.message : "Login Google belum tersedia. Silakan coba lagi.");
            }
        } finally {
            if (isMountedRef.current && initSeqRef.current === seq) setInitializing(false);
        }
    }, [clientId, purpose, text, notifyError]);

    useEffect(() => {
        isMountedRef.current = true;
        void setupGoogleButton();
        return () => {
            isMountedRef.current = false;
            ++initSeqRef.current;
            activeChallengeRef.current = null;
        };
    }, [setupGoogleButton]);

    return (
        <div ref={wrapperRef} className="w-full">
            <div className="relative min-h-[42px] w-full flex items-center justify-center">
                {!ready && (
                    <button
                        type="button"
                        disabled={disabled || initializing}
                        aria-busy={initializing}
                        onClick={() => { void setupGoogleButton(true); }}
                        className="relative w-full max-w-[400px] h-10 rounded-full border border-[#747775] bg-white flex items-center justify-center gap-3 px-3 text-sm font-medium text-[#1f1f1f] hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:cursor-wait disabled:hover:bg-white transition-colors"
                        style={{ fontFamily: "Arial, sans-serif" }}
                    >
                        <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" className="shrink-0">
                            <path fill="#4285F4" d="M22.56 12.25c0-.73-.06-1.42-.19-2.09H12v3.96h5.92c-.26 1.28-1.04 2.36-2.21 3.09v2.56h3.57c2.08-1.92 3.28-4.74 3.28-7.52Z" />
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.56c-.98.66-2.24 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.64A11 11 0 0 0 12 23Z" />
                            <path fill="#FBBC05" d="M5.84 14.31A6.6 6.6 0 0 1 5.5 12c0-.8.14-1.58.34-2.31V7.05H2.18A11 11 0 0 0 1 12c0 1.78.43 3.47 1.18 4.95l3.66-2.64Z" />
                            <path fill="#EA4335" d="M12 5.16c1.62 0 3.07.56 4.21 1.66l3.16-3.16A10.57 10.57 0 0 0 12 1a11 11 0 0 0-9.82 6.05l3.66 2.64C6.71 7.09 9.14 5.16 12 5.16Z" />
                        </svg>
                        <span>{text === "signin_with" ? "Masuk dengan Google" : text === "signup_with" ? "Daftar dengan Google" : "Lanjutkan dengan Google"}</span>
                        {initializing && <Loader2 aria-hidden="true" className="absolute right-3 h-3.5 w-3.5 animate-spin text-slate-400" />}
                    </button>
                )}

                <div
                    ref={containerRef}
                    aria-disabled={disabled || initializing}
                    inert={!ready || disabled || initializing}
                    style={{ display: ready ? undefined : "none" }}
                    className={`w-full flex justify-center transition-opacity duration-200 ${disabled ? "opacity-50 pointer-events-none select-none cursor-not-allowed" : "opacity-100"}`}
                />
            </div>
            {notification && (
                <div role="alert" className="fixed bottom-5 right-5 z-50 flex max-w-sm items-start gap-3 rounded-2xl border border-amber-200 bg-white p-4 text-sm text-slate-700 shadow-lg">
                    <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    <span>{notification}</span>
                    <button type="button" aria-label="Tutup notifikasi" onClick={() => setNotification(null)} className="shrink-0 rounded p-1 hover:bg-slate-100">
                        <X aria-hidden="true" className="h-4 w-4" />
                    </button>
                </div>
            )}
        </div>
    );
}
