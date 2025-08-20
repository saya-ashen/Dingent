/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    '@ant-design',
    'antd'
  ],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:2024/:path*'
      }
    ];
  }
};

module.exports = nextConfig;