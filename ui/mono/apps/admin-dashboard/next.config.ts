import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  basePath: "/admin",
  output: "export",
  images: {
    unoptimized: true,
  },
  transpilePackages: ["@repo/ui", "@repo/config", "@repo/assets", "@repo/hooks", "@repo/lib"],
};

export default nextConfig;
