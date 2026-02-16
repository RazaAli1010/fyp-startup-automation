"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { UserPublic } from "./types";
import { getMe, getToken, clearToken, setToken } from "./api";

interface AuthContextValue {
  user: UserPublic | null;
  loading: boolean;
  login: (token: string, user: UserPublic) => void;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
    refresh();
  }, [refresh]);

  const loginFn = useCallback((token: string, userData: UserPublic) => {
    setToken(token);
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login: loginFn, logout, refresh }),
    [user, loading, loginFn, logout, refresh],
  );

  // Prevent rendering children until client has mounted.
  // This guarantees server HTML === initial client HTML (no hydration mismatch).
  if (!mounted) return null;

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
