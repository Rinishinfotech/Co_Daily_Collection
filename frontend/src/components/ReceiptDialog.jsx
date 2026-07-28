import { Download, MessageCircle, X } from "lucide-react";
import { currency, dateTime } from "@/lib/api";

export default function ReceiptDialog({ receipt, onClose }) {
  if (!receipt) return null;

  const message = `LedgerFlow Collections Receipt ${receipt.receipt_number}\nVendor: ${receipt.vendor_name}\nAmount: ${currency(receipt.amount)}\nMode: ${receipt.payment_mode}\nReceived: ${dateTime(receipt.created_at)}\nCollector: ${receipt.employee_name}\nThank you.`;

  return (
    <div className="dialog-backdrop" role="presentation">
      <section aria-modal="true" aria-label="Digital receipt" className="receipt-dialog" data-testid="receipt-dialog">
        <button aria-label="Close receipt" className="icon-button receipt-close" data-testid="receipt-close-button" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="receipt-brand" data-testid="receipt-company-name">LEDGERFLOW COLLECTIONS</div>
        <div className="receipt-rule" />
        <p className="receipt-label" data-testid="receipt-number-label">RECEIPT NO.</p>
        <p className="receipt-id" data-testid="receipt-number">{receipt.receipt_number}</p>
        <div className="receipt-total" data-testid="receipt-amount">{currency(receipt.amount)}</div>
        <div className="receipt-details">
          <p data-testid="receipt-vendor"><span>VENDOR</span>{receipt.vendor_name}</p>
          <p data-testid="receipt-payment"><span>PAYMENT MODE</span>{receipt.payment_mode}</p>
          <p data-testid="receipt-datetime"><span>RECEIVED AT</span>{dateTime(receipt.created_at)}</p>
          <p data-testid="receipt-employee"><span>COLLECTED BY</span>{receipt.employee_name}</p>
          {receipt.remarks && <p data-testid="receipt-remarks"><span>REMARKS</span>{receipt.remarks}</p>}
        </div>
        <div className="receipt-rule" />
        <p className="receipt-thanks" data-testid="receipt-thanks-message">Thank you for your payment.</p>
        <a className="whatsapp-button" data-testid="receipt-whatsapp-share" href={`https://wa.me/?text=${encodeURIComponent(message)}`} rel="noreferrer" target="_blank">
          <MessageCircle size={18} /> Share via WhatsApp
        </a>
        <button className="outline-button full-button" data-testid="receipt-print-button" onClick={() => window.print()}>
          <Download size={18} /> Download / Print
        </button>
      </section>
    </div>
  );
}