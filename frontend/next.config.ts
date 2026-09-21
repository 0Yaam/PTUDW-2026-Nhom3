import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const nextConfig: NextConfig = {
  // Keep `npm run dev` from generating untracked AI instruction files.
  agentRules: false,
};

export default createNextIntlPlugin("./src/i18n/request.ts")(nextConfig);
