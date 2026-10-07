"use client";

import { useState } from "react";

export interface User {
    id?: string;
    name?: string;
    email?: string;
    role?: string;
}

export function useAuth() {
    // Sementara set mode guest true agar dashboard langsung bisa dirender
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