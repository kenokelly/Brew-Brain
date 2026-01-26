'use client';

import { useState, useEffect } from 'react';

export function GrafanaChart({ timeRange }: { timeRange: string }) {
    const [host, setHost] = useState('');

    useEffect(() => {
        if (typeof window !== 'undefined') {
            setHost(window.location.hostname);
        }
    }, []);

    if (!host) return <div className="w-full h-full bg-muted/10 animate-pulse" />;

    return (
        <iframe
            src={`http://${host}:3000/d-solo/fermentation-dashboard/brew-brain-production?orgId=1&panelId=2&theme=dark&from=${timeRange}&to=now`}
            className="w-full h-full border-none"
            title="Grafana Chart"
        />
    );
}
