/**
 * API Client Service
 * 
 * Replaces Tauri invoke() calls with fetch() to Python backend
 */

// Use VITE_API_BASE env var if set, otherwise default to localhost in dev, or relative path in prod
const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? 'http://localhost:8000' : '');

// Helper to get auth token from localStorage
function getAuthToken(): string | null {
    try {
        const stored = localStorage.getItem('auth-storage');
        if (stored) {
            const parsed = JSON.parse(stored);
            return parsed.state?.token || null;
        }
    } catch {
        return null;
    }
    return null;
}

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
        const token = getAuthToken();
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...(options?.headers as Record<string, string> || {}),
        };

        // Add auth token if available
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || error.error || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Auth
    async login(username: string, password: string) {
        return this.request<{
            access_token: string;
            token_type: string;
            user: {
                id: string;
                username: string;
                api_key: string;
                created_at: string;
            };
        }>('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
    }

    async changePassword(currentPassword: string, newPassword: string) {
        return this.request<{ message: string }>('/api/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            }),
        });
    }

    async getMe() {
        return this.request<{
            id: string;
            username: string;
            api_key: string;
            created_at: string;
        }>('/api/auth/me');
    }

    async regenerateApiKey() {
        return this.request<{ api_key: string; message: string }>('/api/auth/regenerate-key', {
            method: 'POST',
        });
    }

    // Health check
    async health() {
        return this.request<{ status: string; version: string; accounts_loaded: number }>('/health');
    }

    // Account Management
    async getAccounts() {
        return this.request<import('../types/account').Account[]>('/api/accounts/');
    }

    async getAccount(id: string) {
        return this.request<import('../types/account').Account>(`/api/accounts/${id}`);
    }

    async deleteAccount(id: string) {
        return this.request<{ status: string }>(`/api/accounts/${id}`, { method: 'DELETE' });
    }

    // OAuth
    async startOAuth() {
        return this.request<{ auth_url: string; state: string }>('/api/oauth/start');
    }

    async startOAuthRelay() {
        // Relay mode: uses localhost callback for production environments
        // Requires running oauth_relay.py locally
        return this.request<{ auth_url: string; state: string }>('/api/oauth/start-relay');
    }

    async refreshToken(accountId: string) {
        return this.request<{ status: string }>(`/api/oauth/refresh?account_id=${accountId}`, { method: 'POST' });
    }

    // Token Import
    async importToken(data: { email: string; refresh_token: string }) {
        return this.request<{ status: string; account_id: string }>('/api/import/import-token', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async importBulk(tokens: { email: string; refresh_token: string }[]) {
        return this.request<{ status: string; imported: number }>('/api/import/import-bulk', {
            method: 'POST',
            body: JSON.stringify({ tokens }),
        });
    }

    async importJsonFile(file: File) {
        const token = getAuthToken();
        const headers: Record<string, string> = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseUrl}/api/import/import-json-file`, {
            method: 'POST',
            headers,
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Quota & Pool
    async getPoolStatus() {
        return this.request<import('../types/account').PoolStatus>('/api/quota/pool');
    }

    async reloadPool() {
        return this.request<{ status: string; accounts_loaded: number }>('/api/quota/pool/reload', { method: 'POST' });
    }

    async getAvailableModels() {
        return this.request<import('../types/account').AvailableModelsResponse>('/api/quota/models');
    }

    async getModelQuota(modelName: string) {
        return this.request<{ model: string; remaining_fraction?: number }>(`/api/quota/quota/${modelName}`);
    }

    async getQuotaMatrix() {
        return this.request<{
            email: string;
            project_id: string;
            quotas: Record<string, {
                model: string;
                remaining_fraction?: number;
                reset_time?: string;
                available: boolean;
            }>;
            error?: string;
        }[]>('/api/quota/matrix');
    }

    async getBestAccount() {
        return this.request<{
            best_account: {
                email: string;
                project_id: string;
                average_quota: number;
            } | null;
            overall_average: number;
            all_accounts: {
                email: string;
                project_id: string;
                average_quota: number;
            } | null;
            message?: string;
        }>('/api/quota/best-account');
    }

    // Model Mappings
    async getMappings() {
        return this.request<{ id: number; source_model: string; target_model: string; description: string }[]>('/api/mappings/');
    }

    async createMapping(source_model: string, target_model: string, description?: string) {
        return this.request<{ id: number; source_model: string; target_model: string; description: string }>('/api/mappings/', {
            method: 'POST',
            body: JSON.stringify({ source_model, target_model, description }),
        });
    }

    async deleteMapping(id: number) {
        return this.request<{ ok: boolean }>(`/api/mappings/${id}`, { method: 'DELETE' });
    }

    // Image Generation
    async generateImage(prompt: string, size: string = "1024x1024", n: number = 1) {
        // We use the same Auth mechanism (Bearer token) as other endpoints.
        // However, the proxy requires an API Key for /v1/* routes if checking APIKeyMiddleware.
        // BUT, our current frontend uses JWT for everything under /api/*.
        // The image route is under /v1/images.
        // If we use `this.request` it adds the JWT token.
        // The backend's APIKeyMiddleware checks for "Authorization: Bearer <api_key>".
        // It DOES NOT accept our JWT session token.

        // Wait, looking at main.py: APIKeyMiddleware checks /v1/* and /v1beta/*.
        // It expects an API KEY.
        // Our frontend user has an API Key stored in their profile.
        // We should fetch the user's API Key first, OR update backend to accept JWT for /v1 routes (unlikely for broad compatibility).
        // 
        // Strategy: 
        // 1. Get current user info (including API Key)
        // 2. Use that API Key for the request.

        const user = await this.getMe();
        if (!user.api_key) {
            throw new Error("No API Key found for current user. Please generate one in Settings.");
        }

        const response = await fetch(`${this.baseUrl}/v1/images/generations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${user.api_key}`
            },
            body: JSON.stringify({
                prompt,
                size,
                n,
                response_format: "b64_json"
            })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Statistics
    async getStatsOverview() {
        return this.request<{
            total_requests: number;
            success_rate: number;
            avg_response_time_ms: number;
            today_requests: number;
        }>('/api/stats/overview');
    }

    async getStatsProtocols() {
        return this.request<Array<{ name: string; value: number }>>('/api/stats/protocols');
    }

    async getStatsAccounts() {
        return this.request<Array<{ email: string; requests: number }>>('/api/stats/accounts');
    }

    async getStatsModels() {
        return this.request<Array<{ model: string; count: number; percentage: number }>>('/api/stats/models');
    }

    async getStatsDaily() {
        return this.request<Array<{ date: string; requests: number }>>('/api/stats/daily');
    }

    async getStatsErrors() {
        return this.request<Array<{ type: string; count: number }>>('/api/stats/errors');
    }

    async getStatsQuotas() {
        return this.request<Array<{ email: string; tier: string; quota: number }>>('/api/stats/quotas');
    }
}

export const api = new ApiClient();
export default api;
