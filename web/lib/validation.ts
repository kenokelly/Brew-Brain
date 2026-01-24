/**
 * Zod Validation Schemas for Brew-Brain
 * Input validation for calculators and forms
 */

import { z } from 'zod';

// ============================================
// CALCULATOR SCHEMAS
// ============================================

export const ibuSchema = z.object({
    amount: z.number().positive('Hop amount must be positive'),
    alpha: z.number().min(0).max(30, 'Alpha acid typically 0-30%'),
    time: z.number().min(0).max(120, 'Boil time typically 0-120 minutes'),
    volume: z.number().positive('Volume must be positive'),
    gravity: z.number().min(1.000).max(1.200, 'Gravity typically 1.000-1.200'),
});

export const carbonationSchema = z.object({
    temp_c: z.number().min(-5).max(30, 'Temperature must be -5 to 30°C'),
    volumes_co2: z.number().min(1).max(5, 'CO2 volumes typically 1-5'),
});

export const refractometerSchema = z.object({
    original_brix: z.number().min(0).max(40, 'Brix typically 0-40'),
    final_brix: z.number().min(0).max(40, 'Brix typically 0-40'),
    wort_correction_factor: z.number().min(0.9).max(1.1).optional(),
});

export const primingSchema = z.object({
    volume_liters: z.number().positive('Volume must be positive'),
    temp_c: z.number().min(0).max(30, 'Temperature must be 0-30°C'),
    target_co2: z.number().min(1).max(5, 'CO2 volumes typically 1-5'),
    sugar_type: z.string().optional(),
});

// ============================================
// SIMULATION SCHEMAS
// ============================================

export const grainSchema = z.object({
    weight_kg: z.number().positive('Weight must be positive'),
    potential: z.number().min(1.000).max(1.100, 'Potential typically 1.000-1.100'),
});

export const simulationSchema = z.object({
    efficiency: z.number().min(40).max(100, 'Efficiency typically 40-100%'),
    volume: z.number().positive('Volume must be positive'),
    yeast: z.string().optional(),
    grains: z.array(grainSchema).min(1, 'At least one grain required'),
});

// ============================================
// UTILITY TYPES
// ============================================

export type IBUInput = z.infer<typeof ibuSchema>;
export type CarbonationInput = z.infer<typeof carbonationSchema>;
export type RefractometerInput = z.infer<typeof refractometerSchema>;
export type PrimingInput = z.infer<typeof primingSchema>;
export type SimulationInput = z.infer<typeof simulationSchema>;
