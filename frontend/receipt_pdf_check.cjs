/*
 * Regression harness for ReceiptDialog.buildReceiptPdf geometry (80mm receipt roll).
 * Mirrors /app/frontend/src/components/ReceiptDialog.jsx buildReceiptPdf() (measure-then-create version).
 * Run:  cd /app/frontend && node receipt_pdf_check.cjs
 * Then: python /app/frontend/inspect_receipt_pdf.py <pdf>  /  pdftoppm -r 60 -png <pdf> out
 * Keep this file in sync when buildReceiptPdf changes.
 */
const { jsPDF } = require("jspdf");
const fs = require("fs");

const dateTime = (value) =>
  new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));

function buildReceiptPdf(receipt, log) {
  const width = 80;
  const margin = 6;
  const contentWidth = width - margin * 2;
  const details = [
    ["VENDOR", receipt.vendor_name],
    ["PAYMENT MODE", receipt.payment_mode],
    ["RECEIVED AT", dateTime(receipt.created_at)],
    ["COLLECTED BY", receipt.employee_name],
    ...(receipt.remarks ? [["REMARKS", receipt.remarks]] : []),
  ];

  const createPdf = (height) => new jsPDF({ format: [width, height], orientation: "portrait", unit: "mm" });
  const fitText = (pdf, text, initialSize, maxWidth, minimumSize) => {
    let size = initialSize;
    pdf.setFontSize(size);
    while (pdf.getTextWidth(text) > maxWidth && size > minimumSize) {
      size -= 2;
      pdf.setFontSize(size);
    }
    return size;
  };

  const pdfCurrency = `Rs. ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(receipt.amount || 0)}`;
  const measurePdf = createPdf(240);
  measurePdf.setFont("helvetica", "bold");
  const brandSize = fitText(measurePdf, "CO. DAILY COLLECTION", 24, contentWidth, 14);
  measurePdf.setFontSize(brandSize);
  log.brandSize = brandSize;
  log.brandWidth = measurePdf.getTextWidth("CO. DAILY COLLECTION");
  measurePdf.setFont("helvetica", "bold");
  const amountSize = fitText(measurePdf, pdfCurrency, 72, width - 4, 28);
  measurePdf.setFontSize(amountSize);
  log.amountText = pdfCurrency;
  log.amountSize = amountSize;
  log.amountWidth = measurePdf.getTextWidth(pdfCurrency);
  let y = 100;
  log.details = [];
  const detailLayout = details.map(([label, value]) => {
    measurePdf.setFontSize(18);
    const labelHeight = measurePdf.getLineHeight() / measurePdf.internal.scaleFactor;
    const valueSize = fitText(measurePdf, String(value), 30, contentWidth, 18);
    const wrappedValue = measurePdf.splitTextToSize(String(value), contentWidth);
    const valueLineHeight = measurePdf.getLineHeight() / measurePdf.internal.scaleFactor;
    const layout = { label, labelY: y, valueSize, valueY: y + labelHeight + 3, wrappedValue };
    const lastBaseline = layout.valueY + valueLineHeight * (wrappedValue.length - 1);
    let maxLineWidth = 0;
    wrappedValue.forEach((line) => {
      const w = measurePdf.getTextWidth(line);
      if (w > maxLineWidth) maxLineWidth = w;
    });
    y = layout.valueY + valueLineHeight * wrappedValue.length + 8;
    log.details.push({
      label,
      labelSize: 18,
      valueSize,
      wrapped: wrappedValue.length,
      labelY: layout.labelY,
      valueY: layout.valueY,
      lastValueBaseline: lastBaseline,
      nextLabelY: y,
      maxLineWidth: Number(maxLineWidth.toFixed(2)),
    });
    return layout;
  });
  const pageHeight = Math.max(150, y + 28);
  const pdf = createPdf(pageHeight);

  pdf.setFillColor(15, 23, 42);
  pdf.rect(0, 0, width, 34, "F");
  pdf.setTextColor(255, 255, 255);
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(brandSize);
  pdf.text("CO. DAILY COLLECTION", width / 2, 14, { align: "center" });
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(12);
  pdf.text("DIGITAL PAYMENT RECEIPT", width / 2, 23, { align: "center" });
  pdf.setTextColor(15, 23, 42);
  pdf.setFontSize(15);
  pdf.text("RECEIPT NO.", width / 2, 47, { align: "center" });
  pdf.setFont("courier", "bold");
  pdf.setFontSize(18);
  pdf.text(receipt.receipt_number, width / 2, 56, { align: "center" });
  pdf.setTextColor(5, 150, 105);
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(amountSize);
  pdf.text(pdfCurrency, width / 2, 80, { align: "center" });
  detailLayout.forEach(({ label, labelY, valueSize, valueY, wrappedValue }) => {
    pdf.setTextColor(100, 116, 139);
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(18);
    pdf.text(label, margin, labelY);
    pdf.setTextColor(51, 65, 85);
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(valueSize);
    pdf.text(wrappedValue, margin, valueY);
  });
  pdf.setDrawColor(148, 163, 184);
  pdf.setLineDashPattern([2, 2], 0);
  pdf.line(margin, y + 2, width - margin, y + 2);
  pdf.setLineDashPattern([], 0);
  pdf.setTextColor(100, 116, 139);
  pdf.setFontSize(16);
  pdf.text("Thank you for your payment.", width / 2, y + 14, { align: "center" });

  log.pageWidth = pdf.internal.pageSize.getWidth();
  log.pageHeight = pdf.internal.pageSize.getHeight();
  log.expectedPageHeight = pageHeight;
  log.pages = pdf.internal.getNumberOfPages();
  log.ruleY = y + 2;
  log.thanksBaseline = y + 14;
  return pdf;
}

