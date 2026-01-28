'use client';

import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';

interface PintGlassProps {
    beerColor: string;
    fillPercentage: number; // 0 to 100
    className?: string;
    animated?: boolean;
}

export function PintGlass({ beerColor, fillPercentage, className, animated = true }: PintGlassProps) {
    const [height, setHeight] = useState(animated ? 0 : fillPercentage);

    useEffect(() => {
        if (animated) {
            // Animating up on mount
            const timer = setTimeout(() => setHeight(fillPercentage), 100);
            return () => clearTimeout(timer);
        } else {
            setHeight(fillPercentage);
        }
    }, [fillPercentage, animated]);

    return (
        <div className={cn("relative w-[70px] h-[100px]", className)}>
            <div
                className="glass-container w-full h-full relative bg-white/5 overflow-hidden"
                style={{
                    clipPath: 'polygon(10% 100%, 0% 0%, 100% 0%, 90% 100%)',
                }}
            >
                {/* Liquid */}
                <div
                    className="absolute bottom-0 left-0 w-full transition-all duration-1000 ease-in-out opacity-90"
                    style={{
                        height: `${height}%`,
                        backgroundColor: beerColor
                    }}
                >
                    {/* Foam */}
                    <div className="absolute top-[-4px] left-0 w-full h-[4px] bg-white/90 rounded-t-sm" />

                    {/* Bubbles / Carbonation (Optional Subtle Effect) */}
                    <div className="absolute inset-0 opacity-20 bg-[url('/static/noise.png')] mix-blend-overlay" />
                </div>

                {/* Glass Highlights/Reflections */}
                <div className="absolute inset-0 bg-gradient-to-r from-white/10 via-transparent to-white/5 pointer-events-none" />
                <div className="absolute inset-0 shadow-[inset_0_0_20px_rgba(255,255,255,0.1)] pointer-events-none" />
            </div>

            {/* Glass Rim Overlay (Border) */}
            <div
                className="absolute inset-0 border-x-2 border-b-2 border-white/10 pointer-events-none"
                style={{
                    clipPath: 'polygon(10% 100%, 0% 0%, 100% 0%, 90% 100%)',
                }}
            />

            {/* Shadow Base */}
            <div
                className="absolute bottom-[-10px] left-[10%] right-[10%] h-[10px] rounded-full blur-md opacity-40 transition-colors duration-1000"
                style={{ backgroundColor: beerColor }}
            />
        </div>
    );
}

// Utility to get SRM color if needed (or keep it in a shared util)
export const srmToHex = (srm: number) => {
    // Basic approximate map
    if (!srm) return "#f59e0b"; // default amber
    if (srm <= 2) return "#FFE699";
    if (srm <= 4) return "#FFD878";
    if (srm <= 6) return "#FFBF42";
    if (srm <= 9) return "#FBB123";
    if (srm <= 12) return "#D9921E";
    if (srm <= 17) return "#A6620C";
    if (srm <= 24) return "#7B4607";
    if (srm <= 35) return "#361F0B";
    return "#090909";
};
