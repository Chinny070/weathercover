import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* WeatherCover frontend -- frontend only, no server infrastructure of our
   * own. All data comes from the deployed WeatherResolveCover Intelligent
   * Contract via genlayer-js, read directly in the browser -- never from an
   * API route or database we host. */
};

export default nextConfig;
