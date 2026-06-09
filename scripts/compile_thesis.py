import os
import re
import logging
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("compile_thesis")

# Послідовність файлів розділів дипломної роботи
CHAPTER_FILES = [
    "docs/thesis/introduction.md",
    "docs/thesis/chapter1_data_collection_analysis.md",
    "docs/thesis/chapter2_theoretical_background.md",
    "docs/thesis/chapter3_model_design.md",
    "docs/thesis/chapter4_infrastructure.md",
    "docs/thesis/chapter5_training_evaluation.md",
    "docs/thesis/chapter6_online_learning.md",
    "docs/thesis/chapter7_practical_implementation.md",
    "docs/thesis/chapter8_economic_analysis.md",
    "docs/thesis/conclusions.md",
    "docs/thesis/references.md"
]

OUTPUT_DOCX = "docs/thesis/diploma_work.docx"

ROMAN_WORDS = {
    "CAPEX", "OPEX", "LCOE", "MAE", "RMSE", "MAPE", "NOCT", "STC", "GHI", 
    "DNI", "DHI", "sin", "cos", "tanh", "max", "min", "actual", "forecast", 
    "imbalance", "penalty", "scaled", "SELECT", "create_hypertable", 
    "pv_telemetry", "Persistence", "fuel", "temp", "amb", "cell", "inv"
}

GREEK_LETTERS = {
    '\\gamma': 'γ',
    '\\phi': 'φ',
    '\\delta': 'δ',
    '\\omega': 'ω',
    '\\theta': 'θ',
    '\\sigma': 'σ',
    '\\rho': 'ρ',
    '\\eta': 'η',
    '\\nu': 'ν',
    '\\beta': 'β',
    '\\alpha': 'α',
    '\\tilde{C': 'C̃',  # Handle \tilde{C}
    '\\hat{y': 'ŷ',    # Handle \hat{y}
    '\\bar{x': 'x̄',    # Handle \bar{x}
    '\\bar{y': 'ȳ',    # Handle \bar{y}
    '\\sum': '∑',
    '\\prod': '∏',
}

MATH_FUNCTIONS = ["tanh", "sin", "cos", "max", "min", "ln", "log", "exp", "lim", "deg", "det", "dim", "sup", "inf"]

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Налаштування відступів всередині комірки таблиці."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_table_borders(table):
    """
    Застосовує академічні межі до таблиці:
    - Тонка горизонтальна межа зверху та знизу таблиці.
    - Тонка горизонтальна межа під заголовком.
    - Без вертикальних меж.
    """
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            '  <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            '  <w:left w:val="none"/>'
            '  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            '  <w:right w:val="none"/>'
            '  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
            '  <w:insideV w:val="none"/>'
            '</w:tblBorders>'
        )
        tblPr[0].append(borders)

def format_run(run, font_name="Times New Roman", font_size=14, bold=False, italic=False, color_rgb=(0, 0, 0)):
    """Допоміжна функція для застосування стилю до run."""
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)

def is_valid_math(content):
    """Визначає, чи є фрагмент дійсним математичним токеном."""
    if not content or len(content) > 60:
        return False
    # Ігноруємо фрагменти, які містять типові українські слова
    for word in ['кВт', 'грн', 'рік', 'ТЕС', 'ФЕС', 'від', 'для', 'номінал', 'у', 'на', 'річних']:
        if word in content:
            return False
    # Ігноруємо фрагменти, які мають кому з пробілом та текстом (типовий перелік грошових показників)
    if re.search(r',\s+[a-zA-Zа-яА-Я]', content):
        return False
    # Ігноруємо чисті цілі або десяткові числа (це грошові суми, а не формули)
    if re.match(r'^\d+[\s\d,.]*$', content):
        return False
    return True

