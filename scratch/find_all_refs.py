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

# Pattern to find numbers like 1.1, 5.2, etc.
# Avoid matching section headers (e.g., ## 1.1) or floating point numbers (e.g., 0.35%, 1.5, 37.43)
num_pat = re.compile(r'\b\d+\.\d+\b')

# Exclude common floats in the text to reduce noise
ignored_floats = {
    '1.11', '1.5', '0.35', '0.45', '2.0', '10.0', '0.5', '1.0', '0.8',
    '37.43', '122.17', '30.0', '1.43', '81.93', '4.5', '12.0', '6.0',
    '25.0', '20.0', '15.0', '18.0', '2.0', '1.15', '1.25'
}

for ch_path in chapters:
    if not os.path.exists(ch_path):
        continue
    
    print(f"\n=================== REFERENCES IN: {ch_path} ===================")
    with open(ch_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line_str = line.strip()
            # If it's a header line, skip it
            if line_str.startswith("#"):
                continue
                
            matches = num_pat.findall(line_str)
            filtered = [m for m in matches if m not in ignored_floats]
            if filtered:
                print(f"[Line {idx}] Found {filtered} in: {line_str}")
