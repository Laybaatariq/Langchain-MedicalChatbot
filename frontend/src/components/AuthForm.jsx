import { useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";

/** Log in / create account form. Calls onDone() after a successful login or signup. */
export default function AuthForm({ initialMode = "login", onDone }) {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const isSignup = mode === "signup";

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (isSignup) await signUp(name, email, password);
      else await signIn(email, password);
      onDone?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="form" onSubmit={submit}>
      {isSignup && (
        <label>
          Your name
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} autoComplete="name" />
        </label>
      )}
      <label>
        Email
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
      </label>
      <label>
        Password {isSignup && <span className="form-hint">(at least 8 characters)</span>}
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={isSignup ? 8 : undefined}
          autoComplete={isSignup ? "new-password" : "current-password"}
        />
      </label>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <button type="submit" className="primary" disabled={busy}>
        {busy ? "Please wait..." : isSignup ? "Create account" : "Log in"}
      </button>

      <p className="form-switch">
        {isSignup ? "Already have an account?" : "New here?"}{" "}
        <button
          type="button"
          className="link"
          onClick={() => {
            setMode(isSignup ? "login" : "signup");
            setError(null);
          }}
        >
          {isSignup ? "Log in" : "Create an account"}
        </button>
      </p>
    </form>
  );
}