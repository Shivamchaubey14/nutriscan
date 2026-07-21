/** Auth state: secure-stored JWT, with login / register / guest / logout. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { fetchMe, obtainTokens, refreshAccess, register as registerApi } from '../api/auth';
import { deleteItem, getItem, setItem } from './storage';

const ACCESS_KEY = 'nutriscan.access';
const REFRESH_KEY = 'nutriscan.refresh';

type Status = 'loading' | 'authenticated' | 'guest' | 'unauthenticated';

interface AuthContextValue {
  status: Status;
  email: string | null;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  continueAsGuest: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('loading');
  const [email, setEmail] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const persist = useCallback(async (access: string, refresh: string) => {
    await setItem(ACCESS_KEY, access);
    await setItem(REFRESH_KEY, refresh);
    setAccessToken(access);
  }, []);

  const restore = useCallback(async () => {
    const access = await getItem(ACCESS_KEY);
    const refresh = await getItem(REFRESH_KEY);
    if (!access || !refresh) {
      setStatus('unauthenticated');
      return;
    }
    try {
      const me = await fetchMe(access);
      setEmail(me.email);
      setAccessToken(access);
      setStatus('authenticated');
    } catch {
      try {
        const refreshed = await refreshAccess(refresh);
        await setItem(ACCESS_KEY, refreshed.access);
        const me = await fetchMe(refreshed.access);
        setEmail(me.email);
        setAccessToken(refreshed.access);
        setStatus('authenticated');
      } catch {
        await deleteItem(ACCESS_KEY);
        await deleteItem(REFRESH_KEY);
        setStatus('unauthenticated');
      }
    }
  }, []);

  useEffect(() => {
    void restore();
  }, [restore]);

  const login = useCallback(
    async (userEmail: string, password: string) => {
      const tokens = await obtainTokens(userEmail, password);
      await persist(tokens.access, tokens.refresh);
      setEmail(userEmail);
      setStatus('authenticated');
    },
    [persist]
  );

  const register = useCallback(
    async (userEmail: string, password: string) => {
      await registerApi(userEmail, password);
      const tokens = await obtainTokens(userEmail, password);
      await persist(tokens.access, tokens.refresh);
      setEmail(userEmail);
      setStatus('authenticated');
    },
    [persist]
  );

  const continueAsGuest = useCallback(() => {
    setEmail(null);
    setAccessToken(null);
    setStatus('guest');
  }, []);

  const logout = useCallback(async () => {
    await deleteItem(ACCESS_KEY);
    await deleteItem(REFRESH_KEY);
    setEmail(null);
    setAccessToken(null);
    setStatus('unauthenticated');
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, email, accessToken, login, register, continueAsGuest, logout }),
    [status, email, accessToken, login, register, continueAsGuest, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