def tokenize_paragraph(text):
    """Токенізує параграф тексту на звичайний текст, жирний, курсив та формули."""
    tokens = []
    i = 0
    n = len(text)
    
    while i < n:
        if text[i:i+2] == '**':
            end = text.find('**', i+2)
            if end != -1:
                tokens.append(('bold', text[i+2:end]))
                i = end + 2
                continue
        if text[i] == '*':
            end = text.find('*', i+1)
            if end != -1:
                tokens.append(('italic', text[i+1:end]))
                i = end + 1
                continue
        if text[i] == '$':
            end = text.find('$', i+1)
            if end != -1:
                content = text[i+1:end]
                if is_valid_math(content):
                    tokens.append(('math', content))
                    i = end + 1
                    continue
        
        start = i
        i += 1
        while i < n:
            if text[i:i+2] == '**':
                break
            if text[i] == '*':
                break
            if text[i] == '$':
                next_dollar = text.find('$', i+1)
                if next_dollar != -1 and is_valid_math(text[i+1:next_dollar]):
                    break
            i += 1
        tokens.append(('text', text[start:i]))
        
    return tokens

def parse_braced_groups(s, start_idx):
    """Знаходить межі згрупованих фігурних дужок."""
    depth = 0
    for idx in range(start_idx, len(s)):
        if s[idx] == '{':
            depth += 1
        elif s[idx] == '}':
            depth -= 1
            if depth == 0:
                return start_idx + 1, idx
    return None

def convert_fractions(s):
    """Рекурсивно перетворює LaTeX дроби \frac{A}{B} на (A)/(B)."""
    while True:
        idx = s.find('\\frac')
        if idx == -1:
            break
        first_brace = s.find('{', idx + 5)
        if first_brace == -1:
            s = s[:idx] + " " + s[idx+5:]
            continue
        res = parse_braced_groups(s, first_brace)
        if not res:
            break
        start1, end1 = res
        second_brace = s.find('{', end1 + 1)
        if second_brace == -1 or any(c not in ' \t\n' for c in s[end1+1:second_brace]):
            s = s[:idx] + s[start1:end1] + s[end1+1:]
            continue
        res2 = parse_braced_groups(s, second_brace)
        if not res2:
            break
        start2, end2 = res2
        
        num = s[start1:end1]
        den = s[second_brace+1:end2]
        
        num = convert_fractions(num)
        den = convert_fractions(den)
        
        num_str = f"({num})" if ('+' in num or '-' in num or ' ' in num or '*' in num or '/' in num) and not (num.startswith('(') and num.endswith(')')) else num
        den_str = f"({den})" if ('+' in den or '-' in den or ' ' in den or '*' in den or '/' in den) and not (den.startswith('(') and den.endswith(')')) else den
        
        fraction_replacement = f"{num_str}/{den_str}"
        s = s[:idx] + fraction_replacement + s[end2+1:]
    return s

def convert_sqrt(s):
    """Рекурсивно перетворює LaTeX квадратні корені \sqrt{A} на √(A)."""
    while True:
        idx = s.find('\\sqrt')
        if idx == -1:
            break
        brace = s.find('{', idx + 5)
        if brace == -1:
            s = s[:idx] + "√" + s[idx+5:]
            continue
        res = parse_braced_groups(s, brace)
        if not res:
            break
        start, end = res
        content = s[start:end]
        content = convert_sqrt(content)
        replacement = f"√({content})"
        s = s[:idx] + replacement + s[end+1:]
    return s

