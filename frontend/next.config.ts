import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  // Static export for single-container GCP deployment
  ...(isProd ? { output: "export" } : {}),
  ...(!isProd
    ? {
        async rewrites() {
          return [
            {
              source: "/api/proxy/:path*",
              destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*`,
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
