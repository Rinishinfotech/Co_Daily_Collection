import { Landmark, LogOut, UserRound } from "lucide-react";

export default function PortalHeader({ user, onProfile, onLogout }) {
  return (
    <header className="portal-header">
      <div className="brand-mark" data-testid="app-brand"><Landmark size={19} /> <span>Co. Daily Collection</span></div>
      <div className="account-actions" data-testid="signed-in-account"><button className="profile-trigger" data-testid="profile-button" onClick={onProfile}><UserRound size={16} /><span>{user.name}</span><small>{user.role === "admin" ? "Administrator" : "Field employee"}</small></button><button aria-label="Sign out" className="icon-button" data-testid="logout-button" onClick={onLogout}><LogOut size={18} /></button></div>
    </header>
  );
}