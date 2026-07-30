import { Download, MessageCircle, Printer, X } from "lucide-react";
import { jsPDF } from "jspdf";
import { currency, dateTime } from "@/lib/api";

export default function ReceiptDialog({ receipt, onClose }) {
  if (!receipt) return null;

  const fileName = `Co-Daily-Collection-${receipt.receipt_number}.pdf`;

  const buildReceiptPdf = () => {
    const pdf = new jsPDF({ format: "a5", orientation: "portrait", unit: "mm" });
    const width = pdf.internal.pageSize.getWidth();
    const lines = [
      ["VENDOR", receipt.vendor_name],
      ["PAYMENT MODE", receipt.payment_mode],
      ["RECEIVED AT", dateTime(receipt.created_at)],
      ["COLLECTED BY", receipt.employee_name],
      ...(receipt.remarks ? [["REMARKS", receipt.remarks]] : []),
    ];

    pdf.setFillColor(15, 23, 42);
    pdf.rect(0, 0, width, 42, "F");
    pdf.setTextColor(255, 255, 255);
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(14);
    pdf.text("CO. DAILY COLLECTION", width / 2, 16, { align: "center" });
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(8);
    pdf.text("DIGITAL PAYMENT RECEIPT", width / 2, 23, { align: "center" });
    pdf.setTextColor(15, 23, 42);
    pdf.setFontSize(8);
    pdf.text("RECEIPT NO.", width / 2, 55, { align: "center" });
    pdf.setFont("courier", "bold");
    pdf.setFontSize(10);
    pdf.text(receipt.receipt_number, width / 2, 62, { align: "center" });
    pdf.setTextColor(5, 150, 105);
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(25);
    pdf.text(currency(receipt.amount), width / 2, 78, { align: "center" });
    let y = 94;
    lines.forEach(([label, value]) => {
      pdf.setTextColor(100, 116, 139);
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(7);
      pdf.text(label, 18, y);
      pdf.setTextColor(51, 65, 85);
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(10);
      const wrappedValue = pdf.splitTextToSize(value, width - 36);
      pdf.text(wrappedValue, 18, y + 6);
      y += 13 + (wrappedValue.length - 1) * 5;
    });
    pdf.setDrawColor(148, 163, 184);
    pdf.setLineDashPattern([1.5, 1.5], 0);
    pdf.line(18, y + 2, width - 18, y + 2);
    pdf.setLineDashPattern([], 0);
    pdf.setTextColor(100, 116, 139);
    pdf.setFontSize(9);
    pdf.text("Thank you for your payment.", width / 2, y + 12, { align: "center" });
    return pdf;
  };

  const downloadReceipt = () => buildReceiptPdf().save(fileName);

  const shareReceipt = async () => {
    const blob = buildReceiptPdf().output("blob");
    const file = new File([blob], fileName, { type: "application/pdf" });
    if (navigator.share && (!navigator.canShare || navigator.canShare({ files: [file] }))) {
      try {
        await navigator.share({ files: [file], title: "Co. Daily Collection receipt" });
        return;
      } catch (error) {
        if (error.name === "AbortError") return;
      }
    }
    downloadReceipt();
  };

  const printReceipt = () => {
    const pdfUrl = URL.createObjectURL(buildReceiptPdf().output("blob"));
    const printWindow = window.open(pdfUrl, "_blank");
    if (printWindow) {
      printWindow.addEventListener("load", () => printWindow.print(), { once: true });
    }
    window.setTimeout(() => URL.revokeObjectURL(pdfUrl), 60000);
  };

  return (
    <div className="dialog-backdrop" role="presentation">
      <section aria-modal="true" aria-label="Digital receipt" className="receipt-dialog" data-testid="receipt-dialog">
        <button aria-label="Close receipt" className="icon-button receipt-close" data-testid="receipt-close-button" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="receipt-brand" data-testid="receipt-company-name">CO. DAILY COLLECTION</div>
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
        <button className="whatsapp-button" data-testid="receipt-whatsapp-share" onClick={shareReceipt}>
          <MessageCircle size={18} /> Share receipt PDF
        </button>
        <button className="outline-button full-button" data-testid="receipt-download-button" onClick={downloadReceipt}>
          <Download size={18} /> Download this receipt PDF
        </button>
        <button className="outline-button full-button" data-testid="receipt-print-button" onClick={printReceipt}>
          <Printer size={18} /> Print this receipt only
        </button>
      </section>
    </div>
  );
}