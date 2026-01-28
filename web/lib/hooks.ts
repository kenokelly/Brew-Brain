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
const fetcher = async <T>(url: string): Promise<T> => {
    const res = await fetch(url);

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
    return useSWR<SystemStatus>('/api/status', fetcher, {
        refreshInterval: 5000,
        revalidateOnFocus: false,
    });
}

/**
 * Fetch tap data with 10s refresh interval
 */
export function useTaps() {
    return useSWR<TapsResponse>('/api/taps', fetcher, {
        refreshInterval: 10000,
        revalidateOnFocus: false,
    });
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
    return useSWR<Record<string, string>>('/api/settings', fetcher, {
        revalidateOnFocus: false,
    });
}
