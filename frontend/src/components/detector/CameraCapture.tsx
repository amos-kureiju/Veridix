"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, X, RotateCcw, Check, AlertCircle, Loader2 } from "lucide-react";

export interface CameraCaptureProps {
    onUsePhoto: (file: File) => void;
    onClose: () => void;
    maxBytes: number;
    maxPixels: number;
}

type CameraStatus = "requesting" | "ready" | "capturing" | "preview" | "error";

function mapCameraErrorMessage(err: unknown): string {
    if (err instanceof DOMException) {
        switch (err.name) {
            case "NotAllowedError":
            case "PermissionDeniedError":
                return "Izin kamera ditolak. Aktifkan izin kamera pada browser Anda lalu coba lagi.";
            case "NotFoundError":
            case "DevicesNotFoundError":
                return "Kamera tidak ditemukan pada perangkat ini.";
            case "NotReadableError":
            case "TrackStartError":
                return "Kamera sedang digunakan oleh aplikasi lain. Tutup aplikasi tersebut lalu coba lagi.";
            case "OverconstrainedError":
                return "Pengaturan kamera tidak didukung oleh perangkat ini.";
            case "SecurityError":
                return "Akses kamera diblokir karena halaman tidak berjalan pada konteks aman (HTTPS atau localhost).";
            default:
                return err.message || "Gagal mengakses kamera.";
        }
    }
    if (err instanceof Error && err.message) {
        return err.message;
    }
    return "Terjadi kendala saat membuka kamera.";
}

