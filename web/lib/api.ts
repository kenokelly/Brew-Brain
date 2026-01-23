/**
 * Brew-Brain API Client
 * Standardized fetch wrapper with error handling, typing, and utilities
 */

import { ApiError, ApiResponse, isApiError } from '@/types/api';

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
    const { body, headers: customHeaders, ...rest } = options;

    const headers: HeadersInit = {
        ...customHeaders,
    };

    // Only set Content-Type for JSON bodies (not FormData)
    if (body && !(body instanceof FormData)) {
        (headers as Record<string, string>)['Content-Type'] = 'application/json';
    }

    const config: RequestInit = {
        ...rest,
        headers,
        body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    };

    try {
        const response = await fetch(url, config);

        // Handle non-OK responses
        if (!response.ok) {
            let errorData: unknown;
            try {
                errorData = await response.json();
            } catch {
                errorData = await response.text();
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

// ============================================
// TYPED API ENDPOINTS
// ============================================

import type {
    SystemStatus,
    TapsResponse,
    ScoutResult,
    WaterProfile,
    IBUResult,
    CarbonationResult,
    RefractometerResult,
    PrimingResult,
    YeastMetadata,
    RecipeResult,
    RecipeAnalysis,
    AuditResult,
    SourcingResult,
    PriceComparisonResult,
    Inventory,
    PipelineResult,
    AlertResult,
    SimulationResult,
    BrewfatherBatch,
    BrewfatherRecipe,
} from '@/types/api';

export const brewApi = {
    // Status
    getStatus: () => api.get<SystemStatus>('/api/status'),
    getTaps: () => api.get<TapsResponse>('/api/taps'),

    // Automation - Scout
    scout: (query: string) => api.post<ScoutResult[]>('/api/automation/scout', { query }),

    // Automation - Water
    getWaterProfile: (profile: string) => api.get<WaterProfile>(`/api/automation/water/${profile}`),
    getAllWaterProfiles: () => api.get<Record<string, WaterProfile>>('/api/automation/water/all'),

    // Automation - Calculators
    calcIBU: (data: { amount: number; alpha: number; time: number; volume: number; gravity: number }) =>
        api.post<IBUResult>('/api/automation/calc_ibu', data),
    calcCarbonation: (data: { temp_c: number; volumes_co2: number }) =>
        api.post<CarbonationResult>('/api/automation/calc/carbonation', data),
    calcRefractometer: (data: { original_brix: number; final_brix: number; wort_correction_factor?: number }) =>
        api.post<RefractometerResult>('/api/automation/calc/refractometer', data),
    calcPriming: (data: { volume_liters: number; temp_c: number; target_co2: number; sugar_type?: string }) =>
        api.post<PrimingResult>('/api/automation/calc/priming', data),

    // Automation - Yeast
    searchYeast: (query: string) => api.post<YeastMetadata>('/api/automation/yeast/search', { query }),

    // Automation - Recipes
    searchRecipes: (query: string) => api.post<RecipeResult[]>('/api/automation/recipes', { query }),
    analyzeRecipes: (query: string) => api.post<RecipeAnalysis>('/api/automation/recipes/analyze', { query }),
    auditRecipe: (data: { style: string; og: number; name: string }) =>
        api.post<AuditResult>('/api/automation/learning/audit', data),
    scaleRecipe: (recipe: RecipeResult) => api.post<RecipeResult>('/api/automation/recipes/scale', recipe),

    // Automation - Sourcing
    searchSourcing: (query: string) => api.post<SourcingResult[]>('/api/automation/sourcing/search', { query }),
    comparePrices: (recipe_id: string) => api.post<PriceComparisonResult>('/api/automation/sourcing/compare', { recipe_id }),

    // Automation - Inventory
    getInventory: () => api.get<Inventory>('/api/automation/inventory'),
    syncInventory: () => api.post<{ status: string; inventory: Inventory }>('/api/automation/inventory/sync'),

    // Automation - Pipeline
    scanPipeline: () => api.post<PipelineResult>('/api/automation/monitoring/scan'),
    analyzeBatch: (batch_id: string, target: number) =>
        api.post<AlertResult>('/api/automation/brewfather/analyze', { batch_id, target }),

    // Automation - Simulation
    simulate: (data: {
        efficiency: number;
        volume: number;
        yeast?: string;
        grains: { weight_kg: number; potential: number }[];
    }) => api.post<SimulationResult>('/api/automation/learning/simulate', data),

    // Brewfather
    getBrewfatherBatches: () => api.get<BrewfatherBatch[]>('/api/automation/brewfather/batches'),
    getBrewfatherRecipes: () => api.get<BrewfatherRecipe[]>('/api/automation/brewfather/recipes'),
};

export default brewApi;
