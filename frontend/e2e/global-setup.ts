import { execFileSync } from "node:child_process";
import path from "node:path";

/**
 * Tests sign in many accounts from one IP, which quickly reaches the API limit of
 * 10 /auth requests per minute (now shared through Redis). Clearing the counters
 * keeps local runs repeatable without weakening the limit in the application.
 */
export function resetRateLimits(): void {
  if (process.env.E2E_SKIP_RATE_LIMIT_RESET) return;
  execFileSync(
    "docker",
    ["compose", "exec", "-T", "redis", "sh", "-c",
      "redis-cli --scan --pattern 'ratelimit:*' | xargs -r redis-cli del"],
    { cwd: path.resolve(__dirname, "..", ".."), stdio: "pipe" },
  );
}

export default resetRateLimits;
