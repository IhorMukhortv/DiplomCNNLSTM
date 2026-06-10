import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

chapters = {
    1: "docs/thesis/chapter1.md",
    2: "docs/thesis/chapter2.md",
    3: "docs/thesis/chapter3.md",
    4: "docs/thesis/chapter4.md"
}

fig_map = {
    '1.2': '1.1',
    '1.3': '1.2',
    '1.4': '1.3',
    '2.1': '1.4',
    '4.1': '2.1',
    '5.1': '3.1',
    '5.2': '3.2',
    '6.1': '3.3',
    '7.1': '3.4',
    '8.1': '4.1'
}

tab_map = {
    '1.1': '1.1',
    '4.1': '2.1',
    '5.1': '3.1',
    '7.1': '3.2',
    '8.1': '4.1',
    '8.2': '4.2'
}

eq_map = {
    '2.1': '1.1',
    '2.2': '1.2',
    '2.3': '1.3',
    '2.4': '1.4',
    '2.5': '1.5',
    '1.1': '1.6',
    '1.2': '1.7',
    '1.3': '1.8',
    '1.4': '1.9',
    '1.5': '1.10',
    '1.6': '1.11',
    '2.6': '1.12',
    '2.7': '1.13',
    '2.8': '1.14',
    '2.9': '1.15',
    '2.10': '1.16',
    '2.11': '1.17',
    '2.12': '1.18',
    '2.13': '1.19',
    '2.14': '1.20',
    '2.15': '1.21',
    '2.16': '1.22',
    '3.1': '2.1',
    '3.2': '2.2',
    '3.3': '2.3',
    '3.4': '2.4',
    '4.1': '2.5',
    '5.1': '3.1',
    '5.2': '3.2',
    '6.1': '3.3',
    '6.2': '3.4',
    '6.3': '3.5',
    '8.1': '4.1',
    '8.2': '4.2',
    '8.3': '4.3'
}

print("=== STARTING RENUMBERING EXECUTION ===")

for ch_num, ch_path in chapters.items():
    if not os.path.exists(ch_path):
        print(f"Skipping {ch_path} (not found)")
        continue
        
    print(f"\nProcessing Chapter {ch_num} ({ch_path}):")
    
    with open(ch_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. Renumber Figures
    # Sort old numbers by length descending to prevent partial replacements if any overlap (e.g. 1.22 before 1.2)
    for old_num, new_num in sorted(fig_map.items(), key=lambda x: len(x[0]), reverse=True):
        fig_ref_pat = re.compile(rf'\b(рисунок|рисунка|рисунку|рисунком|рис\.)\s*{re.escape(old_num)}\b', re.IGNORECASE)
        def replace_fig(m):
            return f"{m.group(1)} {new_num}"
        content, count = fig_ref_pat.subn(replace_fig, content)
        if count > 0:
            print(f"  Figures: Replaced {old_num} -> {new_num} ({count} times)")
            
    # 2. Renumber Tables
    for old_num, new_num in sorted(tab_map.items(), key=lambda x: len(x[0]), reverse=True):
        tab_ref_pat = re.compile(rf'\b(таблиця|таблиці|таблицею|табл\.)\s*{re.escape(old_num)}\b', re.IGNORECASE)
        def replace_tab(m):
            return f"{m.group(1)} {new_num}"
        content, count = tab_ref_pat.subn(replace_tab, content)
        if count > 0:
            print(f"  Tables: Replaced {old_num} -> {new_num} ({count} times)")
            
    # 3. Renumber Equations
    for old_num, new_num in sorted(eq_map.items(), key=lambda x: len(x[0]), reverse=True):
        eq_ref_pat = re.compile(rf'\(\s*{re.escape(old_num)}\s*\)')
        content, count = eq_ref_pat.subn(f"({new_num})", content)
        if count > 0:
            print(f"  Equations: Replaced ({old_num}) -> ({new_num}) ({count} times)")
            
    # Write back the updated content
    with open(ch_path, "w", encoding="utf-8") as f:
        f.write(content)
        
print("\n=== RENUMBERING COMPLETED ===")
