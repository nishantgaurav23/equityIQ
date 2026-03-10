import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  output: "export",        // ← always export (removes conditional)
  distDir: "out",          // ← explicitly set output dir
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