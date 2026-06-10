import os
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

chapters = [
    "docs/thesis/introduction.md",
    "docs/thesis/chapter1.md",
    "docs/thesis/chapter2.md",
    "docs/thesis/chapter3.md",
    "docs/thesis/chapter4.md",
    "docs/thesis/conclusions.md"
]

for ch in chapters:
    if not os.path.exists(ch):
        continue
    with open(ch, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for idx, line in enumerate(lines):
        if "![" in line:
            print(f"{ch} Line {idx+1}: {repr(line)}")
            # check previous line
            if idx > 0:
                print(f"  Prev line: {repr(lines[idx-1])}")
            else:
                print("  Prev line: (start of file)")
            # check next line
            if idx < len(lines) - 1:
                print(f"  Next line: {repr(lines[idx+1])}")
            else:
                print("  Next line: (end of file)")
            print("-" * 40)
