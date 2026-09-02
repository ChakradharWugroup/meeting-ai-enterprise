import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow the cloud server IP
  allowedDevOrigins: ['141.147.165.228'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // In Docker, the api container is reachable by its service name
        destination: 'http://meeting_ai_api:8000/:path*',
      },
    ];
  },
};

export default nextConfig;
