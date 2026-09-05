import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  cacheComponents: true,

  // Bundle optimization (bundling.md)
  transpilePackages: [
    "@base-ui/react",
    "recharts",
    "framer-motion",
  ],
  serverExternalPackages: [],

  // Tree-shake icon libraries more aggressively
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },

  async rewrites() {
    const apiTarget = process.env.API_URL || "http://localhost:8000/api/v1";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
