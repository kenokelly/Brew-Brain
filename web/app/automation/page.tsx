"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Scout } from "@/components/automation/Scout";
import { Water } from "@/components/automation/Water";
import { IBUCalculator } from "@/components/automation/Calculator";
import { Recipes } from "@/components/automation/Recipes";
import { Inventory } from "@/components/automation/Inventory";
import { Pipeline } from "@/components/automation/Pipeline";
import { Simulation } from "@/components/automation/Simulation";
import { Sourcing } from "@/components/automation/Sourcing";
import { Yeast } from "@/components/automation/Yeast";
import { PriceComparator } from "@/components/automation/PriceComparator";
import { Search, Droplets, Calculator, FlaskConical, FileText, Package, Network, ShoppingCart, Scale, TestTube } from "lucide-react";
import { motion } from "framer-motion";

const TABS = [
    { id: "water", label: "Water Profile", icon: Droplets, component: Water, group: "Recipe Tools" },
    { id: "calc", label: "Calculators", icon: Calculator, component: IBUCalculator, group: "Recipe Tools" },
    { id: "yeast", label: "Yeast", icon: FlaskConical, component: Yeast, group: "Recipe Tools" },
    { id: "recipes", label: "Recipe Finder", icon: FileText, component: Recipes, group: "Recipe Tools" },
    { id: "scout", label: "Ingredient Scout", icon: Search, component: Scout, group: "Sourcing & Inventory" },
    { id: "sourcing", label: "Sourcing", icon: ShoppingCart, component: Sourcing, group: "Sourcing & Inventory" },
    { id: "price", label: "Price Comparator", icon: Scale, component: PriceComparator, group: "Sourcing & Inventory" },
    { id: "inventory", label: "Inventory", icon: Package, component: Inventory, group: "Sourcing & Inventory" },
    { id: "pipeline", label: "R&D Pipeline", icon: Network, component: Pipeline, group: "R&D" },
    { id: "sim", label: "Brew Simulator", icon: TestTube, component: Simulation, group: "R&D" },
];

export default function AutomationPage() {
    const [activeTab, setActiveTab] = useState("water");

    const ActiveComponent = TABS.find((t) => t.id === activeTab)?.component || Scout;

    return (
        <div className="max-w-6xl mx-auto p-4 md:p-8 h-[calc(100vh-4rem)] flex flex-col animate-in fade-in duration-500">
            <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-4xl font-black tracking-tight mb-2">
                        Automation & AI
                    </h1>
                    <p className="text-muted-foreground">Manage inventory sync, deficit sourcing, and predictive R&D models.</p>
                </div>
            </header>

            <div className="flex-1 flex flex-col lg:flex-row gap-8 min-h-0">
                {/* Sidebar Navigation for Tabs */}
                <nav className="w-full lg:w-64 flex flex-row lg:flex-col gap-2 overflow-x-auto lg:overflow-visible pb-2 lg:pb-0 shrink-0">
                    {TABS.map((tab, i) => (
                        <div key={tab.id} className="contents lg:block">
                            {tab.group !== TABS[i - 1]?.group && (
                                <div className="hidden lg:block px-4 pt-4 pb-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 first:pt-0">
                                    {tab.group}
                                </div>
                            )}
                            <button
                                onClick={() => setActiveTab(tab.id)}
                                className={cn(
                                    "flex items-center gap-3 px-4 py-3 rounded-xl transition-all whitespace-nowrap lg:whitespace-normal text-left font-medium w-full",
                                    activeTab === tab.id
                                        ? "bg-primary text-primary-foreground shadow-sm"
                                        : "hover:bg-secondary/50 text-muted-foreground hover:text-foreground"
                                )}
                            >
                                <tab.icon className="w-5 h-5 shrink-0" />
                                {tab.label}
                            </button>
                        </div>
                    ))}
                </nav>

                {/* Main Content Area */}
                <div className="flex-1 overflow-y-auto min-h-0 pb-16 lg:pb-0">
                    <ActiveComponent />
                </div>
            </div>
        </div>
    );
}
