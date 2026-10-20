"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import {
  AUTH_SESSION_CHANGED,
  AUTH_SESSION_KEY,
  clearAuthSession,
  loadActiveAuthSession,
  loadAuthSession,
  type AuthSession,
} from "@/lib/auth-session";

const SERVER_SESSION: AuthSession | null = null;
let cachedRawSession: string | null | undefined;
let cachedSession: AuthSession | null = null;

function getSnapshot(): AuthSession | null {
  const rawSession = window.sessionStorage.getItem(AUTH_SESSION_KEY);
  if (rawSession !== cachedRawSession) {
    cachedRawSession = rawSession;
    cachedSession = loadAuthSession();
  }
  return cachedSession;
}

function subscribe(onStoreChange: () => void) {
  window.addEventListener(AUTH_SESSION_CHANGED, onStoreChange);
  const onStorage = (event: StorageEvent) => {
    if (event.storageArea === window.sessionStorage && event.key === AUTH_SESSION_KEY) onStoreChange();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(AUTH_SESSION_CHANGED, onStoreChange);
    window.removeEventListener("storage", onStorage);
  };
}

export function useAuthStore(): AuthSession | null | undefined {
  const session = useSyncExternalStore(subscribe, getSnapshot, () => SERVER_SESSION);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    void loadActiveAuthSession().finally(() => {
      if (active) setReady(true);
    });
    return () => {
      active = false;
    };
  }, []);

  return ready ? session : undefined;
}

export function signOutFromStore() {
  clearAuthSession();
}
