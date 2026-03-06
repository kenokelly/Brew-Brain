import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // rewrites are not supported in output: "export".
  // Nginx will handle routing /api and /socket.io requests.
  env: {
    // Expose Grafana URL to client-side code
    NEXT_PUBLIC_GRAFANA_URL: process.env.NEXT_PUBLIC_GRAFANA_URL || '',
  },
};

export default nextConfig;
