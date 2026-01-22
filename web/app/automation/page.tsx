'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Scout } from '@/components/automation/Scout';
import { Search, Droplets, Calculator, FlaskConical, Network, ShoppingCart } from 'lucide-react';

const TABS = [
    { id: 'scout', label: 'Ingredient Scout', icon: Search, component: Scout },
    { id: 'water', label: 'Water Profile', icon: Droplets, component: () => <div className="p-8 text-center text-muted-foreground">Water Profile Coming Soon (Native)</div> },
    { id: 'calc', label: 'Calculators', icon: Calculator, component: () => <div className="p-8 text-center text-muted-foreground">Calculators Coming Soon (Native)</div> },
    { id: 'yeast', label: 'Yeast', icon: FlaskConical, component: () => <div className="p-8 text-center text-muted-foreground">Yeast Tools Coming Soon (Native)</div> },
];

export default function AutomationPage() {
    const [activeTab, setActiveTab] = useState('scout');

    const ActiveComponent = TABS.find(t => t.id === activeTab)?.component || Scout;

    return (
        <div className="max-w-7xl mx-auto p-8 h-[calc(100vh-4rem)] flex flex-col">
            <header className="mb-8">
                <h1 className="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500">
                    Automation Lab
                </h1>
                <p className="text-muted-foreground mt-1">AI-Assisted tools for precision brewing.</p>
            </header>

            <div className="flex-1 flex flex-col lg:flex-row gap-8 min-h-0">
                {/* Sidebar Navigation for Tabs */}
                <nav className="w-full lg:w-64 flex flex-row lg:flex-col gap-2 overflow-x-auto lg:overflow-visible pb-2 lg:pb-0 shrink-0">
                    {TABS.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={cn(
                                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all whitespace-nowrap lg:whitespace-normal text-left",
                                activeTab === tab.id
                                    ? "bg-primary/10 text-primary font-medium border border-primary/20 shadow-sm"
                                    : "hover:bg-secondary/30 text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <tab.icon className="w-5 h-5 shrink-0" />
                            {tab.label}
                        </button>
                    ))}
                </nav>

                {/* Main Content Area */}
                <div className="flex-1 overflow-y-auto bg-card/30 backdrop-blur-md border border-border/50 rounded-3xl p-6 shadow-xl">
                    <ActiveComponent />
                </div>
            </div>
        </div>
    );
}
