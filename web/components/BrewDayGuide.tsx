'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { BookOpen, X, Info, ChevronRight, CheckCircle2, FlaskConical, Wifi, Calendar } from 'lucide-react';
import { DataChecklist } from './DataChecklist';

interface BrewDayGuideProps {
    isOpen: boolean;
    onClose: () => void;
}

export function BrewDayGuide({ isOpen, onClose }: BrewDayGuideProps) {
    const [activeTab, setActiveTab] = useState<'checklist' | 'guide'>('checklist');

    return (
        <div className={cn(
            "fixed inset-0 z-50 transition-all duration-500",
            isOpen ? "visible" : "invisible"
        )}>
            {/* Backdrop */}
            <div
                className={cn("absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-500",
                    isOpen ? "opacity-100" : "opacity-0"
                )}
                onClick={onClose}
            />

            {/* Sidebar */}
            <div className={cn(
                "absolute top-0 right-0 h-full w-full max-w-xl bg-zinc-950 border-l border-white/10 shadow-2xl transition-transform duration-500 transform flex flex-col",
                isOpen ? "translate-x-0" : "translate-x-full"
            )}>
                {/* Header */}
                <header className="p-6 border-b border-white/5 flex items-center justify-between bg-zinc-900/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-primary/10 text-primary">
                            <BookOpen className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Brew Day Command</h2>
                            <p className="text-xs text-zinc-500">Autonomous Fermentation Setup Guide</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-full hover:bg-zinc-800 transition-colors text-zinc-400 hover:text-white"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </header>

                {/* Tabs */}
                <div className="flex border-b border-white/5 bg-zinc-950/50">
                    <TabButton
                        active={activeTab === 'checklist'}
                        onClick={() => setActiveTab('checklist')}
                        label="Checks & Balances"
                    />
                    <TabButton
                        active={activeTab === 'guide'}
                        onClick={() => setActiveTab('guide')}
                        label="Full Protocol"
                    />
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar text-zinc-300">
                    {activeTab === 'checklist' ? (
                        <div className="space-y-8">
                            <section>
                                <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-widest mb-4">Verification Status</h3>
                                <DataChecklist />
                            </section>

                            <section className="bg-blue-500/5 border border-blue-500/10 rounded-2xl p-6">
                                <div className="flex gap-4">
                                    <Info className="w-5 h-5 text-blue-400 shrink-0" />
                                    <div className="space-y-2">
                                        <p className="text-sm font-semibold text-blue-100 italic">Why this matters?</p>
                                        <p className="text-xs text-blue-200/70 leading-relaxed">
                                            The Brew-Brain AI architecture relies on accurate metadata (OG, Yeast, Style) to build its initial prediction manifold. Sensor health ensures the drift-correction algorithms stay synced.
                                        </p>
                                    </div>
                                </div>
                            </section>
                        </div>
                    ) : (
                        <div className="space-y-10 pb-10">
                            <GuideSection title="1. Brewfather Setup" icon={<FlaskConical className="w-4 h-4 text-emerald-400" />}>
                                <GuideItem text="Set Recipe Style to a valid BJCP category for Style Intelligence." />
                                <GuideItem text="Ensure Target OG is logged correctly in the recipe." />
                                <GuideItem text="Log Yeast Strain - AI uses this for attenuation expectations." />
                                <GuideItem text="Move batch status to 'Fermenting' to trigger sync." />
                            </GuideSection>

                            <GuideSection title="2. Device Integration" icon={<Wifi className="w-4 h-4 text-primary" />}>
                                <GuideItem text="Check Tilt/iSpindel Battery status." />
                                <GuideItem text="Verify Stream URL in your monitoring app." />
                                <GuideItem text="Confirm signal reach - distance and stainless steel can block Bluetooth." />
                            </GuideSection>

                            <GuideSection title="3. AI Preparation" icon={<Calendar className="w-4 h-4 text-amber-400" />}>
                                <GuideItem text="Wait 12-24 hours for enough data points to calibrate the ML model." />
                                <GuideItem text="Log measured OG in settings if it differs from recipe target." />
                                <GuideItem text="Regularly export batches to Parquet to improve local training." />
                            </GuideSection>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function TabButton({ active, onClick, label }: { active: boolean, onClick: () => void, label: string }) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "flex-1 py-4 text-xs font-bold uppercase tracking-widest transition-all relative",
                active ? "text-primary" : "text-zinc-500 hover:text-zinc-300"
            )}
        >
            {label}
            {active && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary shadow-[0_0_10px_rgba(var(--primary),0.5)]" />}
        </button>
    );
}

function GuideSection({ title, children, icon }: { title: string, children: React.ReactNode, icon: React.ReactNode }) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
                <div className="p-1 px-2 rounded-lg bg-zinc-900 border border-white/5">
                    {icon}
                </div>
                <h4 className="font-bold text-zinc-100">{title}</h4>
            </div>
            <div className="space-y-3">
                {children}
            </div>
        </div>
    );
}

function GuideItem({ text }: { text: string }) {
    return (
        <div className="flex gap-3 group">
            <div className="mt-1">
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-700 group-hover:bg-primary transition-colors" />
            </div>
            <p className="text-xs text-zinc-400 group-hover:text-zinc-200 transition-colors leading-relaxed">
                {text}
            </p>
        </div>
    );
}
