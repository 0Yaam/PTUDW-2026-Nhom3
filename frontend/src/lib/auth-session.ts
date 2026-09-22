export type AuthSession = {
  accessToken: string;
  expiresAt: string;
  user: {
    fullName: string;
    roles: string[];
  };
};

const AUTH_SESSION_KEY = "culinary-blog.auth-session";
export const AUTH_SESSION_CHANGED = "culinary-blog:auth-session-changed";

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
      !session.expiresAt ||
      !session.user?.fullName ||
      !Array.isArray(session.user.roles) ||
      Date.parse(session.expiresAt) <= Date.now()
    ) {
      window.sessionStorage.removeItem(AUTH_SESSION_KEY);
      return null;
    }
    return session;
  } catch {
    window.sessionStorage.removeItem(AUTH_SESSION_KEY);
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
