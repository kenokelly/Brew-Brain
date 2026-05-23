"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Loader2, Beer, GlassWater } from "lucide-react";
import Image from "next/image";
import toast from "react-hot-toast";

interface Tap {
    tap_id: string;
    beer_name: string;
    style: string;
    abv: number;
    keg_volume_l: number;
    keg_remaining_l?: number;
    remaining_pct: number;
    qr_code_base64: string;
    untappd_url?: string;
}

export default function KioskPage() {
    const [taps, setTaps] = useState<Tap[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchTaps = async () => {
        try {
            const res = await apiFetch<any>("/api/taps");
            if (res?.data?.taps) {
                setTaps(res.data.taps);
            }
        } catch (err) {
            console.error("Failed to load taps", err);
        } finally {
            setLoading(false);
        }
    };

    const handlePour = async (tapId: string, amountMl: number) => {
        const toastId = toast.loading("Pouring...");
        try {
            await apiFetch(`/api/taps/${tapId}/pour`, {
                method: "POST",
                body: { amount_ml: amountMl }
            });
            toast.success(`Poured ${amountMl}ml`, { id: toastId });
            fetchTaps(); // Refresh data
        } catch (e: any) {
            toast.error(`Pour failed: ${e.message}`, { id: toastId });
        }
    };

    useEffect(() => {
        fetchTaps();
        const interval = setInterval(fetchTaps, 30000); // refresh every 30s
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen bg-black flex items-center justify-center">
                <Loader2 className="w-12 h-12 text-primary animate-spin" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-black text-white p-8 font-sans selection:bg-primary/30">
            <header className="mb-12 text-center">
                <h1 className="text-5xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-amber-200 to-amber-500 uppercase drop-shadow-sm">
                    On Tap Now
                </h1>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-8 max-w-7xl mx-auto">
                {taps.length === 0 ? (
                    <div className="col-span-full text-center text-zinc-500 py-20 text-xl font-medium">
                        No taps currently active.
                    </div>
                ) : (
                    taps.map((tap, i) => (
                        <div key={tap.tap_id} className="relative bg-zinc-900 border border-zinc-800 rounded-3xl p-8 flex flex-col gap-6 overflow-hidden group shadow-2xl transition-all duration-500 hover:border-amber-500/30 hover:shadow-amber-500/10">
                            {/* Number Badge */}
                            <div className="absolute -top-6 -right-6 text-9xl font-black text-white/[0.03] pointer-events-none transition-transform duration-500 group-hover:scale-110">
                                {i + 1}
                            </div>
                            
                            <div className="space-y-2 z-10">
                                <h2 className="text-3xl font-bold tracking-tight text-white line-clamp-2">
                                    {tap.beer_name || "Unknown Brew"}
                                </h2>
                                <div className="flex items-center gap-3 text-amber-500 font-semibold tracking-wide uppercase text-sm">
                                    <span>{tap.style || "Style Unknown"}</span>
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500/50" />
                                    <span>{tap.abv}% ABV</span>
                                </div>
                            </div>

                            <div className="flex flex-col z-10 mt-6 gap-6 h-full justify-between">
                                {/* Keg Level */}
                                <div className="space-y-3">
                                    <div className="flex justify-between items-end">
                                        <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Keg Level</span>
                                        <div className="text-right">
                                            <span className="text-white text-lg font-bold">{tap.remaining_pct.toFixed(0)}%</span>
                                            <span className="text-amber-500 font-medium ml-2">{tap.keg_remaining_l?.toFixed(1) || 0}L</span>
                                            <span className="text-zinc-500 text-xs ml-1">/ {tap.keg_volume_l}L</span>
                                        </div>
                                    </div>
                                    
                                    <div className="h-4 bg-zinc-800 rounded-full overflow-hidden border border-zinc-700/50">
                                        <div 
                                            className="h-full bg-gradient-to-r from-amber-600 to-amber-400 rounded-full transition-all duration-1000 ease-out"
                                            style={{ width: `${Math.max(0, Math.min(100, tap.remaining_pct))}%` }}
                                        />
                                    </div>
                                    
                                    {tap.untappd_url && (
                                        <div className="pt-2">
                                            <a href={tap.untappd_url} target="_blank" rel="noreferrer" className="text-xs font-bold text-amber-500 hover:text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 px-3 py-1.5 rounded-lg transition-colors inline-block">
                                                VIEW ON UNTAPPD
                                            </a>
                                        </div>
                                    )}
                                </div>

                                {/* Controls & QR Code Row */}
                                <div className="flex items-end justify-between gap-4 mt-auto w-full">
                                    {/* Pour Controls */}
                                    <div className="flex justify-start items-end gap-2 sm:gap-4 h-20 flex-1">
                                        <button onClick={() => handlePour(tap.tap_id || `tap_${i+1}`, 568)} className="group flex flex-col items-center justify-end h-full flex-1 hover:bg-white/5 rounded-xl transition-all pb-1">
                                            <Beer className="w-8 h-8 text-amber-500 group-hover:scale-110 transition-transform mb-2" />
                                            <span className="text-[10px] font-bold text-zinc-400 uppercase">1 Pint</span>
                                        </button>
                                        
                                        <button onClick={() => handlePour(tap.tap_id || `tap_${i+1}`, 379)} className="group flex flex-col items-center justify-end h-full flex-1 hover:bg-white/5 rounded-xl transition-all pb-1">
                                            <Beer className="w-6 h-6 text-amber-500 group-hover:scale-110 transition-transform mb-2" />
                                            <span className="text-[10px] font-bold text-zinc-400 uppercase">2/3 Pint</span>
                                        </button>

                                        <button onClick={() => handlePour(tap.tap_id || `tap_${i+1}`, 284)} className="group flex flex-col items-center justify-end h-full flex-1 hover:bg-white/5 rounded-xl transition-all pb-1">
                                            <GlassWater className="w-6 h-6 text-amber-500/80 group-hover:scale-110 transition-transform mb-2" />
                                            <span className="text-[10px] font-bold text-zinc-400 uppercase">1/2 Pint</span>
                                        </button>

                                        <button onClick={() => handlePour(tap.tap_id || `tap_${i+1}`, 189)} className="group flex flex-col items-center justify-end h-full flex-1 hover:bg-white/5 rounded-xl transition-all pb-1">
                                            <GlassWater className="w-4 h-4 text-amber-500/80 group-hover:scale-110 transition-transform mb-2" />
                                            <span className="text-[10px] font-bold text-zinc-400 uppercase">1/3 Pint</span>
                                        </button>
                                    </div>

                                    {/* QR Code */}
                                    {tap.qr_code_base64 && (
                                        <div className="shrink-0 bg-white p-2 rounded-xl shadow-lg flex flex-col items-center justify-center w-20 h-20 sm:w-24 sm:h-24 transition-transform hover:scale-105 ml-2">
                                            <img src={`data:image/png;base64,${tap.qr_code_base64}`} alt="QR" className="w-full h-full object-contain" />
                                            <span className="text-[7px] sm:text-[8px] font-black text-black/50 tracking-widest mt-1">SCAN</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
