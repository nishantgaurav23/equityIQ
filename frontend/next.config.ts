import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  ...(isProd
    ? {
        output: "export",   // static export for GCP deployment only
        distDir: "out",
      }
    : {
        async rewrites() {
          return [
            {
              source: "/api/proxy/:path*",
              destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*`,
            },
          ];
        },
      }),
};

export default nextConfig;