'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface TooltipProps {
    children: React.ReactNode;
    content: string;
    position?: 'top' | 'bottom' | 'left' | 'right';
}

export function Tooltip({ children, content, position = 'top' }: TooltipProps) {
    const [isVisible, setIsVisible] = useState(false);

    const positions = {
        top: { y: -10, x: '-50%', top: '-100%', left: '50%' },
        bottom: { y: 10, x: '-50%', bottom: '-100%', left: '50%' },
        left: { x: -10, y: '-50%', top: '50%', right: '100%' },
        right: { x: 10, y: '-50%', top: '50%', left: '100%' }
    };

    const initialPositions = {
        top: { y: 5, x: '-50%' },
        bottom: { y: -5, x: '-50%' },
        left: { x: 5, y: '-50%' },
        right: { x: -5, y: '-50%' }
    };

    return (
        <div 
            className="relative inline-flex items-center justify-center"
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
            onFocus={() => setIsVisible(true)}
            onBlur={() => setIsVisible(false)}
        >
            {children}
            <AnimatePresence>
                {isVisible && (
                    <motion.div
                        initial={{ opacity: 0, ...initialPositions[position] }}
                        animate={{ opacity: 1, ...positions[position] }}
                        exit={{ opacity: 0, ...initialPositions[position] }}
                        transition={{ duration: 0.15, ease: 'easeOut' }}
                        className="absolute z-50 px-3 py-1.5 text-xs font-medium text-white bg-slate-800/90 backdrop-blur-md rounded-lg shadow-xl border border-white/10 whitespace-nowrap pointer-events-none"
                        style={{
                            [position === 'top' ? 'bottom' : position === 'bottom' ? 'top' : position]: '100%',
                            [position === 'top' || position === 'bottom' ? 'left' : 'top']: '50%',
                            margin: position === 'top' ? '0 0 8px 0' : position === 'bottom' ? '8px 0 0 0' : position === 'left' ? '0 8px 0 0' : '0 0 0 8px'
                        }}
                    >
                        {content}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
