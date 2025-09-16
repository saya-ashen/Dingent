import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    /* config options here */
    images: {
        unoptimized: true, // 关闭内置优化
    },
    output: 'standalone',
};

export default nextConfig;
