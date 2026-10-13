import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { errMsg } from "@/lib/api";

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try { await login(email, password); nav("/"); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="nd-grain min-h-screen grid lg:grid-cols-[1.3fr_1fr]">
      <section className="bg-black text-[#f3f1ec] p-10 md:p-16 flex flex-col justify-between">
        <div className="font-mono text-xs tracking-[0.3em]">EDITION 001 — EDITORIAL CONSOLE</div>
        <div className="nd-rise">
          <h1 className="font-display text-6xl md:text-8xl leading-[0.9]">RAW PHOTO.<br />ROUGH NOTES.<br /><span className="text-transparent" style={{ WebkitTextStroke: "2px #f3f1ec" }}>READY POST.</span></h1>
          <p className="font-serif text-xl mt-8 max-w-lg opacity-80">Drop in what you shot and what you know. The desk writes the headline, designs the carousel and waits for your nod before it hits Instagram.</p>
        </div>
        <div className="font-mono text-xs opacity-60">STAFF ACCESS ONLY</div>
      </section>
      <section className="p-10 md:p-16 flex items-center">
        <form onSubmit={submit} className="w-full max-w-sm space-y-8 nd-rise" style={{ animationDelay: "120ms" }} data-testid="login-form">
          <h2 className="font-display text-4xl">SIGN IN</h2>
          <div>
            <label className="nd-label">Email</label>
            <input data-testid="login-email-input" className="nd-input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="nd-label">Password</label>
            <input data-testid="login-password-input" className="nd-input" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p data-testid="login-error" className="font-mono text-sm border-l-4 border-black pl-3">{error}</p>}
          <button data-testid="login-submit-button" className="nd-btn w-full justify-center" disabled={busy}>
            {busy ? "Checking…" : "Enter the desk"} <ArrowRight size={16} />
          </button>
        </form>
      </section>
    </div>
  );
}
