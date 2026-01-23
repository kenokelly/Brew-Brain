/**
 * Brew-Brain API Types
 * Centralized type definitions for all API responses
 */

// ============================================
// SYSTEM STATUS
// ============================================

export interface SystemStatus {
    cpu_temp?: number;
    memory_percent?: number;
    disk_percent?: number;
    pi_temp?: number;
    sg?: number;
    temp?: number;
    rssi?: number;
    batch_name?: string;
    status?: string;
    last_sync?: string;
}

export interface DataPoint {
    time: string;
    temp: number;
    sg: number;
}

// ============================================
// TAPS
// ============================================

export interface TapData {
    active: boolean;
    name?: string;
    style?: string;
    notes?: string;
    abv?: number;
    ibu?: number;
    og?: number;
    srm?: number;
    keg_total?: number;
    keg_remaining?: number;
    volume_unit?: string;
}

export interface TapsResponse {
    [key: string]: TapData;
}

// ============================================
// AUTOMATION - SCOUT
// ============================================

export interface ScoutResult {
    title: string;
    link: string;
    price: string;
    source: string;
    is_preferred?: boolean;
}

// ============================================
// AUTOMATION - WATER
// ============================================

export interface WaterProfile {
    calcium: number;
    magnesium: number;
    sodium: number;
    chloride: number;
    sulfate: number;
    bicarbonate: number;
    ph: number;
}

// ============================================
// AUTOMATION - CALCULATORS
// ============================================

export interface IBUResult {
    ibu: number;
    error?: string;
}

export interface CarbonationResult {
    psi: number;
    bar: number;
    kpa: number;
    temp_c: number;
    temp_f: number;
    volumes_co2: number;
    style_suggestion: string;
    equilibrium_days: string;
    error?: string;
}

export interface RefractometerResult {
    original_brix: number;
    final_brix: number;
    original_gravity: number;
    corrected_final_gravity: number;
    abv: number;
    apparent_attenuation: number;
    formula: string;
    note: string;
    error?: string;
}

export interface PrimingResult {
    sugar_type: string;
    total_grams: number;
    grams_per_liter: number;
    per_500ml_bottle: number;
    per_330ml_bottle: number;
    residual_co2: number;
    added_co2: number;
    target_co2: number;
    beer_temp_c: number;
    volume_liters: number;
    conditioning_time: string;
    available_sugars: string[];
    error?: string;
}

// ============================================
// AUTOMATION - YEAST
// ============================================

export interface YeastMetadata {
    name: string;
    url: string;
    attenuation: string;
    flocculation: string;
    temp_range: string;
    abv_tolerance: string;
    error?: string;
}

// ============================================
// AUTOMATION - RECIPES
// ============================================

export interface RecipeResult {
    name: string;
    og: number;
    ibu: number;
    abv: string;
    batch_size_l: number;
    style?: string;
    hops_summary?: string;
    grain_breakdown?: string[];
    est_ph?: string;
    target_ph?: string;
    hardware_valid?: boolean;
    hardware_warnings?: string[];
    source_url?: string;
    is_scaled?: boolean;
}

export interface RecipeAnalysis {
    count: number;
    avg_og: number;
    avg_ibu: number;
    avg_abv: string;
    common_hops: Record<string, number>;
    common_dry_hops?: Record<string, number>;
    common_malts: Record<string, number>;
    recipes: RecipeResult[];
    error?: string;
}

export interface AuditResult {
    status: string;
    message?: string;
    tips?: string[];
    peer_count?: number;
    avg_peer_og?: number;
    avg_peer_att?: number;
    error?: string;
}

// ============================================
// AUTOMATION - SOURCING / PRICE COMPARISON
// ============================================

export interface SourcingResult {
    title: string;
    price: string;
    source: string;
    link?: string;
}

export interface PriceComparisonItem {
    name: string;
    tmm_price: number | null;
    geb_price: number | null;
    best: 'TMM' | 'GEB' | 'TIE';
}

export interface PriceComparisonResult {
    items: PriceComparisonItem[];
    total_tmm: number;
    total_geb: number;
    winner: string;
    error?: string;
}

// ============================================
// AUTOMATION - INVENTORY
// ============================================

export interface InventoryItem {
    name: string;
    amount: number;
    unit?: string;
    origin?: string;
    alpha?: number;
}

export interface Inventory {
    hops: InventoryItem[];
    fermentables: InventoryItem[];
    yeast: InventoryItem[];
    miscs: InventoryItem[];
}

// ============================================
// AUTOMATION - PIPELINE
// ============================================

export interface BatchHealthCheck {
    status: string;
    message: string;
}

export interface PipelineBatch {
    name: string;
    number?: string;
    brewer?: string;
    status: string;
    gravity?: number;
    temp?: number;
    health_check?: BatchHealthCheck;
}

export interface PipelineResult {
    batches: PipelineBatch[];
    error?: string;
}

export interface AlertResult {
    status: string;
    message: string;
    avg_temp?: number;
    temp_range?: string;
    stability_score?: number;
    error?: string;
}

// ============================================
// AUTOMATION - SIMULATION
// ============================================

export interface SimulationResult {
    predicted_og: number;
    predicted_fg?: number;
    predicted_abv?: number;
    expected_fg?: string;
    yeast_found?: boolean;
    attenuation_used?: number;
    hardware_error?: string;
    hardware_warning?: string;
    error?: string;
}

// ============================================
// BREWFATHER
// ============================================

export interface BrewfatherBatch {
    _id: string;
    name: string;
    batchNo?: number;
    status?: string;
}

export interface BrewfatherRecipe {
    _id: string;
    name: string;
}

// ============================================
// GENERIC API RESPONSE
// ============================================

export interface ApiError {
    error: string;
    message?: string;
}

export type ApiResponse<T> = T | ApiError;

export function isApiError<T>(response: ApiResponse<T>): response is ApiError {
    return (response as ApiError).error !== undefined;
}
