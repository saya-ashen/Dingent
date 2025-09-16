import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  basePath: "/admin",
  output: "export",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