export default function CameraCapture({
    onUsePhoto,
    onClose,
    maxBytes,
    maxPixels,
}: CameraCaptureProps) {
    const [status, setStatus] = useState<CameraStatus>("requesting");
    const [frameReady, setFrameReady] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [capturedFile, setCapturedFile] = useState<File | null>(null);
    const [streamVersion, setStreamVersion] = useState(0);

    const videoRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const requestTokenRef = useRef(0);
    const mountedRef = useRef(true);
    const submittedRef = useRef(false);

    const stopStream = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
    }, []);

    const revokePreview = useCallback((url: string | null) => {
        if (url) {
            URL.revokeObjectURL(url);
        }
    }, []);

    const startCamera = useCallback(async () => {
        const token = ++requestTokenRef.current;
        stopStream();
        setFrameReady(false);
        setErrorMessage(null);
        setStatus("requesting");

        if (typeof window !== "undefined" && !window.isSecureContext) {
            setErrorMessage(
                "Akses kamera memerlukan koneksi aman (HTTPS atau localhost). Gunakan HTTPS saat membuka dari HP."
            );
            setStatus("error");
            return;
        }

        if (
            typeof navigator === "undefined" ||
            !navigator.mediaDevices ||
            typeof navigator.mediaDevices.getUserMedia !== "function"
        ) {
            setErrorMessage("Browser ini tidak mendukung pengambilan foto langsung dari kamera.");
            setStatus("error");
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" } },
                audio: false,
            });

            // Jika modal sudah ditutup, unmount, atau ada permintaan baru: hentikan stream terlambat
            if (!mountedRef.current || token !== requestTokenRef.current) {
                stream.getTracks().forEach((track) => track.stop());
                return;
            }

            streamRef.current = stream;
            setStreamVersion((v) => v + 1);
            setStatus("ready");
        } catch (err) {
            if (!mountedRef.current || token !== requestTokenRef.current) {
                return;
            }
            setErrorMessage(mapCameraErrorMessage(err));
            setStatus("error");
        }
    }, [stopStream]);

    // Pasang stream ke elemen <video> setelah render siap
    useEffect(() => {
        if (status === "ready" && videoRef.current && streamRef.current) {
            const video = videoRef.current;
            if (video.srcObject !== streamRef.current) {
                video.srcObject = streamRef.current;
            }
            video.play?.().catch(() => {
                // Abaikan jika autoplay ditahan sementara sebelum metadata siap
            });
        }
    }, [status, streamVersion]);

    // Buka kamera saat komponen dimount, dan bersihkan seluruh resource saat unmount
    useEffect(() => {
        mountedRef.current = true;
        void startCamera();

        return () => {
            mountedRef.current = false;
            requestTokenRef.current += 1;
            stopStream();
        };
    }, [startCamera, stopStream]);

    // Bersihkan object URL pratinjau ketika berubah atau komponen unmount
    useEffect(() => {
        return () => {
            revokePreview(previewUrl);
        };
    }, [previewUrl, revokePreview]);

    const handleClose = useCallback(() => {
        requestTokenRef.current += 1;
        stopStream();
        onClose();
    }, [onClose, stopStream]);

    useEffect(() => {
        const onKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                handleClose();
            }
        };
        window.addEventListener("keydown", onKeyDown);
        return () => window.removeEventListener("keydown", onKeyDown);
    }, [handleClose]);

    const handleVideoFrameReady = () => {
        const video = videoRef.current;
        if (
            video &&
            video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA &&
            video.videoWidth > 0 &&
            video.videoHeight > 0
        ) {
            setFrameReady(true);
        }
    };

    const handleCapturePhoto = () => {
        if (status !== "ready" || !frameReady) return;
        const video = videoRef.current;
        if (
            !video ||
            video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
            video.videoWidth <= 0 ||
            video.videoHeight <= 0
        ) {
            setErrorMessage("Frame kamera belum siap. Tunggu sebentar lalu coba lagi.");
            return;
        }

        const width = video.videoWidth;
        const height = video.videoHeight;

        if (width * height > maxPixels) {
            setErrorMessage(
                `Resolusi kamera (${width}×${height}) melebihi batas maksimal ${maxPixels.toLocaleString("id-ID")} piksel.`
            );
            setStatus("error");
            stopStream();
            return;
        }

        const captureToken = ++requestTokenRef.current;
        setStatus("capturing");
        setErrorMessage(null);

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");

        if (!ctx) {
            setErrorMessage("Gagal menyiapkan kanvas untuk menangkap gambar.");
            setStatus("error");
            stopStream();
            return;
        }

        ctx.drawImage(video, 0, 0, width, height);

        canvas.toBlob(
            (blob) => {
                if (!mountedRef.current || captureToken !== requestTokenRef.current) {
                    return;
                }

                if (!blob || blob.size === 0) {
                    setErrorMessage("Gagal menghasilkan foto dari kamera. Silakan coba lagi.");
                    setStatus("error");
                    stopStream();
                    return;
                }

                if (blob.size > maxBytes) {
                    const maxMiB = (maxBytes / (1024 * 1024)).toFixed(1);
                    setErrorMessage(
                        `Ukuran foto hasil tangkapan melebihi batas maksimal ${maxMiB} MiB.`
                    );
                    setStatus("error");
                    stopStream();
                    return;
                }

                const file = new File([blob], `veridix-kamera-${Date.now()}.jpg`, {
                    type: "image/jpeg",
                });

                stopStream();
                setCapturedFile(file);
                setPreviewUrl(URL.createObjectURL(file));
                setStatus("preview");
            },
            "image/jpeg",
            0.92
        );
    };

    const handleRetake = () => {
        if (status === "capturing") return;
        setCapturedFile(null);
        setPreviewUrl(null);
        submittedRef.current = false;
        void startCamera();
    };

    const handleUsePhoto = () => {
        if (status !== "preview" || !capturedFile || submittedRef.current) return;
        submittedRef.current = true;
        stopStream();
        onUsePhoto(capturedFile);
    };

    const showVideo = status === "requesting" || status === "ready" || status === "capturing";

    return (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="camera-capture-title"
                className="bg-white border border-slate-200 rounded-3xl shadow-2xl max-w-lg w-full overflow-hidden"
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                        <Camera className="w-4 h-4 text-emerald-600" />
                        <h3 id="camera-capture-title" className="text-sm font-bold text-slate-900">
                            Ambil Foto Berita
                        </h3>
                    </div>
                    <button
                        type="button"
                        onClick={handleClose}
                        aria-label="Tutup kamera"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Area Kamera / Pratinjau / Galat */}
                <div className="p-5 space-y-4">
                    <div className="relative aspect-video w-full rounded-2xl overflow-hidden bg-slate-950 flex items-center justify-center">
                        {showVideo && (
                            <video
                                ref={videoRef}
                                autoPlay
                                playsInline
                                muted
                                onLoadedMetadata={handleVideoFrameReady}
                                onLoadedData={handleVideoFrameReady}
                                onCanPlay={handleVideoFrameReady}
                                className={`w-full h-full object-cover ${status === "requesting" ? "opacity-0" : "opacity-100"
                                    }`}
                            />
                        )}

                        {status === "requesting" && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-slate-200 text-xs px-4 text-center">
                                <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
                                <span>Meminta izin dan menyiapkan kamera...</span>
                            </div>
                        )}

                        {status === "capturing" && (
                            <div className="absolute inset-0 bg-slate-950/60 flex flex-col items-center justify-center gap-2 text-white text-xs">
                                <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
                                <span>Memproses foto...</span>
                            </div>
                        )}

                        {status === "preview" && previewUrl && (
                            /* eslint-disable-next-line @next/next/no-img-element */
                            <img
                                src={previewUrl}
                                alt="Pratinjau foto yang diambil"
                                className="w-full h-full object-contain bg-slate-950"
                            />
                        )}

                        {status === "error" && (
                            <div className="p-5 text-center space-y-2 max-w-sm">
                                <AlertCircle className="w-7 h-7 text-rose-400 mx-auto" />
                                <p className="text-xs text-slate-200 leading-relaxed">
                                    {errorMessage || "Kamera tidak dapat digunakan."}
                                </p>
                            </div>
                        )}
                    </div>

                    {status === "ready" && (
                        <p className="text-[11px] text-slate-500 text-center">
                            Arahkan kamera ke satu artikel atau paragraf dengan pencahayaan cukup.
                        </p>
                    )}

                    {/* Tombol Aksi */}
                    <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
                        >
                            Batal
                        </button>

                        {(status === "ready" || status === "capturing") && (
                            <button
                                type="button"
                                disabled={status !== "ready" || !frameReady}
                                onClick={handleCapturePhoto}
                                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 disabled:opacity-50 transition"
                            >
                                <Camera className="w-3.5 h-3.5" />
                                {status === "capturing" ? "Memproses..." : "Ambil Foto"}
                            </button>
                        )}

                        {status === "preview" && (
                            <>
                                <button
                                    type="button"
                                    onClick={handleRetake}
                                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
                                >
                                    <RotateCcw className="w-3.5 h-3.5" />
                                    Ambil Ulang
                                </button>
                                <button
                                    type="button"
                                    onClick={handleUsePhoto}
                                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 transition"
                                >
                                    <Check className="w-3.5 h-3.5" />
                                    Gunakan Foto
                                </button>
                            </>
                        )}

                        {status === "error" && (
                            <button
                                type="button"
                                onClick={() => void startCamera()}
                                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition"
                            >
                                <RotateCcw className="w-3.5 h-3.5" />
                                Coba Lagi
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}