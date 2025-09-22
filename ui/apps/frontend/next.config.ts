import type { NextConfig } from "next";
const path = require("path");

const nextConfig: NextConfig = {
  /* config options here */
  images: {
    unoptimized: true, // 关闭内置优化
  },
  outputFileTracingRoot: path.join(__dirname, "../../"),

  output: "standalone",
  transpilePackages: ["@repo/ui", "@repo/lib"],
  async rewrites() {
    return [
      // 访问 /dashboard 或任意子路由时，都回到静态站点的 index.html
      { source: '/dashboard', destination: '/dashboard/index.html' },
      { source: '/dashboard/:path((?!.*\\.).*)', destination: '/dashboard/:path.html' },
      { source: '/dashboard/:path*', destination: '/dashboard/index.html' },
    ];
  },
  async headers() {
    return [
      {
        // 给静态资源长缓存
        source: '/dashboard/:all*(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf)',
        headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }],
      },
    ];
  },
};

export default nextConfig;
