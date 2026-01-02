/**
 * Auth Store
 * 
 * Manages authentication state using Zustand
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';

interface User {
    id: string;
    username: string;
    api_key: string;
    created_at: string;
}

interface AuthState {
    token: string | null;
    user: User | null;
    isAuthenticated: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
    refreshUser: () => Promise<void>;
    regenerateApiKey: () => Promise<string>;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            token: null,
            user: null,
            isAuthenticated: false,

            login: async (username: string, password: string) => {
                const response = await api.login(username, password);
                set({
                    token: response.access_token,
                    user: response.user,
                    isAuthenticated: true,
                });
            },

            logout: () => {
                set({
                    token: null,
                    user: null,
                    isAuthenticated: false,
                });
            },

            refreshUser: async () => {
                try {
                    const user = await api.getMe();
                    set({ user });
                } catch {
                    // Token invalid, logout
                    get().logout();
                }
            },

            regenerateApiKey: async () => {
                const response = await api.regenerateApiKey();
                const currentUser = get().user;
                if (currentUser) {
                    set({
                        user: { ...currentUser, api_key: response.api_key }
                    });
                }
                return response.api_key;
            },
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                token: state.token,
                user: state.user,
                isAuthenticated: state.isAuthenticated
            }),
        }
    )
);
