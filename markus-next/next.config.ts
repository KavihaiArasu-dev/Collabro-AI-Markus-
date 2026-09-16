import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow server-side Node.js APIs in API routes
  serverExternalPackages: ["better-sqlite3", "simple-git"],
  
  // Experimental features
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },

  // Headers for CORS (development)
  async headers() {
    return [
      {
        source: "/api/:path*",
        headers: [
          { key: "Access-Control-Allow-Origin", value: "*" },
          { key: "Access-Control-Allow-Methods", value: "GET,POST,PUT,DELETE,OPTIONS" },
          { key: "Access-Control-Allow-Headers", value: "Content-Type, Authorization" },
        ],
      },
    ];
  },
};

export default nextConfig;
