import { useRef, useState } from "react";
import html2canvas from "html2canvas";
import { Image, MessageCircle, Printer, X } from "lucide-react";
import { dateTime } from "@/lib/api";

export default function ReceiptDialog({ receipt, onClose }) {
  const receiptContentRef = useRef(null);
  const [isPreparing, setIsPreparing] = useState(false);
  const [exportError, setExportError] = useState("");

  if (!receipt) return null;

  const fileName = `Co-Daily-Collection-${receipt.receipt_number}.jpg`;
  const plainAmount = new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0,
  }).format(receipt.amount || 0);

  const createReceiptImage = async () => {
    if (!receiptContentRef.current) throw new Error("Receipt preview is unavailable");
    await document.fonts?.ready;
    const canvas = await html2canvas(receiptContentRef.current, {
      backgroundColor: "#ffffff",
      logging: false,
      scale: 3,
      useCORS: true,
    });
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error("Could not create receipt image"));
      }, "image/jpeg", 0.95);
    });
  };

  const downloadImage = (blob) => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = fileName;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  };

  const runImageAction = async (action) => {
    setIsPreparing(true);
    setExportError("");
    try {
      const image = await createReceiptImage();
      await action(image);
    } catch (error) {
      console.error("Receipt image export failed", error);
      setExportError("Could not create the receipt image. Please try again.");
    } finally {
      setIsPreparing(false);
    }
  };

  const downloadReceipt = () => runImageAction(async (image) => downloadImage(image));

  const shareReceipt = () => runImageAction(async (image) => {
    const file = new File([image], fileName, { type: "image/jpeg" });
    if (navigator.share && (!navigator.canShare || navigator.canShare({ files: [file] }))) {
      try {
        await navigator.share({ files: [file], title: "Co. Daily Collection receipt" });
        return;
      } catch (error) {
        if (error.name === "AbortError") return;
      }
    }
    downloadImage(image);
  });

  const printReceipt = () => runImageAction(async (image) => {
    const imageUrl = URL.createObjectURL(image);
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      downloadImage(image);
      URL.revokeObjectURL(imageUrl);
      return;
    }
    printWindow.document.write(`<img alt="Receipt" src="${imageUrl}" style="display:block;width:100%;height:auto">`);
    printWindow.document.close();
    let printStarted = false;
    const startPrint = () => {
      if (!printStarted && !printWindow.closed) {
        printStarted = true;
        printWindow.focus();
        printWindow.print();
      }
    };
    printWindow.onload = () => {
      window.setTimeout(startPrint, 400);
    };
    window.setTimeout(startPrint, 1600);
    window.setTimeout(() => URL.revokeObjectURL(imageUrl), 60000);
  });

  return (
    <div className="dialog-backdrop" role="presentation">
      <section aria-modal="true" aria-label="Digital receipt" className="receipt-dialog" data-testid="receipt-dialog">
        <button aria-label="Close receipt" className="icon-button receipt-close" data-testid="receipt-close-button" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="receipt-print-content" ref={receiptContentRef}>
          <div className="receipt-brand" data-testid="receipt-company-name">CO. DAILY COLLECTION</div>
          <div className="receipt-rule" />
          <p className="receipt-label" data-testid="receipt-number-label">RECEIPT NO.</p>
          <p className="receipt-id" data-testid="receipt-number">{receipt.receipt_number}</p>
          <div className="receipt-total" data-testid="receipt-amount">{plainAmount}</div>
          <div className="receipt-details">
            <p data-testid="receipt-vendor"><span>VENDOR</span>{receipt.vendor_name}</p>
            <p data-testid="receipt-payment"><span>PAYMENT MODE</span>{receipt.payment_mode}</p>
            <p data-testid="receipt-datetime"><span>RECEIVED AT</span>{dateTime(receipt.created_at)}</p>
            <p data-testid="receipt-employee"><span>COLLECTED BY</span>{receipt.employee_name}</p>
            {receipt.remarks && <p data-testid="receipt-remarks"><span>REMARKS</span>{receipt.remarks}</p>}
          </div>
          <div className="receipt-rule" />
          <p className="receipt-thanks" data-testid="receipt-thanks-message">Thank you for your payment.</p>
        </div>
        {exportError && <p className="receipt-export-error" data-testid="receipt-export-error">{exportError}</p>}
        <button className="whatsapp-button" data-testid="receipt-whatsapp-share" disabled={isPreparing} onClick={shareReceipt}>
          <MessageCircle size={18} /> {isPreparing ? "Preparing image…" : "Share receipt image"}
        </button>
        <button className="outline-button full-button" data-testid="receipt-download-button" disabled={isPreparing} onClick={downloadReceipt}>
          <Image size={18} /> Download this receipt image
        </button>
        <button className="outline-button full-button" data-testid="receipt-print-button" disabled={isPreparing} onClick={printReceipt}>
          <Printer size={18} /> Print this receipt image
        </button>
      </section>
    </div>
  );
}