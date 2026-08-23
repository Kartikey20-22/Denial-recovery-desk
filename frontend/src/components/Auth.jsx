import React, { useState } from "react";
import { api } from "../api";

export default function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("demo@denialdesk.local");
  const [password, setPassword] = useState("Demo@12345");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const fn = mode === "login" ? api.login(email, password) : api.register(email, password, name);
      const x = await fn;
      localStorage.setItem("token", x.access_token);
      onLogin();
    } catch (e2) {
      setErr(mode === "login" ? "Invalid email or password." : e2.message || "Could not register.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="authScreen">
      <div className="authAside">
        <div className="authBrand">
          <div className="logo">DR</div>
          <span>Denial Recovery Desk</span>
        </div>
        <h1>Turn denied claims back into revenue.</h1>
        <p>
          A local, privacy-first pipeline that reads denial letters, classifies the reason, pulls the
          matching payer policy, and drafts a ready-to-send appeal — with a human review gate for
          anything the model isn't confident about.
        </p>
        <ul className="authStats">
          <li>
            <strong>6</strong>
            <span>pipeline stages</span>
          </li>
          <li>
            <strong>0</strong>
            <span>PHI leaves your machine</span>
          </li>
          <li>
            <strong>90%</strong>
            <span>auto-approve threshold</span>
          </li>
        </ul>
      </div>
      <div className="authCard">
        <div className="card loginCard">
          <div className="brand">DR</div>
          <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
          <p>{mode === "login" ? "Sign in to your recovery desk" : "Set up reviewer access"}</p>
          <form onSubmit={submit}>
            {mode === "register" && (
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" required />
            )}
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              type="email"
              required
            />
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              type="password"
              required
              minLength={mode === "register" ? 8 : undefined}
            />
            <button disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
          </form>
          <small className={err ? "err" : ""}>{err || "Demo: demo@denialdesk.local / Demo@12345"}</small>
          <button className="linkBtn" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
