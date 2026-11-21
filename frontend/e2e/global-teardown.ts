import { execFileSync } from "node:child_process";
import path from "node:path";

/**
 * E2E runs create accounts (e2e-*@example.com), categories ("E2E …") and a draft recipe.
 * Re-running the seed removes them so only the real dataset stays in the database.
 */
export default function globalTeardown(): void {
  if (process.env.E2E_KEEP_TEST_DATA) return;
  execFileSync("docker", ["compose", "exec", "-T", "api", "seed"], {
    cwd: path.resolve(__dirname, "..", ".."),
    stdio: "pipe",
  });
}
