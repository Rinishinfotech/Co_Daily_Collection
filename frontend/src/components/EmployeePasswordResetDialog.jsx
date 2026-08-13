import { useState } from "react";
import { KeyRound, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export default function EmployeePasswordResetDialog({ employee, onClose }) {
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const resetPassword = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.post(`/employees/${employee.id}/reset-password`, {
        temporary_password: temporaryPassword,
      });
      toast.success(`Temporary password set for ${employee.name}`);
      onClose();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not reset this password");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dialog-backdrop">
      <section className="password-dialog" data-testid="employee-password-reset-dialog">
        <button aria-label="Close reset dialog" className="icon-button profile-close" data-testid="close-password-reset-button" onClick={onClose}>
          <X size={18} />
        </button>
        <KeyRound size={24} />
        <p className="eyebrow">EMPLOYEE PASSWORD</p>
        <h2>Set a temporary password</h2>
        <p data-testid="password-reset-employee-name">{employee.name} must create a personal password at next sign-in.</p>
        <form data-testid="employee-password-reset-form" onSubmit={resetPassword}>
          <label>
            Temporary password
            <input required data-testid="employee-temporary-password-input" minLength="8" type="password" value={temporaryPassword} onChange={(event) => setTemporaryPassword(event.target.value)} />
          </label>
          {error && <p className="login-error" data-testid="employee-password-reset-error">{error}</p>}
          <button className="primary-button full-button" data-testid="employee-password-reset-submit" disabled={submitting} type="submit">
            {submitting ? "Saving…" : "Set temporary password"}
          </button>
        </form>
      </section>
    </div>
  );
}