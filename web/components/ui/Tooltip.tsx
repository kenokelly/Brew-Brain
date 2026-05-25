'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface TooltipProps {
    children: React.ReactNode;
    content: string;
    position?: 'top' | 'bottom' | 'left' | 'right';
    className?: string;
}

export function Tooltip({ children, content, position = 'top', className = '' }: TooltipProps) {
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
            className={`relative block w-full ${className}`}
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
            onFocus={() => setIsVisible(true)}
            onBlur={() => setIsVisible(false)}
            onClick={() => setIsVisible(!isVisible)}
        >
            {children}
            <AnimatePresence>
                {isVisible && (
                    <motion.div
                        initial={{ opacity: 0, ...initialPositions[position] }}
                        animate={{ opacity: 1, ...positions[position] }}
                        exit={{ opacity: 0, ...initialPositions[position] }}
                        transition={{ duration: 0.15, ease: 'easeOut' }}
                        className="absolute z-[100] px-3 py-2 text-sm font-medium text-white bg-slate-900 border border-slate-700 rounded-lg shadow-xl whitespace-nowrap pointer-events-none"
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
