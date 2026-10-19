"use client";

import { useSyncExternalStore } from "react";
import { AUTH_SESSION_CHANGED, clearAuthSession, loadAuthSession, type AuthSession } from "@/lib/auth-session";

const SERVER_SESSION: AuthSession | null = null;

function subscribe(onStoreChange: () => void) {
  window.addEventListener(AUTH_SESSION_CHANGED, onStoreChange);
  return () => window.removeEventListener(AUTH_SESSION_CHANGED, onStoreChange);
}

export function useAuthStore(): AuthSession | null {
  return useSyncExternalStore(subscribe, loadAuthSession, () => SERVER_SESSION);
}

export function signOutFromStore() {
  clearAuthSession();
}