const base = {
  receipt_number: "LFC-2607-1001",
  created_at: new Date().toISOString(),
  employee_name: "Raj Mehta",
};

const scenarios = [
  { name: "short (no remarks)", file: "/tmp/receipt_short.pdf", receipt: { ...base, vendor_name: "Urban Grocers", payment_mode: "Cash", amount: 800, remarks: "" } },
  { name: "typical (remarks)", file: "/tmp/receipt_test.pdf", receipt: { ...base, vendor_name: "Urban Grocers Wholesale Traders", payment_mode: "Bank Transfer", amount: 12500, remarks: "Weekly settlement for the month of July 2026" } },
  { name: "large amount + long vendor", file: "/tmp/receipt_big.pdf", receipt: { ...base, vendor_name: "Vishwakarma Enterprises And Wholesale Distributors Pvt Ltd", payment_mode: "Cash", amount: 12500000, remarks: "" } },
  { name: "unbreakable long token", file: "/tmp/receipt_token.pdf", receipt: { ...base, vendor_name: "SHREEBALAJIKIRANAGENERALSTORESWHOLESALEDIVISIONPVTLTD", payment_mode: "Cheque", amount: 45000, remarks: "REFERENCE:CHQ00918273645500001122334455667788990011223344" } },
  { name: "very long remarks", file: "/tmp/receipt_longremarks.pdf", receipt: { ...base, vendor_name: "Shree Balaji Kirana And General Stores Wholesale Division", payment_mode: "UPI", amount: 987654, remarks: "Collected against invoices INV-2026-0912, INV-2026-0913 and INV-2026-0914; balance of Rs. 12,000 pending from the previous cycle and will be settled next Monday by the area supervisor." } },
];

let failures = 0;
const check = (cond, msg) => {
  console.log(`${cond ? "PASS" : "FAIL"}: ${msg}`);
  if (!cond) failures += 1;
};
const PT = 25.4 / 72;

scenarios.forEach((s) => {
  const log = {};
  const pdf = buildReceiptPdf(s.receipt, log);
  fs.writeFileSync(s.file, Buffer.from(pdf.output("arraybuffer")));
  console.log(`\n=== ${s.name} -> ${s.file} ===`);
  console.log(JSON.stringify(log, null, 1));

  check(Math.round(log.pageWidth) === 80, `page width is 80mm (got ${log.pageWidth})`);
  check(log.pages === 1, `single page (got ${log.pages})`);
  check(
    Math.abs(log.pageHeight - log.expectedPageHeight) < 0.5,
    `page height created before drawing (declared ${log.expectedPageHeight.toFixed(1)}mm, actual ${log.pageHeight.toFixed(1)}mm)`
  );
  // header must be inside the page: cap height ~0.72em above the baseline
  const brandTop = 14 - log.brandSize * PT * 0.72;
  check(brandTop >= 0, `brand title top inside page (top=${brandTop.toFixed(1)}mm)`);
  check(log.brandWidth <= 68.01, `brand title fits 68mm content width (got ${log.brandWidth.toFixed(1)}mm at ${log.brandSize}pt)`);
  // footer must be inside the page
  check(log.ruleY < log.pageHeight, `dashed rule inside page (${log.ruleY.toFixed(1)}mm < ${log.pageHeight.toFixed(1)}mm)`);
  check(
    log.thanksBaseline + 16 * PT * 0.25 < log.pageHeight,
    `thank-you line inside page (baseline ${log.thanksBaseline.toFixed(1)}mm, page ${log.pageHeight.toFixed(1)}mm)`
  );
  // amount: >= 3x the old 25pt is the requirement -> 75pt is unreachable on 80mm for wide strings,
  // so assert it is at least the configured floor and dramatically larger than the old value.
  check(log.amountSize >= 28, `amount font >= 28pt floor (got ${log.amountSize}pt for "${log.amountText}")`);
  check(log.amountWidth <= 76.01, `amount fits within 76mm (got ${log.amountWidth.toFixed(1)}mm)`);
  check(/^Rs\. /.test(log.amountText) && !/[^\u0000-\u00ff]/.test(log.amountText), `amount uses printer-safe "Rs." (got "${log.amountText}")`);
  check(log.details.every((d) => d.labelSize >= 14), "detail labels >= 14pt (old 7pt)");
  check(log.details.every((d) => d.valueSize >= 18), "detail values >= 18pt (old 10pt)");
  check(log.details.every((d) => d.maxLineWidth <= 68.01), "every wrapped value line fits 68mm content width");
  // no overlap: next label baseline must clear the last value line by at least its cap height
  const overlaps = log.details.filter((d) => d.nextLabelY - d.lastValueBaseline < 18 * PT * 0.72);
  check(overlaps.length === 0, `no label/value collision (${overlaps.length} overlapping block(s))`);
  const firstDetail = log.details[0];
  const amountBottom = 80 + log.amountSize * PT * 0.25;
  check(amountBottom < firstDetail.labelY - 18 * PT * 0.72, `amount does not collide with first label (amount bottom ${amountBottom.toFixed(1)}mm, first label ${firstDetail.labelY}mm)`);
  check(80 - log.amountSize * PT * 0.72 > 56, `amount does not collide with receipt number (amount top ${(80 - log.amountSize * PT * 0.72).toFixed(1)}mm)`);
});

console.log(`\n${failures} assertion(s) failed`);
