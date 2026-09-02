import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // F012 D1: standalone output for the containerized deployment.
  output: "standalone",
};

export default nextConfig;
