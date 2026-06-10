import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document("docs/thesis/diploma_work.docx")

def has_image(p):
    p_el = p._p
    for elem in p_el.iter():
        tag = elem.tag
        if tag.endswith('}drawing') or tag.endswith('}pic'):
            return True
    return False

print("Scanning paragraphs for images...")
img_paragraphs_found = 0
for idx, p in enumerate(doc.paragraphs):
    if has_image(p):
        img_paragraphs_found += 1
        print(f"Paragraph {idx}:")
        print(f"  Text: {repr(p.text)}")
        print(f"  Alignment: {p.alignment} (Expected: CENTER / {WD_ALIGN_PARAGRAPH.CENTER})")
        print(f"  First Line Indent: {p.paragraph_format.first_line_indent} (Expected: 0 or None)")
        print("-" * 50)

print(f"Total image paragraphs found: {img_paragraphs_found}")
