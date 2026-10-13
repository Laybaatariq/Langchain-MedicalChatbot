import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getMe, getToken, login as apiLogin, setToken, signup as apiSignup } from "../api.js";

const AuthContext = createContext(null);

/**
 * Keeps the logged-in patient for the whole app.
 *   user:    { id, name, email, role } or null
 *   ready:   false until the saved login (if any) has been checked
 *   signIn, signUp, signOut
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  // On page load: if a token is saved, ask the server who it belongs to
  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    getMe()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  // api.js announces this when the server says the saved login is no longer valid
  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("medchat:logout", onLogout);
    return () => window.removeEventListener("medchat:logout", onLogout);
  }, []);

  const signIn = useCallback(async (email, password) => {
    const data = await apiLogin(email, password);
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const signUp = useCallback(async (name, email, password) => {
    const data = await apiSignup(name, email, password);
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, ready, signIn, signUp, signOut }), [user, ready, signIn, signUp, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