def clean_latex_formula(text):
    """Очищує LaTeX розмітку формули та перетворює її на юнікод-символи."""
    text = re.sub(r'<p align="center">', '', text)
    text = re.sub(r'</p>', '', text)
    text = re.sub(r'\\qquad.*$', '', text)
    text = re.sub(r'\\eqno.*$', '', text)
    
    # Попереднє очищення комбінованих символів із фігурними дужками
    text = text.replace('\\tilde{C}', 'C̃')
    text = text.replace('\\hat{y}', 'ŷ')
    text = text.replace('\\bar{x}', 'x̄')
    text = text.replace('\\bar{y}', 'ȳ')
    
    # Захист блоків \text{...} від обробки підрядкових/надрядкових індексів
    text = re.sub(r'\\text\s*\{([^{}]+)\}', r'«\1»', text)
    
    text = convert_fractions(text)
    text = convert_sqrt(text)
    
    # Заміна грецьких літер та математичних сум
    for lat, uni in GREEK_LETTERS.items():
        text = text.replace(lat, uni)
        
    for func in MATH_FUNCTIONS:
        text = text.replace(f'\\{func}', func)
        
    text = text.replace('\\times', ' × ')
    text = text.replace('\\cdot', ' · ')
    text = text.replace('\\odot', ' ⊙ ')
    text = text.replace('\\approx', ' ≈ ')
    text = text.replace('\\pm', ' ± ')
    text = text.replace('\\ge', ' ≥ ')
    text = text.replace('\\le', ' ≤ ')
    text = text.replace('\\left|', '|')
    text = text.replace('\\right|', '|')
    text = text.replace('\\left(', '(')
    text = text.replace('\\right)', ')')
    text = text.replace('\\left[', '[')
    text = text.replace('\\right]', ']')
    text = text.replace('\\qquad', '   ')
    
    text = text.replace('\\,', ' ')
    text = text.replace('\\;', ' ')
    text = text.replace('\\!', '')
    text = text.replace('\\%', '%')
    text = text.replace('\\_', '_')
    text = text.replace('\\#', '#')
    
    return text.strip()

def parse_math_to_runs(text):
    """Розбиває математичну формулу на окремі фрагменти (runs) з індексами."""
    runs = [] # список кортежів (вміст, is_sub, is_super, is_plain)
    i = 0
    n = len(text)
    while i < n:
        char = text[i]
        if char == '«':
            end = text.find('»', i+1)
            if end != -1:
                runs.append((text[i+1:end], False, False, True))
                i = end + 1
                continue
        if char == '_':
            i += 1
            if i < n and text[i] == '{':
                start = i + 1
                depth = 1
                end = start
                while end < n and depth > 0:
                    if text[end] == '{':
                        depth += 1
                    elif text[end] == '}':
                        depth -= 1
                    end += 1
                runs.append((text[start:end-1], True, False, False))
                i = end
            else:
                start = i
                while i < n and (text[i].isalnum() or text[i] == '-'):
                    i += 1
                runs.append((text[start:i], True, False, False))
        elif char == '^':
            i += 1
            if i < n and text[i] == '{':
                start = i + 1
                depth = 1
                end = start
                while end < n and depth > 0:
                    if text[end] == '{':
                        depth += 1
                    elif text[end] == '}':
                        depth -= 1
                    end += 1
                runs.append((text[start:end-1], False, True, False))
                i = end
            else:
                start = i
                while i < n and (text[i].isalnum() or text[i] in '+-'):
                    i += 1
                runs.append((text[start:i], False, True, False))
        else:
            start = i
            while i < n and text[i] not in ('_', '^', '«'):
                i += 1
            runs.append((text[start:i], False, False, False))
    return runs

def add_math_run_to_paragraph(p, text, is_sub, is_super, is_plain=False, font_size=14):
    """Додає математичний фрагмент до параграфа з виділенням курсивом змінних."""
    text = text.replace('«', '').replace('»', '')
    if is_plain:
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(font_size)
        r.font.color.rgb = RGBColor(0, 0, 0)
        if is_sub:
            r.font.subscript = True
        elif is_super:
            r.font.superscript = True
        r.italic = False
        return
        
    parts = re.split(r'([a-zA-Zа-яА-ЯёЁіІїЇєЄґҐα-ωΑ-Ωθ̃́̄\d]+)', text)
    for part in parts:
        if not part:
            continue
        r = p.add_run(part)
        r.font.name = "Times New Roman"
        r.font.size = Pt(font_size)
        r.font.color.rgb = RGBColor(0, 0, 0)
        
        if is_sub:
            r.font.subscript = True
        elif is_super:
            r.font.superscript = True
            
        # Застосування курсиву до літерних змінних, крім констант та абревіатур з ROMAN_WORDS
        if part[0].isalpha():
            if part in ROMAN_WORDS:
                r.italic = False
            else:
                r.italic = True
        else:
            r.italic = False

