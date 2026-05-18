"use client";

import { useState } from "react";
import useSWR from "swr";
import toast from "react-hot-toast";
import { Search, Calculator, Bot, ShoppingCart, RefreshCw, BarChart3, TestTube } from "lucide-react";
import { motion } from "framer-motion";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Automation() {
  const [activeTab, setActiveTab] = useState<"inventory" | "sourcing" | "simulation">("inventory");

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <h1 className="text-4xl font-black tracking-tight mb-2">Automation & AI</h1>
          <p className="text-muted-foreground">Manage inventory sync, deficit sourcing, and predictive R&D models.</p>
        </div>
        
        {/* Tab Navigation */}
        <div className="flex p-1 bg-secondary/50 rounded-xl w-full md:w-auto overflow-x-auto">
          {[
            { id: "inventory", label: "Inventory Sync", icon: RefreshCw },
            { id: "sourcing", label: "Sourcing Agent", icon: ShoppingCart },
            { id: "simulation", label: "Monte Carlo R&D", icon: TestTube }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all whitespace-nowrap ${
                activeTab === tab.id 
                  ? "bg-background text-foreground shadow-sm" 
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8">
        {activeTab === "inventory" && <InventoryTab />}
        {activeTab === "sourcing" && <SourcingTab />}
        {activeTab === "simulation" && <SimulationTab />}
      </div>

    </div>
  );
}

// --- SUB-COMPONENTS ---

function InventoryTab() {
  const { data, error, isLoading, mutate } = useSWR("/api/automation/inventory", fetcher);
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await fetch("/api/automation/inventory/sync", { method: "POST" });
      const resData = await res.json();
      if (resData.status === "success") {
        toast.success("Brewfather inventory synced!");
        mutate();
      } else {
        toast.error(resData.error || "Sync failed");
      }
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSyncing(false);
    }
  };

  if (isLoading) return <div className="p-8 text-center animate-pulse">Loading Inventory...</div>;
  if (error) return <div className="p-8 text-center text-destructive">Failed to load inventory</div>;

  const inventory = data?.data?.inventory || {};
  const items = [
    ...(inventory.fermentables || []),
    ...(inventory.hops || []),
    ...(inventory.yeasts || []),
    ...(inventory.miscs || [])
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button 
          onClick={handleSync} 
          disabled={syncing}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg font-semibold shadow-sm hover:bg-primary/90 disabled:opacity-50 transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
          Force Sync
        </button>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-secondary/30 border-b border-border/50">
              <tr>
                <th className="px-6 py-4">Item Name</th>
                <th className="px-6 py-4">Type</th>
                <th className="px-6 py-4 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item: any, i: number) => (
                <tr key={i} className="border-b border-border/50 hover:bg-secondary/20 transition-colors">
                  <td className="px-6 py-4 font-semibold">{item.name}</td>
                  <td className="px-6 py-4 text-muted-foreground capitalize">{item._type || 'Unknown'}</td>
                  <td className="px-6 py-4 text-right font-mono text-primary">
                    {item.amount?.toFixed(2) || "0"} {item._type === 'hops' ? 'g' : (item._type === 'fermentables' ? 'kg' : 'pkg')}
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-6 py-8 text-center text-muted-foreground">No inventory data found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function SourcingTab() {
  const [recipeId, setRecipeId] = useState("");
  const [sourcing, setSourcing] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipeId) return;
    
    setSourcing(true);
    setResult(null);
    try {
      // 1. Parse Recipe Deficit
      const parseRes = await fetch("/api/automation/recipe/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: "brewfather", recipe_data: recipeId })
      });
      const parseData = await parseRes.json();
      
      if (parseData.status === "error") throw new Error(parseData.error);
      
      const deficit = parseData.data.deficit;
      
      // 2. Source Deficit
      const sourceRes = await fetch("/api/automation/source", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deficit })
      });
      const sourceData = await sourceRes.json();
      
      if (sourceData.status === "error") throw new Error(sourceData.error);
      
      setResult({
        deficit,
        cart: sourceData.data.best_cart
      });
      toast.success("Sourcing complete!");
      
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSourcing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2"><Search className="text-primary"/> Source Recipe Deficits</h2>
        <form onSubmit={handleSource} className="flex gap-4">
          <input 
            type="text" 
            placeholder="Enter Brewfather Recipe ID" 
            value={recipeId}
            onChange={(e) => setRecipeId(e.target.value)}
            className="flex-1 bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary outline-none"
            required
          />
          <button 
            type="submit" 
            disabled={sourcing}
            className="bg-primary text-primary-foreground px-6 py-3 rounded-xl font-semibold hover:bg-primary/90 disabled:opacity-50 transition-all shadow-sm"
          >
            {sourcing ? "Scouting Vendors..." : "Source Ingredients"}
          </button>
        </form>
      </div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <h3 className="text-lg font-bold mb-4">Calculated Deficit</h3>
            <ul className="space-y-3">
              {result.deficit.fermentables.map((f: any, i: number) => (
                <li key={i} className="flex justify-between text-sm border-b border-border/30 pb-2"><span className="text-muted-foreground">{f.name}</span> <span className="font-mono text-primary font-bold">{f.amount.toFixed(2)} kg</span></li>
              ))}
              {result.deficit.hops.map((h: any, i: number) => (
                <li key={i} className="flex justify-between text-sm border-b border-border/30 pb-2"><span className="text-muted-foreground">{h.name}</span> <span className="font-mono text-primary font-bold">{h.amount.toFixed(0)} g</span></li>
              ))}
              {result.deficit.yeasts.map((y: any, i: number) => (
                <li key={i} className="flex justify-between text-sm border-b border-border/30 pb-2"><span className="text-muted-foreground">{y.name}</span> <span className="font-mono text-primary font-bold">{y.amount} pkg</span></li>
              ))}
            </ul>
          </div>
          
          <div className="glass-card p-6 border-2 border-emerald-500/20 bg-emerald-500/5">
            <h3 className="text-lg font-bold mb-4 text-emerald-600 dark:text-emerald-400">Optimized Cart</h3>
            <div className="space-y-4">
               {Object.entries(result.cart || {}).map(([vendor, items]: [string, any]) => {
                 if (vendor === "total_cost") return null;
                 return (
                   <div key={vendor}>
                     <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">{vendor}</div>
                     <ul className="space-y-2">
                       {items.map((item: any, i: number) => (
                         <li key={i} className="flex justify-between text-sm"><span className="truncate pr-4">{item.name}</span> <span className="font-mono text-emerald-600 dark:text-emerald-400">£{item.price}</span></li>
                       ))}
                     </ul>
                   </div>
                 );
               })}
               <div className="mt-6 pt-4 border-t border-emerald-500/20 flex justify-between items-center">
                 <span className="font-bold">Total Estimated Cost</span>
                 <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">£{result.cart?.total_cost?.toFixed(2) || "0.00"}</span>
               </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}

