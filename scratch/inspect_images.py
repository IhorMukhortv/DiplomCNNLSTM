import docx
from docx.shared import Inches, Cm
import os

docx_path = r"C:\Users\igorl\Documents\antigravity\dazzling-rutherford\docs\thesis\diploma_work.docx"
if not os.path.exists(docx_path):
    print("Document not found.")
    exit(1)

doc = docx.Document(docx_path)
print(f"Total inline shapes (images/diagrams): {len(doc.inline_shapes)}")
for idx, shape in enumerate(doc.inline_shapes, 1):
    w_cm = shape.width.cm if shape.width else 0
    h_cm = shape.height.cm if shape.height else 0
    print(f"Shape {idx}: type={shape.type}, width={w_cm:.2f} cm, height={h_cm:.2f} cm")
