"use client";

import { createContext, useContext, useMemo, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";

interface UserSidebarState {
    collapsed: boolean;
    setCollapsed: Dispatch<SetStateAction<boolean>>;
}

const UserSidebarContext = createContext<UserSidebarState | null>(null);

export function UserSidebarProvider({ children }: { children: ReactNode }) {
    // Root layout mempertahankan state ini ketika halaman user berganti.
    const [collapsed, setCollapsed] = useState(false);
    const value = useMemo(() => ({ collapsed, setCollapsed }), [collapsed]);

    return (
        <UserSidebarContext.Provider value={value}>
            {children}
        </UserSidebarContext.Provider>
    );
}

export function useUserSidebar() {
    const context = useContext(UserSidebarContext);

    if (!context) {
        throw new Error("useUserSidebar must be used within UserSidebarProvider");
    }

    return context;
}
