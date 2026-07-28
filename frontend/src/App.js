import { useEffect, useState } from "react";
import "@/App.css";
import { Toaster } from "sonner";
import PortalHeader from "@/components/PortalHeader";
import EmployeePortal from "@/pages/EmployeePortal";
import AdminPortal from "@/pages/AdminPortal";
import LoginPage from "@/pages/LoginPage";
import { api, setAuthToken } from "@/lib/api";

function App() {
  const [user, setUser] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [profile, setProfile] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = () => setRefreshKey((value) => value + 1);

  useEffect(() => {
    api.get("/auth/me").then(({ data }) => setUser(data)).catch(() => setUser(false));
  }, []);

  useEffect(() => {
    if (!user || user === false) return;
    const requests = [api.get("/vendors"), api.get("/profile")];
    if (user.role === "admin") requests.push(api.get("/employees"));
    Promise.all(requests).then(([vendorResponse, profileResponse, employeeResponse]) => {
      setVendors(vendorResponse.data);
      setProfile(profileResponse.data);
      setEmployees(employeeResponse?.data || []);
    });
  }, [user, refreshKey]);

  if (user === null) return <div className="loading-screen" data-testid="app-loading">Loading LedgerFlow…</div>;
  if (user === false) return <LoginPage onLogin={(data) => { setAuthToken(data.token); setUser(data.user); }} />;
  const logout = async () => { try { await api.post("/auth/logout"); } finally { setAuthToken(null); setUser(false); setProfile(null); } };

  return (
    <div className="app-shell">
      <PortalHeader onLogout={logout} onProfile={() => setProfile((value) => ({ ...value, open: !value?.open }))} user={user} />
      {user.role === "employee" ? <EmployeePortal employee={profile?.employee || user} vendors={vendors} refreshKey={refreshKey} onDataChange={refresh} mustChangePassword={user.must_change_password} onPasswordChanged={() => setUser({ ...user, must_change_password: false })} /> : <AdminPortal employees={employees} vendors={vendors} refreshKey={refreshKey} onDataChange={refresh} />}
      {profile?.open && <section className="profile-popover" data-testid="profile-panel"><button className="icon-button profile-close" data-testid="profile-close-button" onClick={() => setProfile({ ...profile, open: false })}>×</button><p className="eyebrow">MY PROFILE</p><h2 data-testid="profile-name">{user.name}</h2><p data-testid="profile-phone">{user.phone}</p><p data-testid="profile-role">{user.role === "admin" ? "Administrator account" : profile.employee?.territory}</p></section>}
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
