/**
 * Account Store (Zustand)
 * 
 * Global state management for accounts
 */
import { create } from 'zustand';
import type { Account, PoolStatus } from '../types/account';
import api from '../services/api';

interface AccountState {
    accounts: Account[];
    poolStatus: PoolStatus | null;
    availableModels: string[];
    loading: boolean;
    error: string | null;

    // Actions
    fetchAccounts: () => Promise<void>;
    fetchPoolStatus: () => Promise<void>;
    fetchAvailableModels: () => Promise<void>;
    addAccount: (email: string, refreshToken: string) => Promise<void>;
    deleteAccount: (id: string) => Promise<void>;
    refreshToken: (id: string) => Promise<void>;
    reloadPool: () => Promise<void>;
}

export const useAccountStore = create<AccountState>((set, get) => ({
    accounts: [],
    poolStatus: null,
    availableModels: [],
    loading: false,
    error: null,

    fetchAccounts: async () => {
        set({ loading: true, error: null });
        try {
            const accounts = await api.getAccounts();
            set({ accounts, loading: false });
        } catch (e) {
            set({ error: String(e), loading: false });
        }
    },

    fetchPoolStatus: async () => {
        try {
            const poolStatus = await api.getPoolStatus();
            set({ poolStatus });
        } catch (e) {
            console.error('Failed to fetch pool status:', e);
        }
    },

    fetchAvailableModels: async () => {
        try {
            const response = await api.getAvailableModels();
            set({ availableModels: response.models });
        } catch (e) {
            console.error('Failed to fetch available models:', e);
        }
    },

    addAccount: async (email: string, refreshToken: string) => {
        set({ loading: true, error: null });
        try {
            await api.importToken({ email, refresh_token: refreshToken });
            await get().fetchAccounts();
            await get().reloadPool();
        } catch (e) {
            set({ error: String(e), loading: false });
            throw e;
        }
    },

    deleteAccount: async (id: string) => {
        set({ loading: true, error: null });
        try {
            await api.deleteAccount(id);
            await get().fetchAccounts();
            await get().reloadPool();
        } catch (e) {
            set({ error: String(e), loading: false });
            throw e;
        }
    },

    refreshToken: async (id: string) => {
        try {
            await api.refreshToken(id);
            await get().fetchAccounts();
        } catch (e) {
            console.error('Failed to refresh token:', e);
            throw e;
        }
    },

    reloadPool: async () => {
        try {
            await api.reloadPool();
            await get().fetchPoolStatus();
        } catch (e) {
            console.error('Failed to reload pool:', e);
        }
    },
}));
