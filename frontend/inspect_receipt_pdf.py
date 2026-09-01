import sys
from pypdf import PdfReader

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/receipt_test.pdf"
r = PdfReader(path)
print("pages:", len(r.pages))
p = r.pages[0]
box = p.mediabox
print("mediabox pt:", float(box.width), float(box.height))
print("mediabox mm: %.2f x %.2f" % (float(box.width)/72*25.4, float(box.height)/72*25.4))
print("---- extracted text ----")
txt = p.extract_text()
print(repr(txt))
print("---- font sizes / positions ----")
items = []
def visitor(text, cm, tm, font_dict, font_size):
    t = text.strip()
    if t:
        items.append((round(tm[5], 1), round(tm[4], 1), round(font_size, 1), t))
p.extract_text(visitor_text=visitor)
for y, x, fs, t in items:
    print(f"y_pt={y:8} (mm={y/72*25.4:7.1f})  x_pt={x:7}  size={fs:6}  {t!r}")
