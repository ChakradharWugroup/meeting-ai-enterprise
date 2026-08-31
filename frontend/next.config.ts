import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['623786933810a9.lhr.life', '100.86.17.36', '192.168.1.105', 'unsubtle-bright-astute.ngrok-free.dev', 'ai-transcribe.loca.lt', 'meeting-ai-transcriber.loca.lt', 'kalle-ai-transcriber.loca.lt', 'ai-transcribe-ignition.ngrok-free.dev', 'abridge-ship-city.ngrok-free.dev', 'shortage-lantern-bring.ngrok-free.dev'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8081/:path*',
      },
    ];
  },
};

export default nextConfig;
