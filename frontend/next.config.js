/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: [],
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
