const withPWA = require('next-pwa')({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  skipWaiting: true,
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  env: {
    NEXT_PUBLIC_GRAFANA_URL: process.env.NEXT_PUBLIC_GRAFANA_URL || '',
  },
  experimental: {
    // This is often needed when using plugins that use webpack with turbopack
    turbo: {},
  },
};

module.exports = withPWA(nextConfig);
