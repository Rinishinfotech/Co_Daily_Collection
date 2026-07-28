import { Landmark, LayoutDashboard, UserRound } from "lucide-react";

export default function PortalHeader({ view, setView, employee, setEmployee, employees }) {
  return (
    <header className="portal-header">
      <div className="brand-mark" data-testid="app-brand"><Landmark size={19} /> <span>LedgerFlow</span></div>
      <div className="role-switcher" data-testid="role-switcher">
        <button className={view === "employee" ? "active" : ""} data-testid="employee-view-button" onClick={() => setView("employee")}><UserRound size={15} /> Employee</button>
        <button className={view === "admin" ? "active" : ""} data-testid="admin-view-button" onClick={() => setView("admin")}><LayoutDashboard size={15} /> Admin</button>
      </div>
      {view === "employee" && (
        <select aria-label="Active employee" className="employee-select" data-testid="active-employee-select" value={employee.id} onChange={(event) => setEmployee(employees.find((item) => item.id === event.target.value))}>
          {employees.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      )}
    </header>
  );
}