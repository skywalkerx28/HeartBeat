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
    const raw = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').trim()
    const isLocal = /localhost|127\.0\.0\.1/.test(raw)
    // Normalize scheme for non-local targets
    let base = (isLocal ? raw : raw.replace(/^http:\/\//, 'https://')).replace(/\/+$/, '')
    // Guard against malformed values (e.g., 'https:' or 'https:/domain')
    if (!/^https?:\/\/[^/]+/i.test(base)) {
      console.warn(`Invalid NEXT_PUBLIC_API_BASE_URL='${raw}' - defaulting to http://localhost:8000`)
      base = 'http://localhost:8000'
    }
    return [
      {
        source: '/api/:path*',
        destination: `${base}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
