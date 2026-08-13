import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export default function EmployeeDeleteDialog({ employee, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  const deleteEmployee = async () => {
    setDeleting(true);
    setError("");
    try {
      await api.delete(`/employees/${employee.id}`);
      toast.success(`${employee.name} was removed`);
      onDeleted(employee.id);
      onClose();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not remove this employee");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="dialog-backdrop">
      <section className="password-dialog" data-testid="employee-delete-dialog">
        <button aria-label="Close delete dialog" className="icon-button profile-close" data-testid="close-employee-delete-button" onClick={onClose}>
          <X size={18} />
        </button>
        <AlertTriangle className="delete-warning-icon" size={24} />
        <p className="eyebrow">REMOVE EMPLOYEE</p>
        <h2>Remove {employee.name}?</h2>
        <p data-testid="employee-delete-message">This removes their sign-in account and profile photo access. Collection history remains available for reporting.</p>
        {error && <p className="login-error" data-testid="employee-delete-error">{error}</p>}
        <div className="dialog-actions">
          <button className="outline-button" data-testid="cancel-employee-delete-button" disabled={deleting} onClick={onClose}>
            Cancel
          </button>
          <button className="danger-button" data-testid="confirm-employee-delete-button" disabled={deleting} onClick={deleteEmployee}>
            {deleting ? "Removing…" : "Remove employee"}
          </button>
        </div>
      </section>
    </div>
  );
}