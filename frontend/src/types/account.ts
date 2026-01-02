/**
 * Account and Token Types
 * 
 * Matches the Python backend models
 */

export interface Token {
    access_token: string;
    refresh_token: string;
    expires_in: number;
    expiry_timestamp: number;
    token_type: string;
    email: string;
    project_id?: string;
    subscription_tier?: string;  // FREE/PRO/ULTRA
    average_quota?: number;      // Cached avg quota for routing
}

export interface QuotaModel {
    name: string;
    percentage: number;
    remaining_fraction?: number;
}

export interface Quota {
    models: QuotaModel[];
    last_updated?: number;
}

export interface Account {
    id: string;
    email: string;
    name?: string;
    created_at: number;
    last_used?: number;
    token: Token;
    quota?: Quota;
}

export interface PoolStatus {
    pool_size: number;
    accounts: {
        account_id: string;
        email: string;
        project_id?: string;
        subscription_tier?: string;
        average_quota?: number;
        expiry_timestamp: number;
        expires_in_seconds: number;
    }[];
}

export interface AvailableModelsResponse {
    account_email: string;
    project_id: string;
    total_models: number;
    models: string[];
}
