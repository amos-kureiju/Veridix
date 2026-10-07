"use client";

import { useState } from "react";

export interface User {
    id?: string;
    name?: string;
    email?: string;
    role?: string;
}

export function useAuth() {
    const [user, setUser] = useState<User | null>(null);
    const [isGuest, setIsGuest] = useState<boolean>(true);

    const logout = () => {
        setUser(null);
        setIsGuest(true);
    };

    return {
        user,
        isGuest,
        logout,
    };
}