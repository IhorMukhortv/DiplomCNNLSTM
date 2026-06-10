import os
import re
import sys

# Configure output to support Ukrainian/Russian characters on Windows console
sys.stdout.reconfigure(encoding='utf-8')

chapters = [
    "docs/thesis/introduction.md",
    "docs/thesis/chapter1.md",
    "docs/thesis/chapter2.md",
    "docs/thesis/chapter3.md",
    "docs/thesis/chapter4.md",
    "docs/thesis/conclusions.md"
]

fig_def_pat = re.compile(r'Рисунок\.?\s*(\d+\.\d+)', re.IGNORECASE)
tab_def_pat = re.compile(r'Таблиця\s*(\d+\.\d+)', re.IGNORECASE)
eq_def_pat = re.compile(r'\(\s*(\d+\.\d+)\s*\)') # inside/outside formulas

# We want to trace:
# 1. Definitions
# 2. Potential in-text references

for ch_path in chapters:
    if not os.path.exists(ch_path):
        print(f"Skipping {ch_path} (does not exist)")
        continue
    
    print(f"\n=================== ANALYZING: {ch_path} ===================")
    with open(ch_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for idx, line in enumerate(lines, 1):
        # Check figures
        fig_defs = fig_def_pat.findall(line)
        if fig_defs:
            print(f"[Line {idx}] Figure ref/def: {fig_defs} -> {line.strip()}")
            
        # Check tables
        tab_defs = tab_def_pat.findall(line)
        if tab_defs:
            print(f"[Line {idx}] Table ref/def: {tab_defs} -> {line.strip()}")
            
        # Check equations
        # Only check line if it contains $$ or is close to it, or let's search for (X.Y) references
        eq_refs = eq_def_pat.findall(line)
        if eq_refs:
            # check if it is part of formula
            is_formula = "$$" in line
            print(f"[Line {idx}] Parentheses number (eq or ref?): {eq_refs} -> {line.strip()}")
