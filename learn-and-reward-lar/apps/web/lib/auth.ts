"use client";

import { useEffect, useState } from "react";
import { api, getToken, setToken, type UserResponse } from "./api";

/**
 * Lightweight auth context backed by the localStorage token.
 * NOTE: the login page and this shell are a placeholder until Developer C's
 * frontend shell lands; the auth pages will be replaced then.
 */

type AuthState = {
  user: UserResponse | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => void;
};

export function useAuthState(): AuthState {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!getToken()) {
        setUser(null);
        setLoading(false);
        return;
      }
      try {
        const me = await api<UserResponse>("/users/me");
        if (!cancelled) setUser(me);
      } catch {
        setToken(null);
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refresh() {
    if (!getToken()) {
      setUser(null);
      return;
    }
    try {
      setUser(await api<UserResponse>("/users/me"));
    } catch {
      setToken(null);
      setUser(null);
    }
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return { user, loading, refresh, logout };
}
