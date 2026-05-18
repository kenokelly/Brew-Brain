"use client";

import useSWR from "swr";
import { Beer, Droplet, Percent, Info } from "lucide-react";
import { motion } from "framer-motion";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function TapList() {
  const { data, error, isLoading } = useSWR("/api/taps", fetcher, {
    refreshInterval: 10000,
  });

  if (isLoading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading Tap List...</div>;
  if (error) return <div className="p-8 text-center text-destructive">Failed to load tap list.</div>;

  const tapsData = data?.data?.taps || [];

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <div className="mb-8">
        <h1 className="text-4xl font-black tracking-tight mb-2">On Tap</h1>
        <p className="text-muted-foreground">What's currently pouring in the brewery.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {tapsData.map((tap: any, index: number) => (
          <motion.div
            key={tap.tap_id || index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="glass-card overflow-hidden flex flex-col group"
          >
            {/* Beer Header & Color Bar */}
            <div className="h-3 w-full bg-[#FFC107]" /> {/* Mock color for now */}
            
            <div className="p-6 flex-1 flex flex-col">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Tap {index + 1}</div>
                  <h2 className="text-2xl font-black leading-tight group-hover:text-primary transition-colors">
                    {tap.beer_name || "Empty Tap"}
                  </h2>
                  <p className="text-sm font-medium text-muted-foreground mt-1">
                    {tap.style || "N/A"}
                  </p>
                </div>
              </div>

              {/* Stats Row */}
              <div className="flex gap-4 mb-8">
                <div className="flex items-center gap-1.5 bg-secondary/50 px-3 py-1.5 rounded-full text-sm font-semibold">
                  <Percent className="w-4 h-4 text-primary" />
                  {tap.abv?.toFixed(1)}% ABV
                </div>
                {/* Calories mock */}
                <div className="flex items-center gap-1.5 bg-secondary/50 px-3 py-1.5 rounded-full text-sm font-semibold text-muted-foreground">
                  <Info className="w-4 h-4" />
                  ~210 Cal
                </div>
              </div>

              {/* Keg Volume Ring / Bar */}
              <div className="mt-auto">
                <div className="flex justify-between text-xs font-semibold mb-2">
                  <span className="text-muted-foreground uppercase tracking-wider">Remaining</span>
                  <span>{tap.remaining_pct?.toFixed(0)}%</span>
                </div>
                <div className="w-full h-3 bg-secondary rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${tap.remaining_pct || 0}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className={`h-full rounded-full ${
                      (tap.remaining_pct || 0) > 20 ? 'bg-primary' : 'bg-destructive'
                    }`}
                  />
                </div>
                <p className="text-[10px] text-muted-foreground mt-2 text-right">
                  Keg size: {tap.keg_volume_l}L
                </p>
              </div>
            </div>

            {/* QR Code Section */}
            {tap.qr_code_base64 && (
              <div className="border-t border-border/50 bg-secondary/20 p-4 flex flex-col items-center gap-2">
                 <img src={`data:image/png;base64,${tap.qr_code_base64}`} alt="QR Code" className="w-24 h-24 rounded-md" />
                 <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Scan for Details</span>
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
