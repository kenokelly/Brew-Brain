import type { ReactNode } from 'react';

/** The AI writes **bold** markdown; show it as bold rather than raw asterisks. */
export function renderBold(text: string): ReactNode[] {
    return text.split(/\*\*(.+?)\*\*/g).map((part, i) =>
        i % 2 === 1 ? <strong key={i} className="font-semibold">{part}</strong> : part
    );
}
