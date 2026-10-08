interface AuthHeadingProps {
    title: string;
    subtitle?: string;
}

/**
 * Judul seragam untuk semua halaman /auth/* (login, register, lupa sandi, reset sandi):
 * judul besar di tengah + garis aksen hijau + subjudul.
 */
export default function AuthHeading({ title, subtitle }: AuthHeadingProps) {
    return (
        <div className="text-center">
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">{title}</h1>
            <span className="mx-auto mt-3 block h-1 w-10 rounded-full bg-emerald-500" />
            {subtitle && <p className="mt-4 text-sm text-slate-500">{subtitle}</p>}
        </div>
    );
}