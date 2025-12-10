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
};

export default nextConfig;
