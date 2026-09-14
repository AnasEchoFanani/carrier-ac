import type { NextConfig } from "next"

const apiOrigin = process.env.CARRIER_AC_API ?? "http://127.0.0.1:43148"

const nextConfig: NextConfig = {
  agentRules: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
