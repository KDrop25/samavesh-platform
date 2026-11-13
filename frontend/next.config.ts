import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false, // the dev badge sits on top of form buttons
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
