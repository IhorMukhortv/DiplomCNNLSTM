import os
import re
import logging
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
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

def add_formatted_paragraph(doc, text, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=Inches(0.5), space_after=6, space_before=0, line_spacing=1.5):
    """
    Додає параграф і парсить базові inline-елементи:
    - **bold** -> жирний
    - *italic* -> курсив
    - $math$ -> курсив (змінні/формули)
    """
    p = doc.add_paragraph()
    p.alignment = alignment
    p.paragraph_format.first_line_indent = first_line_indent
    p.paragraph_format.line_spacing = line_spacing
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)

    # Регулярний вираз для токенізації жирного, курсива та вбудованих формул
    tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*|\$.*?\$)', text)
    for token in tokens:
        if not token:
            continue
        
        if token.startswith('**') and token.endswith('**'):
            run = p.add_run(token[2:-2])
            format_run(run, bold=True)
        elif token.startswith('*') and token.endswith('*'):
            run = p.add_run(token[1:-1])
            format_run(run, italic=True)
        elif token.startswith('$') and token.endswith('$'):
            run = p.add_run(token[1:-1])
            format_run(run, italic=True)
        else:
            run = p.add_run(token)
            format_run(run)
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
                run = p.add_run(heading_text.upper())
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
                run = p.add_run(heading_text)
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
                run = p.add_run(heading_text)
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
                        
                        # Парсимо inline стилі в комірці
                        tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*|\$.*?\$)', cell_value)
                        for token in tokens:
                            if not token:
                                continue
                            if token.startswith('**') and token.endswith('**'):
                                run = cell_p.add_run(token[2:-2])
                                format_run(run, font_size=12, bold=True)
                            elif token.startswith('*') and token.endswith('*'):
                                run = cell_p.add_run(token[1:-1])
                                format_run(run, font_size=12, italic=True)
                            elif token.startswith('$') and token.endswith('$'):
                                run = cell_p.add_run(token[1:-1])
                                format_run(run, font_size=12, italic=True)
                            else:
                                run = cell_p.add_run(token)
                                format_run(run, font_size=12)
                
                # Додаємо порожній рядок після таблиці для візуального відступу
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                in_list = False
                continue

            # --- Обробка зображень ---
            # Виявлення зображення у форматі ![caption](path) або <p align="center"><img>
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
            # Формули розміщуються по центру, номер формули — праворуч
            formula_match = re.search(r'\$\$\s*(.*?)\s*\$\$', block, re.DOTALL)
            if formula_match:
                formula_content = formula_match.group(1).strip()
                # Перевіряємо наявність HTML тегів або eqno номерів формули
                formula_clean = re.sub(r'\\qquad.*$', '', formula_content).strip()
                formula_clean = re.sub(r'\\eqno.*$', '', formula_clean).strip()
                
                # Спробуємо знайти номер формули (наприклад, (8.1))
                num_match = re.search(r'\((?:\d+\.\d+|\d+)\)', formula_content)
                formula_num = num_match.group(0) if num_match else ""
                
                # Додаємо формулу як центрований параграф
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.first_line_indent = Inches(0)
                
                # Якщо є номер, ми створюємо гарне форматування табуляцією або пробілами
                # Для простоти, додамо формулу та номер в один рядок
                formula_text = formula_clean.replace('\\times', ' × ').replace('\\text', '').replace('{', '').replace('}', '').replace('\\', '')
                if formula_num:
                    # Додаємо великий простір перед номером формули
                    run_form = p.add_run(formula_text)
                    format_run(run_form, italic=True)
                    
                    # Спрощений таб-ефект для номеру формули
                    run_space = p.add_run(" " * 40)
                    format_run(run_space)
                    
                    run_num = p.add_run(formula_num)
                    format_run(run_num)
                else:
                    run_form = p.add_run(formula_text)
                    format_run(run_form, italic=True)
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
                        
                        # Парсимо inline форматування
                        tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*|\$.*?\$)', item_text)
                        for token in tokens:
                            if not token:
                                continue
                            if token.startswith('**') and token.endswith('**'):
                                run = p.add_run(token[2:-2])
                                format_run(run, bold=True)
                            elif token.startswith('*') and token.endswith('*'):
                                run = p.add_run(token[1:-1])
                                format_run(run, italic=True)
                            elif token.startswith('$') and token.endswith('$'):
                                run = p.add_run(token[1:-1])
                                format_run(run, italic=True)
                            else:
                                run = p.add_run(token)
                                format_run(run)
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
                        
                        # Парсимо inline форматування
                        tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*|\$.*?\$)', item_text)
                        for token in tokens:
                            if not token:
                                continue
                            if token.startswith('**') and token.endswith('**'):
                                run = p.add_run(token[2:-2])
                                format_run(run, bold=True)
                            elif token.startswith('*') and token.endswith('*'):
                                run = p.add_run(token[1:-1])
                                format_run(run, italic=True)
                            elif token.startswith('$') and token.endswith('$'):
                                run = p.add_run(token[1:-1])
                                format_run(run, italic=True)
                            else:
                                run = p.add_run(token)
                                format_run(run)
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
