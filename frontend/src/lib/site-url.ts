const siteBase = (process.env.APP_PUBLIC_URL ?? "http://localhost:3000").replace(/\/$/, "");

/** Builds an absolute URL under the public site origin, for canonical links, sitemaps, and robots.txt. */
export function siteUrl(path = "/"): string {
  if (path === "/") {
    return siteBase;
  }
  return `${siteBase}${path.startsWith("/") ? path : `/${path}`}`;
}
