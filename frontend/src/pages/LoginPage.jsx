import { useState } from "react";
import { Landmark, LockKeyhole, Phone } from "lucide-react";
import { api } from "@/lib/api";

export default function LoginPage({ onLogin }) {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [employeeMode, setEmployeeMode] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/auth/login", { phone, password });
      if (employeeMode && data.user.role !== "employee") {
        await api.post("/auth/logout");
        setError("This sign-in is for field employees. Use administrator sign-in instead.");
        return;
      }
      onLogin(data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to sign in. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return <main className="login-page" data-testid="login-page"><section className="login-panel"><div className="login-brand" data-testid="login-brand"><Landmark size={24} /><span>LedgerFlow</span></div><p className="eyebrow">{employeeMode ? "EMPLOYEE ACCESS" : "SECURE COLLECTION ACCESS"}</p><h1>{employeeMode ? "Employee sign-in." : "Sign in to your field desk."}</h1><p className="login-copy">{employeeMode ? "Enter the phone number and personal password created by your administrator." : "Use the phone number and password issued by your administrator."}</p><form data-testid="login-form" onSubmit={submit}><label>Phone number<div className="login-input"><Phone size={17} /><input required data-testid="login-phone-input" placeholder="Your registered phone number" value={phone} onChange={(event) => setPhone(event.target.value)} /></div></label><label>Password<div className="login-input"><LockKeyhole size={17} /><input required data-testid="login-password-input" placeholder="Your password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></div></label>{error && <p className="login-error" data-testid="login-error-message">{error}</p>}<button className="primary-button full-button" data-testid="login-submit-button" disabled={loading} type="submit">{loading ? "Signing in…" : employeeMode ? "Sign in as employee" : "Sign in securely"}</button></form>{employeeMode ? <button className="employee-login-link" data-testid="administrator-login-link" onClick={() => { setEmployeeMode(false); setError(""); }}>Administrator sign-in</button> : <button className="employee-login-link" data-testid="employee-login-link" onClick={() => { setEmployeeMode(true); setError(""); }}>Login as an employee</button>}</section></main>;
}