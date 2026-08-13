import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, BadgeIndianRupee, MapPin, Plus, ReceiptText } from "lucide-react";
import { toast } from "sonner";
import ReceiptDialog from "@/components/ReceiptDialog";
import ChangePasswordDialog from "@/components/ChangePasswordDialog";
import { api, currency, dateTime } from "@/lib/api";

const emptyCollection = { vendor_id: "", vendor_name: "", amount: "", payment_mode: "UPI", remarks: "" };

export default function EmployeePortal({ employee, vendors, refreshKey, onDataChange, mustChangePassword, onPasswordChanged }) {
  const [dashboard, setDashboard] = useState(null);
  const [collections, setCollections] = useState([]);
  const [collection, setCollection] = useState(emptyCollection);
  const [receipt, setReceipt] = useState(null);
  const [showQuickVendor, setShowQuickVendor] = useState(false);
  const [quickVendorName, setQuickVendorName] = useState("");
  const [passwordRequired, setPasswordRequired] = useState(mustChangePassword);

  useEffect(() => {
    Promise.all([api.get(`/dashboard?employee_id=${employee.id}`), api.get(`/collections?employee_id=${employee.id}`)]).then(([dash, col]) => {
      setDashboard(dash.data);
      setCollections(col.data);
    });
  }, [employee, refreshKey]);

  const submitCollection = async (event) => {
    event.preventDefault();
    const vendor = vendors.find((item) => item.id === collection.vendor_id);
    const payload = { ...collection, vendor_name: vendor?.name || collection.vendor_name, amount: Number(collection.amount), employee_id: employee.id, employee_name: employee.name };
    const { data } = await api.post("/collections", payload);
    setReceipt(data);
    setCollection(emptyCollection);
    toast.success("Collection recorded successfully");
    onDataChange();
  };

  const updateCollection = (key, value) => setCollection((previous) => ({ ...previous, [key]: value }));
  const addQuickVendor = async () => {
    if (quickVendorName.trim().length < 2) {
      toast.error("Enter a vendor name first");
      return;
    }
    try {
      const { data } = await api.post("/vendors/quick-add", { name: quickVendorName.trim() });
      setCollection((previous) => ({ ...previous, vendor_id: data.id, vendor_name: data.name }));
      setQuickVendorName("");
      setShowQuickVendor(false);
      toast.success(`${data.business_name} is ready to select`);
      onDataChange();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Could not add this vendor");
    }
  };

  return (
    <motion.main animate={{ opacity: 1, y: 0 }} className="employee-page" initial={{ opacity: 0, y: 10 }}>
      <section className="employee-welcome" data-testid="employee-welcome">
        <p className="eyebrow">FIELD DESK · TODAY</p>
        <h1>Good morning, {employee.name.split(" ")[0]}.</h1>
        <p data-testid="employee-territory"><MapPin size={15} /> {employee.territory} territory</p>
      </section>
      <section className="metric-grid employee-metrics" aria-label="Today's performance">
        <article className="metric-card ink" data-testid="employee-today-collection"><BadgeIndianRupee /><span>Collected today</span><strong>{currency(dashboard?.today_collection)}</strong></article>
        <article className="metric-card" data-testid="employee-vendors-visited"><MapPin /><span>Vendors visited</span><strong>{dashboard?.vendors_visited || 0}</strong></article>
      </section>
      <section className="form-panel collection-panel" data-testid="collection-entry-panel">
        <div className="panel-heading"><div><p className="eyebrow">NEW ENTRY</p><h2>Record a collection</h2></div><ReceiptText size={22} /></div>
        <form onSubmit={submitCollection}>
          <label>Vendor
            <select required data-testid="collection-vendor-select" value={collection.vendor_id} onChange={(event) => updateCollection("vendor_id", event.target.value)}>
              <option value="">Choose from your vendors</option>
              {vendors.map((vendor) => <option key={vendor.id} value={vendor.id}>{`${vendor.business_name} · ${vendor.name}`}</option>)}
            </select>
          </label>
          <button className="form-or quick-vendor-toggle" data-testid="toggle-quick-vendor-button" type="button" onClick={() => setShowQuickVendor(!showQuickVendor)}>or add a new vendor</button>
          {showQuickVendor && <div className="quick-vendor-form" data-testid="quick-vendor-form"><label>New vendor / business name<input data-testid="quick-vendor-name-input" placeholder="Business name" value={quickVendorName} onChange={(event) => setQuickVendorName(event.target.value)} /></label><button className="outline-button" data-testid="quick-vendor-save-button" type="button" onClick={addQuickVendor}>Add to vendors</button></div>}
          <label>Vendor name<input data-testid="collection-vendor-name-input" placeholder="Vendor name" value={collection.vendor_name} onChange={(event) => updateCollection("vendor_name", event.target.value)} /></label>
          <label>Collection amount<input required data-testid="collection-amount-input" min="1" placeholder="0" type="number" value={collection.amount} onChange={(event) => updateCollection("amount", event.target.value)} /></label>
          <label>Payment mode<select data-testid="collection-payment-mode-select" value={collection.payment_mode} onChange={(event) => updateCollection("payment_mode", event.target.value)}>{["Cash", "UPI", "Bank Transfer", "Cheque"].map((mode) => <option key={mode}>{mode}</option>)}</select></label>
          <label>Remarks<textarea data-testid="collection-remarks-input" placeholder="Optional payment note" value={collection.remarks} onChange={(event) => updateCollection("remarks", event.target.value)} /></label>
          <button className="primary-button full-button" data-testid="collection-submit-button" type="submit"><Plus size={19} /> Save collection</button>
        </form>
      </section>
      <section className="section-block" data-testid="recent-transactions-section"><div className="section-heading"><div><p className="eyebrow">ACTIVITY</p><h2>Recent collections</h2></div><ArrowUpRight size={19} /></div><div className="transaction-list">{collections.slice(0, 4).map((item) => <article className="transaction-row" data-testid={`transaction-${item.id}`} key={item.id}><div className="transaction-icon"><ReceiptText size={18} /></div><div><strong>{item.vendor_name}</strong><span>{dateTime(item.created_at)} · {item.payment_mode}</span></div><b>{currency(item.amount)}</b></article>)}</div></section>
      <ReceiptDialog receipt={receipt} onClose={() => setReceipt(null)} />
      {passwordRequired && <ChangePasswordDialog onComplete={() => { setPasswordRequired(false); onPasswordChanged(); }} />}
    </motion.main>
  );
}