import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
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
};

export default nextConfig;
