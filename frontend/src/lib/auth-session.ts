export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  user: {
    fullName: string;
    roles: string[];
  };
};

const AUTH_SESSION_KEY = "culinary-blog.auth-session";
export const AUTH_SESSION_CHANGED = "culinary-blog:auth-session-changed";
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export async function loadActiveAuthSession(): Promise<AuthSession | null> {
  const session = loadAuthSession();
  if (session || typeof window === "undefined") return session;

  const stored = window.sessionStorage.getItem(AUTH_SESSION_KEY);
  if (!stored) return null;

  try {
    const expired = JSON.parse(stored) as AuthSession;
    if (!expired.refreshToken) return null;
    const response = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken: expired.refreshToken }),
    });
    if (!response.ok) throw new Error("refresh failed");
    const refreshed = (await response.json()) as AuthSession;
    saveAuthSession(refreshed);
    return refreshed;
  } catch {
    clearAuthSession();
    return null;
  }
}

export function saveAuthSession(session: AuthSession) {
  window.sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
  notifySessionChanged();
}

export function clearAuthSession() {
  window.sessionStorage.removeItem(AUTH_SESSION_KEY);
  notifySessionChanged();
}
