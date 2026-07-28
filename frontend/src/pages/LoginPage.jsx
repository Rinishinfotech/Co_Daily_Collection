import { useState } from "react";
import { Landmark, LockKeyhole, Phone } from "lucide-react";
import { api } from "@/lib/api";

export default function LoginPage({ onLogin }) {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/auth/login", { phone, password });
      onLogin(data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to sign in. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return <main className="login-page" data-testid="login-page"><section className="login-panel"><div className="login-brand" data-testid="login-brand"><Landmark size={24} /><span>LedgerFlow</span></div><p className="eyebrow">SECURE COLLECTION ACCESS</p><h1>Sign in to your field desk.</h1><p className="login-copy">Use the phone number and password issued by your administrator.</p><form data-testid="login-form" onSubmit={submit}><label>Phone number<div className="login-input"><Phone size={17} /><input required data-testid="login-phone-input" placeholder="Your registered phone number" value={phone} onChange={(event) => setPhone(event.target.value)} /></div></label><label>Password<div className="login-input"><LockKeyhole size={17} /><input required data-testid="login-password-input" placeholder="Your password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></div></label>{error && <p className="login-error" data-testid="login-error-message">{error}</p>}<button className="primary-button full-button" data-testid="login-submit-button" disabled={loading} type="submit">{loading ? "Signing in…" : "Sign in securely"}</button></form></section></main>;
}