import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

content = """
Коефіцієнт кореляції Пірсона оцінює силу лінійного зв'язку і розраховується як:

$$r = \\frac{\\sum (x_i - \\bar{x})(y_i - \\bar{y})}{\\sqrt{\\sum (x_i - \\bar{x})^2 \\sum (y_i - \\bar{y})^2}}$$ (1.10)

Коефіцієнт кореляції Спірмена оцінює монотонність зв'язку (навіть якщо він нелінійний) і базується на рангах значень:

$$\\rho = 1 - \\frac{6 \\sum d_i^2}{n(n^2 - 1)}$$ (1.11)
"""

def replace_equation(match):
    formula_content = match.group(1).strip()
    eq_num = match.group(2) if len(match.groups()) >= 2 and match.group(2) else None
    
    if not eq_num:
        num_match = re.search(r'\(\s*(\d+\.\d+|\d+)\s*\)', formula_content)
        eq_num = num_match.group(0) if num_match else ""
    else:
        eq_num = eq_num.strip()
        
    formula_clean = re.sub(r'\\qquad.*$', '', formula_content).strip()
    formula_clean = re.sub(r'\\eqno.*$', '', formula_clean).strip()
    if eq_num:
        formula_clean = formula_clean.replace(eq_num, '').strip()
        formula_clean = re.sub(r'\\qquad\s*$', '', formula_clean).strip()
        formula_clean = re.sub(r'\\eqno\s*$', '', formula_clean).strip()
        
    print(f"Matched formula: {repr(formula_clean)}")
    print(f"Matched number: {repr(eq_num)}")
    
    if eq_num:
        return f"\n\n$${formula_clean}$$\n\n[EQNO: {eq_num}]\n\n"
    else:
        return f"\n\n$${formula_clean}$$\n\n"

res = re.sub(r'\$\$(.*?)\$\$(?:\s*(\(\s*\d+(?:\.\d+)*\s*\)))?', replace_equation, content, flags=re.DOTALL)
print("Result:")
print(res)
