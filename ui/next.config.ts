import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || undefined,
  assetPrefix: process.env.NEXT_PUBLIC_BASE_PATH || undefined,

  output: "standalone",
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}${basePath}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
