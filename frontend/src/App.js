import { useEffect, useState } from "react";
import "@/App.css";
import { Toaster } from "sonner";
import PortalHeader from "@/components/PortalHeader";
import EmployeePortal from "@/pages/EmployeePortal";
import AdminPortal from "@/pages/AdminPortal";
import { api } from "@/lib/api";

function App() {
  const [view, setView] = useState("employee");
  const [vendors, setVendors] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [employee, setEmployee] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = () => setRefreshKey((value) => value + 1);

  useEffect(() => {
    Promise.all([api.get("/vendors"), api.get("/employees")]).then(([vendorResponse, employeeResponse]) => {
      setVendors(vendorResponse.data);
      setEmployees(employeeResponse.data);
      setEmployee((current) => current || employeeResponse.data[0]);
    });
  }, [refreshKey]);

  if (!employee) return <div className="loading-screen" data-testid="app-loading">Loading LedgerFlow…</div>;

  return (
    <div className={`app-shell ${view === "admin" ? "admin-shell" : "employee-shell"}`}>
      <PortalHeader employee={employee} employees={employees} setEmployee={setEmployee} setView={setView} view={view} />
      {view === "employee" ? <EmployeePortal employee={employee} vendors={vendors} refreshKey={refreshKey} onDataChange={refresh} /> : <AdminPortal employees={employees} vendors={vendors} refreshKey={refreshKey} onDataChange={refresh} />}
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
