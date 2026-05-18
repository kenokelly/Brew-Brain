"use client";

import useSWR from "swr";
import { useState } from "react";
import toast from "react-hot-toast";
import { Save, Server, Bell, Cpu, ArrowLeftRight } from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Settings() {
  const { data, error, isLoading, mutate } = useSWR("/api/settings", fetcher);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<any>({});

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const response = await fetch("/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      
      const resData = await response.json();
      if (resData.status === "updated") {
        toast.success("Settings saved atomically.");
        mutate(); // refresh data
      } else {
        toast.error(resData.error || "Failed to save settings");
      }
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading Configuration...</div>;
  if (error) return <div className="p-8 text-center text-destructive">Failed to load configuration.</div>;

  const config = { ...data?.data, ...formData };

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-4xl font-black tracking-tight mb-2">System Configuration</h1>
          <p className="text-muted-foreground">Manage API keys, thresholds, and environment variables.</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center justify-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-3 rounded-full font-semibold transition-all shadow-sm disabled:opacity-50"
        >
          <Save className="w-5 h-5" />
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        
        {/* API Integrations Card */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6 border-b border-border/50 pb-4">
            <div className="p-2 bg-blue-500/10 rounded-xl text-blue-500">
              <ArrowLeftRight className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold tracking-tight">API Integrations</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Brewfather User ID</label>
              <input 
                name="bf_user" 
                value={config.bf_user || ""} 
                onChange={handleInputChange} 
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Brewfather API Key</label>
              <input 
                name="bf_key" 
                type="password"
                value={config.bf_key || ""} 
                onChange={handleInputChange} 
                placeholder="********"
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">SerpApi Key (Sourcing)</label>
              <input 
                name="serp_api_key" 
                type="password"
                value={config.serp_api_key || ""} 
                onChange={handleInputChange} 
                placeholder="********"
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
              />
            </div>
          </div>
        </div>

        {/* Telegram Alerts Card */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6 border-b border-border/50 pb-4">
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-500">
              <Bell className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold tracking-tight">Telegram Alerts</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Bot Token</label>
              <input 
                name="alert_telegram_token" 
                type="password"
                value={config.alert_telegram_token || ""} 
                onChange={handleInputChange} 
                placeholder="********"
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Chat ID</label>
              <input 
                name="alert_telegram_chat" 
                value={config.alert_telegram_chat || ""} 
                onChange={handleInputChange} 
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-2 text-foreground focus:ring-2 focus:ring-primary outline-none transition-all" 
              />
            </div>
          </div>
        </div>

      </form>
    </div>
  );
}