function SimulationTab() {
  const [formData, setFormData] = useState({ target_og: "1.055", yeast: "US-05", mash_temp_c: "65" });
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    setResult(null);
    try {
      const res = await fetch("/api/automation/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });
      const data = await res.json();
      
      if (data.status === "error") throw new Error(data.error);
      
      const taskId = data.data.task_id;
      
      // Poll for result
      const poll = setInterval(async () => {
        const statusRes = await fetch(`/api/automation/simulate/status/${taskId}`);
        const statusData = await statusRes.json();
        
        if (statusData.data?.status === "success" || statusData.data?.mean_fg) {
          clearInterval(poll);
          setResult(statusData.data);
          setSimulating(false);
          toast.success("Simulation complete!");
        } else if (statusData.status === "error") {
          clearInterval(poll);
          toast.error("Simulation failed");
          setSimulating(false);
        }
      }, 2000);
      
    } catch (err: any) {
      toast.error(err.message);
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-6">
       <div className="glass-card p-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2"><TestTube className="text-primary"/> Dry Run (Monte Carlo R&D)</h2>
        <form onSubmit={handleSimulate} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div className="space-y-2">
             <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Target OG</label>
             <input type="number" step="0.001" value={formData.target_og} onChange={e => setFormData({...formData, target_og: e.target.value})} className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2" required />
          </div>
          <div className="space-y-2">
             <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Yeast Strain</label>
             <input type="text" value={formData.yeast} onChange={e => setFormData({...formData, yeast: e.target.value})} className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2" required />
          </div>
          <div className="space-y-2">
             <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Mash Temp (°C)</label>
             <input type="number" step="0.1" value={formData.mash_temp_c} onChange={e => setFormData({...formData, mash_temp_c: e.target.value})} className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2" required />
          </div>
          <button 
            type="submit" 
            disabled={simulating}
            className="bg-primary text-primary-foreground h-[42px] rounded-xl font-semibold hover:bg-primary/90 disabled:opacity-50 transition-all shadow-sm"
          >
            {simulating ? "Simulating..." : "Run Simulation"}
          </button>
        </form>
      </div>

      {result && (
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="glass-card p-8 bg-primary/5 border-primary/20">
           <div className="text-center space-y-2 mb-8">
             <div className="text-sm font-bold text-primary uppercase tracking-widest">Prediction Results</div>
             <div className="text-5xl font-black">{result.mean_fg?.toFixed(3)}</div>
             <div className="text-muted-foreground font-medium">Estimated Final Gravity</div>
           </div>
           
           <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
             <div className="p-4 bg-background rounded-2xl border border-border shadow-sm">
                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Confidence Interval</div>
                <div className="text-xl font-bold font-mono">{result.confidence_interval?.[0]?.toFixed(3)} - {result.confidence_interval?.[1]?.toFixed(3)}</div>
             </div>
             <div className="p-4 bg-background rounded-2xl border border-border shadow-sm">
                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Iterations</div>
                <div className="text-xl font-bold font-mono">{result.iterations}</div>
             </div>
             <div className="p-4 bg-background rounded-2xl border border-border shadow-sm">
                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Stall Risk ({">"}1.018)</div>
                <div className="text-xl font-bold font-mono text-amber-500">{(result.risk_of_stall_pct * 100).toFixed(1)}%</div>
             </div>
           </div>
        </motion.div>
      )}
    </div>
  );
}
