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
    const raw = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    const isLocal = /localhost|127\.0\.0\.1/.test(raw)
    // Force https for non-local targets to avoid CORS preflight redirects
    const normalized = (isLocal ? raw : raw.replace(/^http:\/\//, 'https://')).replace(/\/+$/, '')

    return [
      {
        source: '/api/:path*',
        destination: `${normalized}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
