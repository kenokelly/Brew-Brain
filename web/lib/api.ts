/**
 * Brew-Brain API Client
 * Standardized fetch wrapper with error handling, typing, and utilities
 */

import { isApiError } from '@/types/api';

export function getApiUrl(path: string): string {
    if (process.env.NODE_ENV === 'development' && path.startsWith('/api')) {
        if (typeof window !== "undefined") {
            return `http://${window.location.hostname}:5000${path}`;
        }
    }
    return path;
}

export class ApiClientError extends Error {
    public status: number;
    public data?: unknown;

    constructor(message: string, status: number, data?: unknown) {
        super(message);
        this.name = 'ApiClientError';
        this.status = status;
        this.data = data;
    }
}

interface FetchOptions extends Omit<RequestInit, 'body'> {
    body?: object | FormData;
}

/**
 * Generic fetch wrapper with proper error handling
 */
export async function apiFetch<T>(
    url: string,
    options: FetchOptions = {}
): Promise<T> {
    const fetchUrl = getApiUrl(url);

    const { body, headers: customHeaders, ...rest } = options;

    const headers: Record<string, string> = {};

    if (customHeaders) {
        if (customHeaders instanceof Headers) {
            customHeaders.forEach((value, key) => {
                headers[key] = value;
            });
        } else if (Array.isArray(customHeaders)) {
            customHeaders.forEach(([key, value]) => {
                headers[key] = value;
            });
        } else {
            Object.assign(headers, customHeaders);
        }
    }

    // Try to get API token from localStorage
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("brew_brain_token");
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
    }

    // Only set Content-Type for JSON bodies (not FormData)
    if (body && !(body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const config: RequestInit = {
        ...rest,
        headers,
        body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    };

    try {
        const response = await fetch(fetchUrl, config);

        // Handle non-OK responses
        if (!response.ok) {
            let errorData: unknown;
            try {
                const text = await response.text();
                try {
                    errorData = JSON.parse(text);
                } catch {
                    errorData = text;
                }
            } catch (e) {
                errorData = 'Unable to parse response body';
            }
            throw new ApiClientError(
                `Request failed with status ${response.status}`,
                response.status,
                errorData
            );
        }

        // Parse JSON response
        const data = await response.json();

        // Check for API-level errors in response body
        if (isApiError(data)) {
            throw new ApiClientError(data.error, 200, data);
        }

        return data as T;
    } catch (error) {
        if (error instanceof ApiClientError) {
            throw error;
        }
        // Network or parsing errors
        throw new ApiClientError(
            error instanceof Error ? error.message : 'Unknown error occurred',
            0
        );
    }
}

// ============================================
// CONVENIENCE METHODS
// ============================================

export const api = {
    get: <T>(url: string, options?: FetchOptions) =>
        apiFetch<T>(url, { ...options, method: 'GET' }),

    post: <T>(url: string, body?: object, options?: FetchOptions) =>
        apiFetch<T>(url, { ...options, method: 'POST', body }),

    put: <T>(url: string, body?: object, options?: FetchOptions) =>
        apiFetch<T>(url, { ...options, method: 'PUT', body }),

    delete: <T>(url: string, options?: FetchOptions) =>
        apiFetch<T>(url, { ...options, method: 'DELETE' }),

    upload: <T>(url: string, formData: FormData, options?: FetchOptions) =>
        apiFetch<T>(url, { ...options, method: 'POST', body: formData }),
};
