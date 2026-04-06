/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'

const nextConfig = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'ngrok-skip-browser-warning', value: 'true' },
        ],
      },
    ]
  },
  async rewrites() {
    return [
      {
        source: '/backend/:path*',
        destination: `${backendUrl}/:path*`,
      },
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
