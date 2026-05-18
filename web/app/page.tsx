"use client";

import { useSocket } from "@/lib/socket";
import { Activity, Thermometer, Droplets, Gauge } from "lucide-react";
import { motion } from "framer-motion";

export default function Dashboard() {
  const { systemStatus, sensors } = useSocket();

  const isFermenting = systemStatus?.phase === "Fermenting";
  const bgGradient = isFermenting 
    ? "from-emerald-500/10 via-emerald-500/5 to-transparent" 
    : "from-blue-500/10 via-blue-500/5 to-transparent";

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      
      {/* Header section with gradient background matching the current phase */}
      <div className={`relative overflow-hidden rounded-3xl bg-gradient-to-br ${bgGradient} border border-border p-8`}>
        <div className="relative z-10">
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2">
            {systemStatus?.batch_name || "No Active Batch"}
          </h1>
          <div className="flex items-center gap-2 text-muted-foreground font-medium">
            <span className="flex items-center gap-1.5 bg-background/50 px-3 py-1 rounded-full border border-border backdrop-blur-sm">
              <Activity className="w-4 h-4" />
              {systemStatus?.phase || "Idle"}
            </span>
          </div>
        </div>
      </div>

      {/* Core Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Temperature Card */}
        <motion.div 
          whileHover={{ y: -5 }}
          className="glass-card p-6 flex flex-col justify-between"
        >
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-red-500/10 rounded-2xl text-red-500">
              <Thermometer className="w-6 h-6" />
            </div>
            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Temperature</span>
          </div>
          <div>
            <div className="text-4xl font-bold tracking-tight">
              {sensors?.temp_c?.toFixed(1) || "--"}
              <span className="text-xl text-muted-foreground ml-1">°C</span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">Target: {systemStatus?.target_temp || "--"}°C</p>
          </div>
        </motion.div>

        {/* Gravity Card */}
        <motion.div 
          whileHover={{ y: -5 }}
          className="glass-card p-6 flex flex-col justify-between"
        >
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-blue-500/10 rounded-2xl text-blue-500">
              <Droplets className="w-6 h-6" />
            </div>
            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Gravity</span>
          </div>
          <div>
            <div className="text-4xl font-bold tracking-tight">
              {sensors?.sg?.toFixed(3) || "1.000"}
            </div>
            <p className="text-sm text-muted-foreground mt-2">Target FG: {systemStatus?.target_fg || "1.010"}</p>
          </div>
        </motion.div>

        {/* Pressure Card (Mocked for now, but aesthetic) */}
        <motion.div 
          whileHover={{ y: -5 }}
          className="glass-card p-6 flex flex-col justify-between"
        >
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-purple-500/10 rounded-2xl text-purple-500">
              <Gauge className="w-6 h-6" />
            </div>
            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Pressure</span>
          </div>
          <div>
            <div className="text-4xl font-bold tracking-tight">
              {sensors?.pressure_psi?.toFixed(1) || "12.5"}
              <span className="text-xl text-muted-foreground ml-1">PSI</span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">Spunding Valve set to 15 PSI</p>
          </div>
        </motion.div>
        
      </div>

    </div>
  );
}
