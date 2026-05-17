'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Activity, Thermometer, Droplets, Server, Wifi, Brain, RefreshCcw, ExternalLink, BookOpen, Sparkles } from 'lucide-react';
import { useSocket } from '@/lib/socket';
import { useStatus } from '@/lib/hooks';
import { DashboardSkeleton } from '@/components/ui/skeleton';
import { AnomalyWidget } from '@/components/AnomalyWidget';
import { AdviceWidget } from '@/components/AdviceWidget';
import { PredictionCard } from '@/components/PredictionCard';
import { PeerComparisonWidget } from '@/components/PeerComparison';
import { BrewDayGuide } from '@/components/BrewDayGuide';
import { GrafanaChart } from '@/components/GrafanaChart';
import { SystemHealth } from '@/components/SystemHealth';
import type { SystemStatus } from '@/types/api';
import { toast } from 'react-hot-toast';

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
};

export default function Dashboard() {
  const { socket, isConnected: connected } = useSocket();
  const { data: status, error, isLoading, mutate: mutateStatus } = useStatus();
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [timeRange, setTimeRange] = useState('now-7d');

  // Socket Listeners for real-time updates
  useEffect(() => {
    if (!socket) return;

    const handleStatusUpdate = (data: SystemStatus) => {
      if (data?.temp && data?.sg) {
        mutateStatus(); // Refresh SWR cache
      }
    };

    socket.on('status_update', handleStatusUpdate);
    return () => {
      socket.off('status_update', handleStatusUpdate);
    };
  }, [socket, mutateStatus]);

  const handleSyncBrewfather = async () => {
    const toastId = toast.loading("Syncing with Brewfather...");
    try {
      const res = await fetch('/api/sync_brewfather', { method: 'POST' });
      const d = await res.json();
      if (res.ok && d.status === 'synced') {
        toast.success(`Synced batch: ${d.data.name}`, { id: toastId });
        mutateStatus();
      } else {
        toast.error(`Sync error: ${d.error || 'Unknown'}`, { id: toastId });
      }
    } catch (e: any) {
      toast.error(`Error: ${e.message}`, { id: toastId });
    }
  };

  const openTiltPi = () => {
    window.open(`http://${window.location.hostname}:1880/ui/`, '_blank');
  };

  // Calculations for Rings
  const og = status?.og || 1.050;
  const sg = status?.sg || 1.000;
  const abv = Math.max(0, (og - sg) * 131.25);
  const att = og > 1 ? Math.max(0, ((og - sg) / (og - 1)) * 100) : 0;

  if (isLoading) return <DashboardSkeleton />;

  return (
    <main className="min-h-screen p-4 md:p-8 space-y-8 max-w-7xl mx-auto selection:bg-primary/20 pb-24">
      {/* Header Section */}
      <motion.header 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex flex-col md:flex-row md:items-end justify-between gap-6"
      >
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-primary">
            <Sparkles className="w-5 h-5" />
            <span className="text-sm font-bold uppercase tracking-widest opacity-70">Intelligent Monitoring</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight text-gradient">
            {status?.batch_name || "Brew Brain"}
          </h1>
          <p className="text-muted-foreground font-medium text-lg">
            {status?.batch_notes || "Autonomous Fermentation Intelligence"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-4 py-2 rounded-full glass-card shadow-sm">
            <div className={cn("w-2 h-2 rounded-full animate-pulse",
              connected ? "bg-emerald-500" : (!error && status) ? "bg-amber-500" : "bg-rose-500"
            )} />
            <span className="text-xs font-bold uppercase tracking-wider">
              {connected ? "Real-time" : (!error && status) ? "Live" : "Offline"}
            </span>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsGuideOpen(true)}
            className="hidden md:flex items-center gap-2 px-6 py-2.5 rounded-full bg-primary text-primary-foreground font-bold text-sm shadow-lg shadow-primary/20 transition-all"
          >
            <BookOpen className="w-4 h-4" />
            Prep Guide
          </motion.button>
        </div>
      </motion.header>

      <BrewDayGuide isOpen={isGuideOpen} onClose={() => setIsGuideOpen(false)} />

      {/* Main Grid */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        <StatCard
          icon={Droplets}
          label="Gravity"
          value={status?.sg ? status.sg.toFixed(3) : "--.---"}
          unit="SG"
          color="text-amber-500"
          bgGradient="from-amber-500/10"
        />
        <StatCard
          icon={Thermometer}
          label="Temperature"
          value={status?.temp ? status.temp.toFixed(1) : "--.-"}
          unit={`°${status?.temp_unit || 'C'}`}
          color="text-blue-500"
          bgGradient="from-blue-500/10"
          subtext={status?.pi_temp ? `System: ${status.pi_temp}°C` : undefined}
        />
        <motion.div variants={itemVariants} className="glass-card glass-card-hover rounded-3xl p-6 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent pointer-events-none" />
          <span className="text-xs font-bold uppercase tracking-widest text-emerald-500/80 mb-4 z-10">Alcohol (ABV)</span>
          <RingChart value={abv} max={15} color="#10b981" unit="%" />
        </motion.div>
        <motion.div variants={itemVariants} className="glass-card glass-card-hover rounded-3xl p-6 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent pointer-events-none" />
          <span className="text-xs font-bold uppercase tracking-widest text-purple-500/80 mb-4 z-10">Attenuation</span>
          <RingChart value={att} max={100} color="#a855f7" unit="%" />
        </motion.div>
      </motion.div>

      {/* Insights Section */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-8"
      >
        <motion.div variants={itemVariants}>
          <PredictionCard className="h-full rounded-3xl" />
        </motion.div>
        <motion.div variants={itemVariants}>
          <AdviceWidget className="h-full rounded-3xl" />
        </motion.div>
      </motion.div>

      {/* Secondary Tools */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
      >
        <motion.div variants={itemVariants}>
          <AnomalyWidget className="h-full rounded-3xl" />
        </motion.div>
        <motion.div variants={itemVariants}>
          <PeerComparisonWidget />
        </motion.div>
        <motion.div variants={itemVariants}>
          <SystemHealth />
        </motion.div>
      </motion.div>

      {/* Data Visualization */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="space-y-6"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h3 className="text-2xl font-black tracking-tight flex items-center gap-3">
            <Activity className="w-6 h-6 text-primary" /> Fermentation Analysis
          </h3>
          <div className="flex flex-wrap gap-3">
            <button onClick={openTiltPi} className="flex items-center gap-2 px-4 py-2 text-xs font-bold uppercase rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition-all">
              <ExternalLink className="w-3.5 h-3.5" /> TiltPi Panel
            </button>
            <div className="flex bg-secondary/50 rounded-full p-1 border border-border/50">
              {['now-24h', 'now-3d', 'now-7d', 'now-30d'].map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={cn(
                    "px-4 py-1.5 text-[10px] font-bold uppercase rounded-full transition-all",
                    timeRange === range ? "bg-primary text-primary-foreground shadow-md" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {range.replace('now-', '')}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="w-full h-[450px] md:h-[650px] rounded-[2rem] overflow-hidden glass-card relative group shadow-2xl">
          <GrafanaChart timeRange={timeRange} />
          <div className="absolute inset-0 border-[10px] border-card/50 pointer-events-none rounded-[2rem]" />
        </div>
      </motion.div>
    </main>
  );
}

function StatCard({ icon: Icon, label, value, unit, color, bgGradient, subtext }: { icon: any, label: string, value: string, unit: string, color: string, bgGradient: string, subtext?: string }) {
  return (
    <motion.div
      variants={itemVariants}
      className="glass-card glass-card-hover rounded-3xl p-6 relative overflow-hidden group"
    >
      <div className={cn("absolute inset-0 bg-gradient-to-br to-transparent pointer-events-none opacity-40", bgGradient)} />
      <div className="flex items-center justify-between mb-4 relative z-10">
        <div className={cn("p-2.5 rounded-2xl bg-secondary/80", color)}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      
      <div className="space-y-1 relative z-10">
        <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">{label}</p>
        <div className="flex items-baseline gap-1">
          <h3 className="text-3xl font-black tabular-nums tracking-tighter">{value}</h3>
          <span className="text-sm font-bold text-muted-foreground">{unit}</span>
        </div>
        {subtext && <div className="text-[10px] font-bold text-muted-foreground mt-1 opacity-60">{subtext}</div>}
      </div>

      <Icon className={cn("absolute -bottom-4 -right-4 w-24 h-24 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity", color)} />
    </motion.div>
  );
}

function RingChart({ value, max, color, unit }: { value: number, max: number, color: string, unit: string }) {
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(value / max, 1) * circumference);

  return (
    <div className="relative w-24 h-24 z-10">
      <svg className="w-full h-full transform -rotate-90">
        <circle className="text-secondary/30" strokeWidth="8" stroke="currentColor" fill="transparent" r={radius} cx="48" cy="48" />
        <motion.circle
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeLinecap="round"
          stroke={color}
          fill="transparent"
          r={radius}
          cx="48"
          cy="48"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span className="text-xl font-black tabular-nums leading-none">{value.toFixed(1)}</span>
        <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter mt-1">{unit}</span>
      </div>
    </div>
  );
}
