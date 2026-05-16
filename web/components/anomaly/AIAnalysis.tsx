'use client';

import { Sparkles } from 'lucide-react';

interface AIAnalysisProps {
    analysis: string;
    source?: string;
}

export function AIAnalysis({ analysis, source }: AIAnalysisProps) {
    return (
        <div className="mb-6 animate-in fade-in slide-in-from-top-2 duration-500">
            <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-purple-500" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-purple-500">Brewmaster Analysis</h3>
                {source === 'ollama' && (
                    <span className="text-[10px] bg-purple-500/10 text-purple-500 px-2 py-0.5 rounded-full font-bold">AI</span>
                )}
            </div>
            <div className="p-4 rounded-2xl bg-purple-600/5 border border-purple-500/20 text-sm leading-relaxed whitespace-pre-wrap">
                {analysis}
            </div>
        </div>
    );
}
