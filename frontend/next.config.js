/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "img.a.transfermarkt.technology"
      }
    ]
  }
};

module.exports = nextConfig;