def clean_text_backslashes(text):
    """Очищає екрановані символи у звичайному тексті."""
    text = text.replace('\\%', '%')
    text = text.replace('\\_', '_')
    text = text.replace('\\#', '#')
    text = text.replace('\\$', '$')
    text = text.replace('\\&', '&')
    text = text.replace('\\{', '{')
    text = text.replace('\\}', '}')
    return text

def add_runs_to_paragraph(p, text, font_size=14):
    """Додає форматовані фрагменти тексту до параграфа."""
    tokens = tokenize_paragraph(text)
    for tok_type, tok_val in tokens:
        if tok_type == 'bold':
            val_clean = clean_text_backslashes(tok_val)
            run = p.add_run(val_clean)
            format_run(run, font_size=font_size, bold=True)
        elif tok_type == 'italic':
            val_clean = clean_text_backslashes(tok_val)
            run = p.add_run(val_clean)
            format_run(run, font_size=font_size, italic=True)
        elif tok_type == 'math':
            math_clean = clean_latex_formula(tok_val)
            math_runs = parse_math_to_runs(math_clean)
            for m_content, is_sub, is_super, is_plain in math_runs:
                add_math_run_to_paragraph(p, m_content, is_sub, is_super, is_plain, font_size=font_size)
        else:
            val_clean = clean_text_backslashes(tok_val)
            run = p.add_run(val_clean)
            format_run(run, font_size=font_size)

def add_formatted_paragraph(doc, text, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=Inches(0.5), space_after=6, space_before=0, line_spacing=1.5):
    """Додає параграф тексту, згенерований за вимогами ДСТУ."""
    p = doc.add_paragraph()
    p.alignment = alignment
    p.paragraph_format.first_line_indent = first_line_indent
    p.paragraph_format.line_spacing = line_spacing
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    
    add_runs_to_paragraph(p, text, font_size=14)
    return p

def parse_markdown_table(block_lines):
    """Парсить таблицю у форматі Markdown і повертає список рядків."""
    table_data = []
    alignments = []
    
    for line in block_lines:
        line = line.strip()
        if not line.startswith('|') or not line.endswith('|'):
            continue
        
        # Розділяємо по стовпцях, ігноруючи порожні елементи по боках
        cells = [c.strip() for c in line.split('|')[1:-1]]
        
        # Перевірка на розділювач вирівнювання (наприклад, | :--- | :---: |)
        if all(re.match(r'^:?-+:?$', c) for c in cells):
            for c in cells:
                if c.startswith(':') and c.endswith(':'):
                    alignments.append(WD_ALIGN_PARAGRAPH.CENTER)
                elif c.endswith(':'):
                    alignments.append(WD_ALIGN_PARAGRAPH.RIGHT)
                else:
                    alignments.append(WD_ALIGN_PARAGRAPH.LEFT)
            continue
            
        table_data.append(cells)
        
    if not alignments and table_data:
        alignments = [WD_ALIGN_PARAGRAPH.LEFT] * len(table_data[0])
        
    return table_data, alignments

