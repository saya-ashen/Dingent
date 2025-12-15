import type { NextConfig } from "next";
const path = require("path");

const nextConfig: NextConfig = {
  /* config options here */
  images: {
    unoptimized: true, // 关闭内置优化
  },
  outputFileTracingRoot: path.join(__dirname, "../../"),

  output: "standalone",
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },

  transpilePackages: ["@repo/ui", "@repo/lib"],
};

export default nextConfig;
