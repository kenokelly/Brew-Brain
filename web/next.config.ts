import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ];
  },
  async rewrites() {
    // In Docker, hostname is 'brew-brain', locally set API_HOST=127.0.0.1
    const apiHost = process.env.API_HOST || 'brew-brain';
    return [
      {
        source: '/api/:path*',
        destination: `http://${apiHost}:5000/api/:path*`,
      },
      {
        source: '/static/:path*',
        destination: `http://${apiHost}:5000/static/:path*`,
      },
      {
        source: '/socket.io/:path*',
        destination: `http://${apiHost}:5000/socket.io/:path*`,
      },
    ]
  },
  env: {
    // Expose Grafana URL to client-side code
    NEXT_PUBLIC_GRAFANA_URL: process.env.NEXT_PUBLIC_GRAFANA_URL || '',
  },
};

export default nextConfig;
