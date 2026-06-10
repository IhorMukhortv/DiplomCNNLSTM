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

# Regexes
fig_def_pat = re.compile(r'Рисунок\.?\s*(\d+\.\d+)\.?\s*', re.IGNORECASE)
tab_def_pat = re.compile(r'\*\*Таблиця\s*(\d+\.\d+)\.?\s*', re.IGNORECASE)
eq_line_pat = re.compile(r'\$\$(.*?)\$\$\s*\((\d+\.\d+)\)')
eq_inline_pat = re.compile(r'\$\$(.*?)(?:\\qquad|\\eqno|\s)\s*\((\d+\.\d+)\)\s*\$\$')

print("=== GLOBAL DRY RUN RENUMBERING ===")

# Pass 1: Collect definitions globally
global_fig_map = {} # old_num -> new_num
global_tab_map = {}
global_eq_map = {}

# Keep track of where each definition was found
def_locations = {}

for ch_num, ch_path in chapters.items():
    if not os.path.exists(ch_path):
        continue
    with open(ch_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        
    fig_seq = 1
    tab_seq = 1
    eq_seq = 1
    
    for idx, line in enumerate(lines, 1):
        # Figures
        if "Рисунок" in line and ("<p align" in line or "<em>" in line):
            m = fig_def_pat.search(line)
            if m:
                old_num = m.group(1)
                new_num = f"{ch_num}.{fig_seq}"
                global_fig_map[old_num] = new_num
                def_locations[('fig', old_num)] = (ch_num, idx)
                fig_seq += 1
        
        # Tables
        if "**Таблиця" in line:
            m = tab_def_pat.search(line)
            if m:
                old_num = m.group(1)
                new_num = f"{ch_num}.{tab_seq}"
                global_tab_map[old_num] = new_num
                def_locations[('tab', old_num)] = (ch_num, idx)
                tab_seq += 1
                
        # Equations
        m_out = eq_line_pat.search(line)
        if m_out:
            old_num = m_out.group(2)
            new_num = f"{ch_num}.{eq_seq}"
            global_eq_map[old_num] = new_num
            def_locations[('eq', old_num)] = (ch_num, idx)
            eq_seq += 1
        else:
            m_in = eq_inline_pat.search(line)
            if m_in:
                old_num = m_in.group(2)
                new_num = f"{ch_num}.{eq_seq}"
                global_eq_map[old_num] = new_num
                def_locations[('eq', old_num)] = (ch_num, idx)
                eq_seq += 1

print("\n--- GLOBAL DEFINITION MAPS ---")
print("Figures:")
for k, v in sorted(global_fig_map.items()):
    loc = def_locations[('fig', k)]
    print(f"  {k} -> {v} (Chapter {loc[0]}, line {loc[1]})")
print("Tables:")
for k, v in sorted(global_tab_map.items()):
    loc = def_locations[('tab', k)]
    print(f"  {k} -> {v} (Chapter {loc[0]}, line {loc[1]})")
print("Equations:")
for k, v in sorted(global_eq_map.items()):
    loc = def_locations[('eq', k)]
    print(f"  {k} -> {v} (Chapter {loc[0]}, line {loc[1]})")

# Pass 2: Scan all chapters for references using the global maps
print("\n--- IN-TEXT REFERENCES SCAN ---")
for ch_num, ch_path in chapters.items():
    if not os.path.exists(ch_path):
        continue
    with open(ch_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        
    print(f"\nScanning Chapter {ch_num} ({ch_path}):")
    for idx, line in enumerate(lines, 1):
        # 1. Check figures
        for old_num, new_num in global_fig_map.items():
            fig_ref_pat = re.compile(rf'\b(рисунок|рисунка|рисунку|рисунком|рис\.)\s*{re.escape(old_num)}\b', re.IGNORECASE)
            matches = fig_ref_pat.findall(line)
            if matches:
                # Is it the definition line in its own chapter?
                is_def = (('fig', old_num) in def_locations and def_locations[('fig', old_num)] == (ch_num, idx))
                label = "FIGURE DEF" if is_def else "FIGURE REF"
                print(f"  Line {idx} [{label}]: '{matches}' containing {old_num} -> change to {new_num}")
                
        # 2. Check tables
        for old_num, new_num in global_tab_map.items():
            tab_ref_pat = re.compile(rf'\b(таблиця|таблиці|таблицею|табл\.)\s*{re.escape(old_num)}\b', re.IGNORECASE)
            matches = tab_ref_pat.findall(line)
            if matches:
                is_def = (('tab', old_num) in def_locations and def_locations[('tab', old_num)] == (ch_num, idx))
                label = "TABLE DEF" if is_def else "TABLE REF"
                print(f"  Line {idx} [{label}]: '{matches}' containing {old_num} -> change to {new_num}")
                
        # 3. Check equations
        for old_num, new_num in global_eq_map.items():
            eq_ref_pat = re.compile(rf'\(\s*{re.escape(old_num)}\s*\)')
            matches = eq_ref_pat.findall(line)
            if matches:
                is_def = (('eq', old_num) in def_locations and def_locations[('eq', old_num)] == (ch_num, idx))
                label = "EQ DEF" if is_def else "EQ REF"
                print(f"  Line {idx} [{label}]: '{matches}' containing {old_num} -> change to {new_num}")
