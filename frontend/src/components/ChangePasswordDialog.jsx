import { useState } from "react";
import { KeyRound } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export default function ChangePasswordDialog({ onComplete }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    try {
      await api.post("/auth/change-password", { current_password: currentPassword, new_password: newPassword });
      toast.success("Your password has been updated");
      onComplete();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not update password");
    }
  };

  return <div className="dialog-backdrop"><section className="password-dialog" data-testid="change-password-dialog"><KeyRound size={24} /><p className="eyebrow">ACCOUNT SECURITY</p><h2>Create your personal password</h2><p>Your administrator issued a temporary password. Change it before recording collections.</p><form onSubmit={submit}><label>Temporary password<input required data-testid="current-password-input" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label><label>New password<input required data-testid="new-password-input" minLength="8" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>{error && <p className="login-error" data-testid="password-change-error">{error}</p>}<button className="primary-button full-button" data-testid="change-password-submit-button" type="submit">Save new password</button></form></section></div>;
}