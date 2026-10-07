import type { NavKey } from "@/lib/navigation";
import type { User } from "@/types/user";
import Footer from "@/components/shared/Footer";
import UserSidebar from "./UserSidebar";
import UserTopbar from "./UserTopbar";

interface Props {
    user: User | null;
    guest: boolean;
    active: NavKey;
    title: string;
    subtitle: string;
    notif?: number;
    onLogout: () => void;
    children: React.ReactNode;
}

export default function UserShell({ user, guest, active, title, subtitle, notif, onLogout, children }: Props) {
    return (
        <div className="min-h-screen bg-[#e3ebe7] lg:p-4">
            <div className="mx-auto flex min-h-screen max-w-[1500px] overflow-hidden bg-white shadow-xl shadow-emerald-900/10 lg:min-h-[calc(100vh-2rem)] lg:rounded-3xl">
                <UserSidebar user={user} active={active} feedbackBadge={notif} onLogout={onLogout} />
                <div className="flex min-w-0 flex-1 flex-col">
                    <UserTopbar title={title} subtitle={subtitle} guest={guest} notif={notif} />
                    <main className="flex-1 space-y-4 bg-white p-5 lg:p-6">
                        {children}
                        <Footer />
                    </main>
                </div>
            </div>
        </div>
    );
}