def compile_markdown_to_docx():
    logger.info("Створення порожнього Word документа...")
    doc = Document()

    # Налаштування полів сторінки відповідно до ДСТУ
    for section in doc.sections:
        section.top_margin = Inches(0.787)      # 20 мм
        section.bottom_margin = Inches(0.787)   # 20 мм
        section.left_margin = Inches(0.984)     # 25 мм
        section.right_margin = Inches(0.59)      # 15 мм

    first_chapter = True

    for file_path in CHAPTER_FILES:
        if not os.path.exists(file_path):
            logger.warning(f"Файл {file_path} не знайдено, пропуск.")
            continue
            
        logger.info(f"Обробка файлу: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Розбиваємо вміст файлу на блоки
        blocks = re.split(r'\n\s*\n', content)
        in_list = False

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split('\n')
            first_line = lines[0].strip()

            # --- Обробка заголовків ---
            if first_line.startswith('# '):
                # Заголовок Розділу/Вступу/Висновків (Heading 1)
                heading_text = first_line[2:].strip()
                
                # Додаємо розрив сторінки перед кожним розділом, крім вступу
                if not first_chapter:
                    doc.add_page_break()
                else:
                    first_chapter = False
                
                # За вимогами ДСТУ, назви розділів пишуться великими літерами, по центру, напівжирним 14 пт
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(18)
                p.paragraph_format.line_spacing = 1.5
                
                heading_clean = clean_text_backslashes(heading_text)
                run = p.add_run(heading_clean.upper())
                format_run(run, font_size=14, bold=True)
                in_list = False
                continue

            elif first_line.startswith('## '):
                # Заголовок підрозділу (Heading 2)
                heading_text = first_line[3:].strip()
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(12)
                p.paragraph_format.line_spacing = 1.5
                
                heading_clean = clean_text_backslashes(heading_text)
                run = p.add_run(heading_clean)
                format_run(run, font_size=14, bold=True)
                in_list = False
                continue

            elif first_line.startswith('### '):
                # Заголовок пункту (Heading 3)
                heading_text = first_line[4:].strip()
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.line_spacing = 1.5
                
                heading_clean = clean_text_backslashes(heading_text)
                run = p.add_run(heading_clean)
                format_run(run, font_size=14, bold=True, italic=True)
                in_list = False
                continue

            # --- Обробка таблиць ---
            if first_line.startswith('|') and len(lines) > 1 and '|' in lines[1]:
                table_data, alignments = parse_markdown_table(lines)
                if not table_data:
                    continue
                
                rows_count = len(table_data)
                cols_count = len(table_data[0])
                
                # Додаємо таблицю в документ
                table = doc.add_table(rows=rows_count, cols=cols_count)
                table.alignment = WD_ALIGN_PARAGRAPH.CENTER
                set_table_borders(table)
                
                # Заповнюємо дані
                for r_idx, row_cells in enumerate(table_data):
                    for c_idx, cell_value in enumerate(row_cells):
                        if c_idx >= cols_count:
                            continue
                        cell = table.cell(r_idx, c_idx)
                        set_cell_margins(cell)
                        
                        # Додаємо та форматуємо текст у комірці
                        cell_p = cell.paragraphs[0]
                        cell_p.alignment = alignments[c_idx] if c_idx < len(alignments) else WD_ALIGN_PARAGRAPH.LEFT
                        cell_p.paragraph_format.line_spacing = 1.15
                        cell_p.paragraph_format.space_after = Pt(2)
                        cell_p.paragraph_format.space_before = Pt(2)
                        cell_p.paragraph_format.first_line_indent = Inches(0)
                        
                        add_runs_to_paragraph(cell_p, cell_value, font_size=12)
                
                # Додаємо порожній рядок після таблиці для візуального відступу
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                in_list = False
                continue

            # --- Обробка зображень ---
            img_match = re.search(r'!\[(.*?)\]\((.*?)\)', block)
            if img_match:
                caption = img_match.group(1)
                img_path = img_match.group(2)
                
                # Нормалізуємо шлях зображення
                if img_path.startswith('/'):
                    img_path = img_path[1:]
                img_path = img_path.replace('/', os.sep)
                
                if os.path.exists(img_path):
                    # Вставляємо зображення (центроване)
                    p_img = doc.add_paragraph()
                    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_img.paragraph_format.space_before = Pt(12)
                    p_img.paragraph_format.space_after = Pt(6)
                    p_img.paragraph_format.first_line_indent = Inches(0)
                    
                    run_img = p_img.add_run()
                    run_img.add_picture(img_path, width=Inches(6.0))
                    
                    # Додаємо підпис під рисунком ( Times New Roman, 12 пт, курсив, по центру)
                    p_cap = doc.add_paragraph()
                    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_cap.paragraph_format.space_before = Pt(0)
                    p_cap.paragraph_format.space_after = Pt(12)
                    p_cap.paragraph_format.first_line_indent = Inches(0)
                    
                    run_cap = p_cap.add_run(f"Рисунок. {caption}" if caption else "Рисунок")
                    format_run(run_cap, font_size=12, italic=True)
                else:
                    logger.warning(f"Зображення {img_path} не знайдено, пропускаємо вставку картини.")
                    # Вставляємо просто плейсхолдер
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run(f"[Рисунок: {caption} (файл {img_path} відсутній)]")
                    format_run(run, italic=True)
                in_list = False
                continue

            # Також обробляємо центрований підпис рисунка в HTML стилі
            html_cap_match = re.search(r'<p align="center"><em>(.*?)</em></p>', block)
            if html_cap_match:
                caption_text = html_cap_match.group(1)
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(12)
                p.paragraph_format.first_line_indent = Inches(0)
                run = p.add_run(caption_text)
                format_run(run, font_size=12, italic=True)
                in_list = False
                continue

            # --- Обробка блок-формул $$ ---
            # Формули розміщуються по центру, номер формули — праворуч за допомогою tab stops
            if '$$' in block:
                formula_match = re.search(r'\$\$\s*(.*?)\s*\$\$', block, re.DOTALL)
                if formula_match:
                    formula_content = formula_match.group(1).strip()
                    formula_clean = clean_latex_formula(formula_content)
                    
                    # Шукаємо номер формули в усьому блоці (а не лише всередині $$)
                    num_match = re.search(r'\(\s*(?:\d+\.\d+|\d+)\s*\)', block)
                    formula_num = num_match.group(0) if num_match else ""
                    
                    p = doc.add_paragraph()
                    # Налаштування табуляції для центрування формули та притискання номеру праворуч
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(3.35), alignment=WD_TAB_ALIGNMENT.CENTER)
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.70), alignment=WD_TAB_ALIGNMENT.RIGHT)
                    p.paragraph_format.first_line_indent = Inches(0)
                    p.paragraph_format.space_before = Pt(6)
                    p.paragraph_format.space_after = Pt(6)
                    p.paragraph_format.line_spacing = 1.5
                    
                    p.add_run('\t')
                    
                    math_runs = parse_math_to_runs(formula_clean)
                    for m_content, is_sub, is_super, is_plain in math_runs:
                        add_math_run_to_paragraph(p, m_content, is_sub, is_super, is_plain, font_size=14)
                        
                    if formula_num:
                        p.add_run('\t')
                        run_num = p.add_run(formula_num)
                        format_run(run_num, font_size=14)
                        
                    in_list = False
                    continue

            # --- Обробка списків ---
            if first_line.startswith('- ') or first_line.startswith('* '):
                # Маркований список
                for line in lines:
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('* '):
                        item_text = line[2:].strip()
                        p = doc.add_paragraph(style='List Bullet')
                        p.paragraph_format.space_after = Pt(3)
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.line_spacing = 1.5
                        p.paragraph_format.first_line_indent = Inches(0)
                        
                        add_runs_to_paragraph(p, item_text, font_size=14)
                in_list = True
                continue

            elif re.match(r'^\d+\.\s', first_line):
                # Нумерований список
                for line in lines:
                    line = line.strip()
                    match = re.match(r'^(\d+\.)\s*(.*)$', line)
                    if match:
                        num_prefix = match.group(1)
                        item_text = match.group(2)
                        p = doc.add_paragraph(style='List Number')
                        p.paragraph_format.space_after = Pt(3)
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.line_spacing = 1.5
                        p.paragraph_format.first_line_indent = Inches(0)
                        
                        add_runs_to_paragraph(p, item_text, font_size=14)
                in_list = True
                continue

            # --- Звичайний абзац тексту ---
            # Об'єднуємо розбиті рядки в один суцільний абзац
            paragraph_text = " ".join([l.strip() for l in lines if l.strip()])
            
            # Ігноруємо специфічні теги розриву або пусті HTML
            if paragraph_text.startswith('<p') or paragraph_text.startswith('</p') or paragraph_text.startswith('---'):
                continue
                
            add_formatted_paragraph(doc, paragraph_text)
            in_list = False

    # Створення директорії для вихідного файлу, якщо вона відсутня
    output_dir = os.path.dirname(OUTPUT_DOCX)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Збереження документа
    logger.info(f"Збереження скомпільованого Word документа у: {OUTPUT_DOCX}")
    doc.save(OUTPUT_DOCX)
    logger.info("Успішно завершено!")

if __name__ == "__main__":
    compile_markdown_to_docx()
