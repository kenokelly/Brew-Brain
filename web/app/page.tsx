'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Activity, Thermometer, Droplets, Server } from 'lucide-react';

interface SystemStatus {
  cpu_temp?: number;
  memory_percent?: number;
  disk_percent?: number;
  timestamp?: string;
}

export default function Dashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/status')
      .then((res) => res.json())
      .then((data) => {
        setStatus(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("API Error:", err);
        setLoading(false);
      });
  }, []);

  return (
    <main className="min-h-screen bg-background text-foreground p-8 font-sans selection:bg-primary/20">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
              Brew Brain
            </h1>
            <p className="text-muted-foreground mt-2 text-lg">
              Autonomous Fermentation Intelligence
            </p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/50 backdrop-blur-md border border-white/10 shadow-sm">
            <div className={cn("w-3 h-3 rounded-full animate-pulse", status ? "bg-emerald-500" : "bg-rose-500")} />
            <span className="text-sm font-medium">
              {status ? "System Online" : "Connecting..."}
            </span>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="CPU Temp"
            value={status?.cpu_temp ? `${status.cpu_temp.toFixed(1)}°C` : "--"}
            icon={<Thermometer className="w-5 h-5 text-rose-500" />}
          />
          <StatCard
            title="Memory Usage"
            value={status?.memory_percent ? `${status.memory_percent.toFixed(1)}%` : "--"}
            icon={<Activity className="w-5 h-5 text-blue-500" />}
          />
          <StatCard
            title="Disk Usage"
            value={status?.disk_percent ? `${status.disk_percent.toFixed(1)}%` : "--"}
            icon={<Server className="w-5 h-5 text-amber-500" />}
          />
          <StatCard
            title="Active Batches"
            value="1"
            icon={<Droplets className="w-5 h-5 text-emerald-500" />}
          />
        </div>

        {/* Glassmorphism Section */}
        <section className="relative overflow-hidden rounded-3xl bg-secondary/30 backdrop-blur-xl border border-white/10 p-8 shadow-2xl">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent pointer-events-none" />
          <h2 className="text-2xl font-semibold mb-4 relative z-10">Active Fermentation</h2>
          <div className="h-64 flex items-center justify-center text-muted-foreground bg-black/5 rounded-xl border border-black/5">
            Placeholder for D3/Recharts Visualization
          </div>
        </section>
      </div>
    </main>
  );
}

function StatCard({ title, value, icon }: { title: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="group relative overflow-hidden rounded-2xl bg-card p-6 shadow-md border border-border/50 hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        <div className="p-2 rounded-full bg-secondary/80 text-secondary-foreground">
          {icon}
        </div>
      </div>
      <div className="text-3xl font-bold tracking-tight">{value}</div>
      <div className="absolute bottom-0 left-0 h-1 w-full bg-gradient-to-r from-primary/0 via-primary/20 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );
}
