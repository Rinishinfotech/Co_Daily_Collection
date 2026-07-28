import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, BadgeIndianRupee, MapPin, Plus, ReceiptText, WalletCards } from "lucide-react";
import { toast } from "sonner";
import ReceiptDialog from "@/components/ReceiptDialog";
import { api, currency, dateTime } from "@/lib/api";

const emptyCollection = { vendor_id: "", vendor_name: "", amount: "", payment_mode: "UPI", remarks: "" };
const emptyExpense = { category: "Fuel", amount: "", remarks: "" };

export default function EmployeePortal({ employee, vendors, refreshKey, onDataChange }) {
  const [dashboard, setDashboard] = useState(null);
  const [collections, setCollections] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [collection, setCollection] = useState(emptyCollection);
  const [expense, setExpense] = useState(emptyExpense);
  const [receipt, setReceipt] = useState(null);
  const [showExpense, setShowExpense] = useState(false);

  useEffect(() => {
    Promise.all([api.get(`/dashboard?employee_id=${employee.id}`), api.get(`/collections?employee_id=${employee.id}`), api.get(`/expenses?employee_id=${employee.id}`)]).then(([dash, col, exp]) => {
      setDashboard(dash.data);
      setCollections(col.data);
      setExpenses(exp.data);
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

  const submitExpense = async (event) => {
    event.preventDefault();
    await api.post("/expenses", { ...expense, amount: Number(expense.amount), employee_id: employee.id, employee_name: employee.name });
    setExpense(emptyExpense);
    setShowExpense(false);
    toast.success("Expense logged for today");
    onDataChange();
  };

  const updateCollection = (key, value) => setCollection((previous) => ({ ...previous, [key]: value }));
  const updateExpense = (key, value) => setExpense((previous) => ({ ...previous, [key]: value }));

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
        <article className="metric-card" data-testid="employee-today-expenses"><WalletCards /><span>Field expenses</span><strong>{currency(dashboard?.today_expenses)}</strong></article>
      </section>
      <section className="form-panel collection-panel" data-testid="collection-entry-panel">
        <div className="panel-heading"><div><p className="eyebrow">NEW ENTRY</p><h2>Record a collection</h2></div><ReceiptText size={22} /></div>
        <form onSubmit={submitCollection}>
          <label>Vendor
            <select required data-testid="collection-vendor-select" value={collection.vendor_id} onChange={(event) => updateCollection("vendor_id", event.target.value)}>
              <option value="">Choose from your vendors</option>
              {vendors.map((vendor) => <option key={vendor.id} value={vendor.id}>{vendor.business_name} · {vendor.name}</option>)}
            </select>
          </label>
          <div className="form-or">or enter a new vendor</div>
          <label>Vendor name<input data-testid="collection-vendor-name-input" placeholder="Vendor name" value={collection.vendor_name} onChange={(event) => updateCollection("vendor_name", event.target.value)} /></label>
          <label>Collection amount<input required data-testid="collection-amount-input" min="1" placeholder="0" type="number" value={collection.amount} onChange={(event) => updateCollection("amount", event.target.value)} /></label>
          <label>Payment mode<select data-testid="collection-payment-mode-select" value={collection.payment_mode} onChange={(event) => updateCollection("payment_mode", event.target.value)}>{["Cash", "UPI", "Bank Transfer", "Cheque"].map((mode) => <option key={mode}>{mode}</option>)}</select></label>
          <label>Remarks<textarea data-testid="collection-remarks-input" placeholder="Optional payment note" value={collection.remarks} onChange={(event) => updateCollection("remarks", event.target.value)} /></label>
          <button className="primary-button full-button" data-testid="collection-submit-button" type="submit"><Plus size={19} /> Save collection</button>
        </form>
      </section>
      <section className="section-block" data-testid="recent-transactions-section"><div className="section-heading"><div><p className="eyebrow">ACTIVITY</p><h2>Recent collections</h2></div><ArrowUpRight size={19} /></div><div className="transaction-list">{collections.slice(0, 4).map((item) => <article className="transaction-row" data-testid={`transaction-${item.id}`} key={item.id}><div className="transaction-icon"><ReceiptText size={18} /></div><div><strong>{item.vendor_name}</strong><span>{dateTime(item.created_at)} · {item.payment_mode}</span></div><b>{currency(item.amount)}</b></article>)}</div></section>
      <section className="section-block expense-section" data-testid="expense-section"><div className="section-heading"><div><p className="eyebrow">FIELD COSTS</p><h2>Daily expenses</h2></div><button className="compact-button" data-testid="toggle-expense-form-button" onClick={() => setShowExpense(!showExpense)}>{showExpense ? "Close" : "Add expense"}</button></div>
        {showExpense && <form className="inline-form" data-testid="expense-entry-form" onSubmit={submitExpense}><label>Category<select data-testid="expense-category-select" value={expense.category} onChange={(event) => updateExpense("category", event.target.value)}>{["Fuel", "Meals", "Parking", "Supplies", "Other"].map((category) => <option key={category}>{category}</option>)}</select></label><label>Amount<input required data-testid="expense-amount-input" min="1" type="number" value={expense.amount} onChange={(event) => updateExpense("amount", event.target.value)} /></label><label>Remarks<textarea data-testid="expense-remarks-input" value={expense.remarks} onChange={(event) => updateExpense("remarks", event.target.value)} /></label><button className="primary-button full-button" data-testid="expense-submit-button" type="submit">Save expense</button></form>}
        <div className="expense-list">{expenses.slice(0, 3).map((item) => <article className="expense-row" data-testid={`expense-${item.id}`} key={item.id}><span>{item.category}</span><span>{item.remarks || "Field cost"}</span><b>{currency(item.amount)}</b></article>)}</div>
      </section>
      <ReceiptDialog receipt={receipt} onClose={() => setReceipt(null)} />
    </motion.main>
  );
}