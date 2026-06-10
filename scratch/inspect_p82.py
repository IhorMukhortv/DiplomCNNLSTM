import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
import xml.dom.minidom

doc = Document("docs/thesis/diploma_work.docx")

for idx in [82, 84]:
    p = doc.paragraphs[idx]
    print(f"Paragraph {idx} XML:")
    xml_str = xml.dom.minidom.parseString(p._p.xml).toprettyxml(indent="  ")
    print(xml_str)
    print("=" * 80)
