'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Sparkles, RefreshCcw, ChevronRight, MessageSquare, Lightbulb, Loader2 } from 'lucide-react';
import { fetcher } from '@/lib/hooks';

interface AdviceData {
    status: 'success' | 'fallback' | 'error';
    advice: string;
    source?: string;
}

export function AdviceWidget({ className }: { className?: string }) {
    const [advice, setAdvice] = useState<AdviceData | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const fetchAdvice = async () => {
        setIsLoading(true);
        try {
            const json = await fetcher<{ status: string; data: AdviceData }>('/api/ai/advice');
            if (json.status === 'success') {
                setAdvice(json.data);
            }
        } catch (error) {
            console.error('Failed to fetch AI advice:', error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchAdvice();
    }, []);

    if (isLoading && !advice) {
        return (
            <div className={cn(
                "rounded-2xl bg-purple-600/5 border border-purple-500/20 p-6 flex flex-col items-center justify-center min-h-[200px] animate-pulse",
                className
            )}>
                <Loader2 className="w-8 h-8 text-purple-500 animate-spin mb-4" />
                <div className="h-4 bg-purple-500/10 rounded w-32" />
            </div>
        );
    }

    if (!advice) return null;

    return (
        <div className={cn(
            "group relative overflow-hidden rounded-2xl p-6 shadow-md border transition-all duration-300",
            "bg-card/50 backdrop-blur-md border-purple-500/20 hover:border-purple-500/40",
            className
        )}>
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-purple-600/10 text-purple-500">
                        <Sparkles className="w-4 h-4" />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-purple-500">Proactive Advice</h3>
                        <div className="flex items-center gap-1">
                            <span className="text-[10px] text-muted-foreground">Brewmaster Intelligence</span>
                            {advice.source === 'ollama' && (
                                <span className="text-[9px] bg-purple-500/10 text-purple-500 px-1.5 py-0.5 rounded-full font-bold">EDGE</span>
                            )}
                        </div>
                    </div>
                </div>
                <button 
                    onClick={fetchAdvice}
                    disabled={isLoading}
                    className="p-2 rounded-full hover:bg-purple-500/10 text-purple-500 transition-colors disabled:opacity-50"
                >
                    <RefreshCcw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                </button>
            </div>

            {/* Content */}
            <div className="relative z-10">
                <div className="flex gap-3">
                    <div className="shrink-0 mt-1">
                        <Lightbulb className="w-5 h-5 text-amber-400" />
                    </div>
                    <div className="space-y-3">
                        <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
                            {advice.advice}
                        </p>
                        <div className="flex items-center gap-4 pt-2">
                            <button className="text-[10px] font-bold text-purple-400 hover:text-purple-300 flex items-center gap-1 transition-colors uppercase tracking-tight">
                                <MessageSquare className="w-3 h-3" /> Ask Detail
                            </button>
                            <button className="text-[10px] font-bold text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors uppercase tracking-tight">
                                Learn More <ChevronRight className="w-3 h-3" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Background Decoration */}
            <div className="absolute -bottom-6 -right-6 opacity-[0.03] group-hover:opacity-[0.07] transition-opacity">
                <Sparkles className="w-32 h-32 text-purple-500" />
            </div>
        </div>
    );
}

export default AdviceWidget;
