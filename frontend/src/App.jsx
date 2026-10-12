import { useEffect, useState } from "react";

const API = "/api/auth";

async function request(path, payload, token) {
  const response = await fetch(`${API}/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong. Please try again.");
  }
  return data;
}

function App() {
  const [mode, setMode] = useState("login");
  const [pendingEmail, setPendingEmail] = useState("");
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("auth-token");
    if (!token) return undefined;

    let active = true;
    fetch(`${API}/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (response.status === 401) {
          localStorage.removeItem("auth-token");
          return null;
        }
        if (!response.ok) throw new Error("Could not restore your session.");
        return response.json();
      })
      .then((currentUser) => {
        if (active && currentUser) {
          setUser(currentUser);
        }
      })
      .catch((error) => {
        if (active) setNotice({ type: "error", text: error.message });
      });

    return () => { active = false; };
  }, []);

  function changeMode(nextMode) {
    setMode(nextMode);
    setNotice(null);
  }

  async function handleRegister(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setNotice(null);
    try {
      const data = await request("register", {
        name: form.get("name"),
        email: form.get("email"),
        password: form.get("password"),
      });
      setPendingEmail(form.get("email").trim().toLowerCase());
      setMode("verify");
      setNotice({ type: "success", text: data.message });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setNotice(null);
    try {
      const data = await request("verify", {
        email: pendingEmail,
        otp: form.get("otp"),
      });
      setMode("login");
      setNotice({ type: "success", text: data.message });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setNotice(null);
    try {
      const data = await request("login", {
        email: form.get("email"),
        password: form.get("password"),
      });
      localStorage.setItem("auth-token", data.access_token);
      setUser(data.user);
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("auth-token");
    setUser(null);
    setNotice({ type: "success", text: "You have been logged out." });
  }

  return (
    <main className="page-shell">
      <section className="intro-panel" aria-label="Account security information">
        <div className="brand"><span className="brand-mark">N</span> Northstar</div>
        <div className="intro-copy">
          <span className="eyebrow">YOUR SPACE, SECURED</span>
          <h1>A simpler way to manage your account.</h1>
          <p>Create an account in moments. We’ll verify your email before you get started.</p>
        </div>
        <div className="security-note">
          <span className="shield" aria-hidden="true">✓</span>
          <div><strong>Security comes first</strong><span>Your password is encrypted and never sent by email.</span></div>
        </div>
        <span className="panel-orb orb-one" aria-hidden="true" />
        <span className="panel-orb orb-two" aria-hidden="true" />
      </section>

      <section className="form-panel">
        <div className="mobile-brand"><span className="brand-mark">N</span> Northstar</div>
        {user ? (
          <div className="form-content welcome">
            <span className="eyebrow">ACCOUNT VERIFIED</span>
            <h2>Welcome, {user.name}.</h2>
            <p className="form-subtitle">You’re signed in as <strong>{user.email}</strong>.</p>
            <div className="account-card"><span className="avatar">{user.name[0]?.toUpperCase()}</span><div><strong>{user.name}</strong><span>{user.email}</span></div><span className="verified">Verified</span></div>
            <button className="button secondary-button" onClick={handleLogout}>Sign out</button>
          </div>
        ) : (
          <div className="form-content">
            <div className="form-heading">
              <span className="eyebrow">{mode === "verify" ? "ONE LAST STEP" : "WELCOME"}</span>
              <h2>
                {mode === "register" && "Create your account"}
                {mode === "login" && "Welcome back"}
                {mode === "verify" && "Check your inbox"}
              </h2>
              <p className="form-subtitle">
                {mode === "register" && "Enter your details to get started."}
                {mode === "login" && "Sign in to continue to your account."}
                {mode === "verify" && <>We sent a 6-digit verification code to <strong>{pendingEmail}</strong>.</>}
              </p>
            </div>

            {mode !== "verify" && (
              <div className="tabs" role="tablist" aria-label="Account access">
                <button className={mode === "login" ? "tab active" : "tab"} onClick={() => changeMode("login")} role="tab" aria-selected={mode === "login"}>Sign in</button>
                <button className={mode === "register" ? "tab active" : "tab"} onClick={() => changeMode("register")} role="tab" aria-selected={mode === "register"}>Create account</button>
              </div>
            )}

            {notice && <div className={`notice ${notice.type}`} role="status">{notice.text}</div>}

            {mode === "register" && (
              <form className="auth-form" onSubmit={handleRegister}>
                <label>Full name<input name="name" type="text" placeholder="e.g. Alex Morgan" autoComplete="name" maxLength="120" required /></label>
                <label>Email address<input name="email" type="email" placeholder="you@example.com" autoComplete="email" required /></label>
                <label>Password<input name="password" type="password" placeholder="At least 8 characters" autoComplete="new-password" minLength="8" maxLength="128" required /><span className="field-hint">Use at least 8 characters.</span></label>
                <button className="button" type="submit" disabled={busy}>{busy ? "Sending code…" : "Create account"}<span aria-hidden="true">→</span></button>
              </form>
            )}

            {mode === "login" && (
              <form className="auth-form" onSubmit={handleLogin}>
                <label>Email address<input name="email" type="email" placeholder="you@example.com" autoComplete="email" required /></label>
                <label>Password<input name="password" type="password" placeholder="Enter your password" autoComplete="current-password" required /></label>
                <button className="button" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}<span aria-hidden="true">→</span></button>
              </form>
            )}

            {mode === "verify" && (
              <form className="auth-form verify-form" onSubmit={handleVerify}>
                <label>Verification code<input name="otp" type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength="6" placeholder="000000" autoComplete="one-time-code" className="otp-input" required /></label>
                <span className="field-hint">The code expires in 10 minutes.</span>
                <button className="button" type="submit" disabled={busy}>{busy ? "Verifying…" : "Verify email"}<span aria-hidden="true">→</span></button>
                <button className="text-button" type="button" onClick={() => changeMode("register")}>Back to registration</button>
              </form>
            )}

            <p className="privacy-note"><span aria-hidden="true">✳</span> Your information stays private and secure.</p>
          </div>
        )}
        <footer>© 2026 Northstar. Secure access, made simple.</footer>
      </section>
    </main>
  );
}

export default App;
