import { apiRequest } from "@/lib/api/client";

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  user: {
    fullName: string;
    roles: string[];
  };
};

export const AUTH_SESSION_KEY = "culinary-blog.auth-session";
export const AUTH_SESSION_CHANGED = "culinary-blog:auth-session-changed";
let refreshPromise: Promise<AuthSession | null> | null = null;

function notifySessionChanged() {
  window.dispatchEvent(new Event(AUTH_SESSION_CHANGED));
}

export function loadAuthSession(): AuthSession | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = window.sessionStorage.getItem(AUTH_SESSION_KEY);
    if (!stored) return null;

    const session = JSON.parse(stored) as AuthSession;
    if (
      !session.accessToken ||
      !session.refreshToken ||
      !session.expiresAt ||
      !session.user?.fullName ||
      !Array.isArray(session.user.roles)
    ) {
      window.sessionStorage.removeItem(AUTH_SESSION_KEY);
      return null;
    }
    if (Date.parse(session.expiresAt) <= Date.now()) return null;
    return session;
  } catch {
    window.sessionStorage.removeItem(AUTH_SESSION_KEY);
    return null;
  }
}

export function loadActiveAuthSession(): Promise<AuthSession | null> {
  const session = loadAuthSession();
  if (session || typeof window === "undefined") return Promise.resolve(session);

  const stored = window.sessionStorage.getItem(AUTH_SESSION_KEY);
  if (!stored) return Promise.resolve(null);
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const expired = JSON.parse(stored) as AuthSession;
      if (!expired.refreshToken) return null;
      const refreshed = await apiRequest<AuthSession>("/api/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refreshToken: expired.refreshToken }),
      });
      saveAuthSession(refreshed);
      return refreshed;
    } catch {
      clearAuthSession();
      return null;
    }
  })().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

export function saveAuthSession(session: AuthSession) {
  window.sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
  notifySessionChanged();
}

export function clearAuthSession() {
  window.sessionStorage.removeItem(AUTH_SESSION_KEY);
  notifySessionChanged();
}
