'use client';

/**
 * SWR Hooks for Brew-Brain
 * Centralized data fetching with caching and revalidation
 */

import useSWR from 'swr';
import type {
    SystemStatus,
    TapsResponse,
    Inventory,
    BrewfatherBatch,
    BrewfatherRecipe,
} from '@/types/api';

// Default fetcher with error handling
export const fetcher = async <T>(url: string): Promise<T> => {
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
    };

    // Try to get API token from localStorage
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("brew_brain_token");
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
    }

    const res = await fetch(url, { headers });

    // Check Content-Type
    const contentType = res.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
        const text = await res.text();
        console.error(`[API Error] ${url} returned ${res.status} (Non-JSON):`, text.substring(0, 200));
        // Throw with a preview of the text
        throw new Error(`API returned non-JSON (${res.status}): ${text.substring(0, 100)}`);
    }

    if (!res.ok) {
        // Try to parse error JSON if present
        try {
            const data = await res.json();
            throw new Error(data.error || `API error: ${res.status}`);
        } catch (e: any) {
            // Fallback if JSON parse fails or matches outer catch
            if (e.message.includes("API error")) throw e;
            throw new Error(`API error: ${res.status}`);
        }
    }

    return res.json();
};

// ============================================
// HOOKS
// ============================================

/**
 * Fetch system status with 5s refresh interval
 */
export function useStatus() {
    const { data, error, mutate, isLoading } = useSWR<any>('/api/status', fetcher, {
        refreshInterval: 5000,
        revalidateOnFocus: false,
    });
    
    return {
        data: data as SystemStatus | undefined,
        isLoading,
        isError: !!error,
        error,
        mutate
    };
}

/**
 * Fetch tap data with 10s refresh interval
 */
export function useTaps() {
    const { data, error, mutate, isLoading } = useSWR<any>('/api/taps', fetcher, {
        refreshInterval: 10000,
        revalidateOnFocus: false,
    });

    return {
        data: data?.data as Record<string, any> | undefined,
        isLoading,
        isError: !!error,
        error,
        mutate
    };
}

/**
 * Fetch inventory (on-demand, no auto-refresh)
 */
export function useInventory() {
    return useSWR<Inventory>('/api/automation/inventory', fetcher, {
        revalidateOnFocus: false,
    });
}

/**
 * Fetch Brewfather batches
 */
export function useBrewfatherBatches() {
    return useSWR<BrewfatherBatch[]>('/api/automation/brewfather/batches', fetcher, {
        revalidateOnFocus: false,
    });
}

/**
 * Fetch Brewfather recipes
 */
export function useBrewfatherRecipes() {
    return useSWR<BrewfatherRecipe[]>('/api/automation/brewfather/recipes', fetcher, {
        revalidateOnFocus: false,
    });
}

/**
 * Fetch all application settings
 */
export function useSettings() {
    const { data, error, mutate, isValidating, isLoading } = useSWR<any>('/api/settings', fetcher, {
        revalidateOnFocus: false,
    });
    
    return {
        data: data?.data as Record<string, any> | undefined,
        status: data?.status,
        isLoading,
        isError: !!error,
        error,
        mutate,
        isValidating
    };
}
