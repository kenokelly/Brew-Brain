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

    // Prefer an explicitly configured Grafana URL (e.g. a different host/port,
    // or an externally-hosted Grafana); fall back to the same-host default
    // port Grafana runs on in the standard docker-compose setup.
    const grafanaBase = process.env.NEXT_PUBLIC_GRAFANA_URL || `http://${host}:3000`;

    return (
        <iframe
            src={`${grafanaBase}/d-solo/fermentation-dashboard/brew-brain-production?orgId=1&panelId=2&theme=dark&from=${timeRange}&to=now`}
            className="w-full h-full border-none"
            title="Grafana Chart"
        />
    );
}
