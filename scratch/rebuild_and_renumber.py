import os
import re
import sys

# Configure output encoding to support Ukrainian characters on Windows console
sys.stdout.reconfigure(encoding='utf-8')

thesis_dir = r"C:\Users\igorl\Documents\antigravity\dazzling-rutherford\docs\thesis"

def read_file(name):
    with open(os.path.join(thesis_dir, name), 'r', encoding='utf-8') as f:
        return f.read()

def write_file(name, content):
    with open(os.path.join(thesis_dir, name), 'w', encoding='utf-8') as f:
        f.write(content)

def extract_section(text, header_regex, end_regex=None):
    match = re.search(header_regex, text)
    if not match:
        print(f"Warning: pattern {header_regex} not found!")
        return ""
    start = match.start()
    if end_regex:
        end_match = re.search(end_regex, text[start+1:])
        if end_match:
            return text[start:start+1+end_match.start()]
    return text[start:]

def renumber_text(text, fig_map, tab_map, eq_map):
    # Phase 1: replace with unique temp placeholders
    # Sort old numbers by length descending to prevent partial replacements (e.g. 1.10 matching 1.1)
    for old_num, new_num in sorted(fig_map.items(), key=lambda x: len(x[0]), reverse=True):
        pat = re.compile(rf'\b(рисунок|рисунка|рисунку|рисунком|рис\.)\s*{re.escape(old_num)}\b', re.IGNORECASE)
        text = pat.sub(lambda m: f"{m.group(1)} __FIG_TEMP_{new_num}__", text)
        
    for old_num, new_num in sorted(tab_map.items(), key=lambda x: len(x[0]), reverse=True):
        pat = re.compile(rf'\b(таблиця|таблиці|таблицею|табл\.)\s*{re.escape(old_num)}\b', re.IGNORECASE)
        text = pat.sub(lambda m: f"{m.group(1)} __TAB_TEMP_{new_num}__", text)
        
    for old_num, new_num in sorted(eq_map.items(), key=lambda x: len(x[0]), reverse=True):
        pat = re.compile(rf'\(\s*{re.escape(old_num)}\s*\)')
        text = pat.sub(f"(__EQ_TEMP_{new_num}__)", text)
        
    # Phase 2: replace placeholders with actual final values
    text = re.sub(r'__FIG_TEMP_(.*?)__', r'\1', text)
    text = re.sub(r'__TAB_TEMP_(.*?)__', r'\1', text)
    text = re.sub(r'__EQ_TEMP_(.*?)__', r'\1', text)
    
    return text

print("=== STARTING THE CLEAN THESIS RECONSTRUCTION AND RENUMBERING ===")

# --- Clean Checkout or verify original files exist ---
# Read unmodified source files
try:
    ch1_raw = read_file("chapter1_data_collection_analysis.md")
    ch2_raw = read_file("chapter2_theoretical_background.md")
    ch3_raw = read_file("chapter3_model_design.md")
    ch4_raw = read_file("chapter4_infrastructure.md")
    ch5_raw = read_file("chapter5_training_evaluation.md")
    ch6_raw = read_file("chapter6_online_learning.md")
    ch7_raw = read_file("chapter7_practical_implementation.md")
    ch8_raw = read_file("chapter8_economic_analysis.md")
except Exception as e:
    print(f"Error reading source files: {e}")
    sys.exit(1)

# ----------------- RECONSTRUCT CHAPTER 1 -----------------
print("\nRebuilding Chapter 1...")
# Extract sections
part1_1_from_ch2 = extract_section(ch2_raw, r"(?m)^## 2\.1\.", r"(?m)^## 2\.3\.")
part1_1_from_ch1 = extract_section(ch1_raw, r"(?m)^### 1\.1\.1\.", r"(?m)^### 1\.1\.2\.")
part1_2_from_ch1 = extract_section(ch1_raw, r"(?m)^### 1\.1\.2\.")
part1_3_from_ch2 = extract_section(ch2_raw, r"(?m)^## 2\.3\.")

# Clean headers
part1_1_from_ch2 = part1_1_from_ch2.replace(
    "## 2.1. Особливості фотоелектричного перетворення та джерела втрат у фотоелектричних системах",
    "## 1.1. Особливості функціонування ФЕС та вплив метеорологічних факторів на генерацію\n\n### 1.1.1. Особливості фотоелектричного перетворення та джерела втрат у фотоелектричних системах"
).replace(
    "## 2.2. Географічний та кліматичний вплив на сонячну інсоляцію",
    "### 1.1.2. Географічний та кліматичний вплив на сонячну інсоляцію"
)

part1_1_from_ch1 = part1_1_from_ch1.replace(
    "### 1.1.1. Фізичне обґрунтування впливу метеорологічних факторів на генерацію ФЕС",
    "### Вплив метеорологічних факторів на генерацію ФЕС"
).replace(
    r"$$GHI = DNI \cdot \cos(\theta) + DHI$$",
    r"$$GHI = DNI \cdot \cos(\theta) + DHI$$ (1.6)"
).replace(
    r"$$P_{PV} = P_{STC} \cdot \frac{GHI}{1000} \cdot [1 - \gamma \cdot (T_{cell} - T_{STC})]$$",
    r"$$P_{PV} = P_{STC} \cdot \frac{GHI}{1000} \cdot [1 - \gamma \cdot (T_{cell} - T_{STC})]$$ (1.7)"
).replace(
    r"$$T_{cell} = T_{amb} + GHI \cdot \frac{NOCT - 20}{800}$$",
    r"$$T_{cell} = T_{amb} + GHI \cdot \frac{NOCT - 20}{800}$$ (1.8)"
)

part1_2_from_ch1 = part1_2_from_ch1.replace(
    "### 1.1.2. Методологія збору, очищення та синхронізації даних",
    "## 1.2. Збір, аналіз та попередня обробка первинних даних сонячної генерації\n\n### 1.2.1. Методологія збору, очищення та синхронізації даних"
).replace(
    "### 1.1.3. Результати статистичного та кореляційного аналізу",
    "### 1.2.2. Результати статистичного та кореляційного аналізу"
).replace(
    "### 1.1.4. Візуальний аналіз та обговорення графічних залежностей",
    "### 1.2.3. Візуальний аналіз та обговорення графічних залежностей"
).replace(
    r"$$P_{hour} = \frac{1}{60} \sum_{i=1}^{60} P_{min, i}$$",
    r"$$P_{hour} = \frac{1}{60} \sum_{i=1}^{60} P_{min, i}$$ (1.9)"
).replace(
    r"$$r = \frac{\sum (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum (x_i - \bar{x})^2 \sum (y_i - \bar{y})^2}}$$",
    r"$$r = \frac{\sum (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum (x_i - \bar{x})^2 \sum (y_i - \bar{y})^2}}$$ (1.10)"
).replace(
    r"$$\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$$",
    r"$$\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$$ (1.11)"
)

part1_3_from_ch2 = part1_3_from_ch2.replace(
    "## 2.3. Теоретичний опис гібридної нейромережевої архітектури CNN-LSTM",
    "## 1.3. Огляд архітектури гібридних нейромереж CNN-LSTM та їх застосування в прогнозуванні"
).replace(
    "### Одновимірні згорткові шари (Conv1D)",
    "### 1.3.1. Одновимірні згорткові шари (Conv1D)"
).replace(
    "### Шари довгої короткострокової пам'яті (LSTM)",
    "### 1.3.2. Шари довгої короткострокової пам'яті (LSTM)"
).replace(
    "### Концепція синергії CNN-LSTM у прогнозуванні ФЕС",
    "### 1.3.3. Концепція синергії CNN-LSTM у прогнозуванні ФЕС"
)

ch1_conclusions = """## Висновки до розділу 1

У першому розділі було здійснено детальний аналіз теоретичних засад функціонування фотоелектричних станцій та досліджено характер впливу метеорологічних факторів на інтенсивність сонячної генерації. Проведений кореляційний аналіз підтвердив, що глобальне горизонтальне випромінювання (GHI) має найсильніший прямий лінійний зв'язок із потужністю генерації ФЕС (коефіцієнт Пірсона $r = +0.9034$, Спірмена $\rho = +0.9102$). Температура повітря та відносна вологість чинять суттєвий непрямий вплив, коригуючи ККД сонячних панелей та розсіюючи світло в атмосфері.

Обґрунтовано вибір гібридної нейромережевої архітектури CNN-LSTM як найбільш перспективного підходу для короткострокового прогнозування. Поєднання одновимірних згорткових шарів (Conv1D) для виявлення просторових і міжінформаційних залежностей та осередків LSTM для моделювання довгострокової динаміки часових рядів дозволяє ефективно враховувати як сезонні кліматичні закономірності, так і швидкозмінні погодні флуктуації."""

ch1_body = f"""# Розділ 1. Теоретичні засади та аналіз предметної області

{part1_1_from_ch2.strip()}

{part1_1_from_ch1.strip()}

{part1_2_from_ch1.strip()}

{part1_3_from_ch2.strip()}

{ch1_conclusions.strip()}
"""

# Chapter 1 Numbering Maps
ch1_figs = {'1.2': '1.1', '1.3': '1.2', '1.4': '1.3', '2.1': '1.4'}
ch1_tabs = {}  # Table 1.1 remains Table 1.1
ch1_eqs = {
    '2.1': '1.1', '2.2': '1.2', '2.3': '1.3', '2.4': '1.4', '2.5': '1.5',
    '2.6': '1.12', '2.7': '1.13', '2.8': '1.14', '2.9': '1.15', '2.10': '1.16',
    '2.11': '1.17', '2.12': '1.18', '2.13': '1.19', '2.14': '1.20',
    '2.15': '1.21', '2.16': '1.22'
}

ch1_body = renumber_text(ch1_body, ch1_figs, ch1_tabs, ch1_eqs)
write_file("chapter1.md", ch1_body)
print("  Chapter 1 generated successfully.")


# ----------------- RECONSTRUCT CHAPTER 2 -----------------
print("\nRebuilding Chapter 2...")
ch3_clean = ch3_raw.replace("# Розділ 3. Проектування та реалізація моделі CNN-LSTM\n", "").replace("# Розділ 3. Проектування та реалізація моделі CNN-LSTM", "")
ch3_clean = ch3_clean.replace("## 3.1.", "## 2.1.").replace("## 3.2.", "## 2.2.")
ch3_clean = ch3_clean.replace("## 3.3. Критерії оцінки точності прогнозування (Метрики)", "### 2.2.1. Критерії оцінки точності прогнозування (Метрики)")

ch4_clean = ch4_raw.replace("# Розділ 4. Архітектура та програмна реалізація інфраструктури системи\n", "").replace("# Розділ 4. Архітектура та програмна реалізація інфраструктури системи", "")
ch4_clean = ch4_clean.replace("## 4.1. Обґрунтування вибору СКБД TimescaleDB для часових рядів та проектування бази даних", "## 2.3. Проектування бази даних часових рядів на базі TimescaleDB")
ch4_clean = ch4_clean.replace("## 4.2. Проектування архітектури асинхронного REST API на FastAPI", "## 2.4. Архітектура програмного забезпечення та асинхронного REST API (FastAPI)")
ch4_clean = ch4_clean.replace("## 4.3. Автоматична інтерактивна специфікація інтерфейсів OpenAPI (Swagger UI)", "### 2.4.1. Автоматична інтерактивна специфікація інтерфейсів OpenAPI (Swagger UI)")

ch2_conclusions = """## Висновки до розділу 2

У другому розділі було спроектовано архітектуру та інфраструктурне забезпечення комп'ютерно-інтегрованої системи прогнозування. Розроблено математичний опис шарів гібридної моделі CNN-LSTM та алгоритм передобробки вхідних часових рядів із застосуванням нормалізації методом ковзного вікна.

Проектування бази даних виконано на основі технології TimescaleDB (розширення PostgreSQL), де створення гіпертаблиці `pv_telemetry` із тижневим інтервалом секціонування дозволило вирішити проблему зниження швидкості запису мільйонів записів та переповнення індексів у RAM. Реалізація асинхронного REST API на базі фреймворку FastAPI із автоматичним генератором документації OpenAPI забезпечує високу швидкість обробки конкурентних запитів прогнозування та зручність інтеграції системи із промисловими стандартами SCADA і диспетчерськими центрами."""

ch2_body = f"""# Розділ 2. Проектування моделі та інфраструктури системи

{ch3_clean.strip()}

{ch4_clean.strip()}

{ch2_conclusions.strip()}
"""

# Chapter 2 Numbering Maps
ch2_figs = {'4.1': '2.1'}
ch2_tabs = {'4.1': '2.1'}
ch2_eqs = {
    '3.1': '2.1', '3.2': '2.2', '3.3': '2.3', '3.4': '2.4',
    '4.1': '2.5'
}

ch2_body = renumber_text(ch2_body, ch2_figs, ch2_tabs, ch2_eqs)
write_file("chapter2.md", ch2_body)
print("  Chapter 2 generated successfully.")


# ----------------- RECONSTRUCT CHAPTER 3 -----------------
print("\nRebuilding Chapter 3...")
ch5_clean = ch5_raw.replace("# Розділ 5. Навчання моделі та первинне тестування\n", "").replace("# Розділ 5. Навчання моделі та первинне тестування", "")
ch5_clean = ch5_clean.replace("## 5.1. Параметри та процес навчання моделі CNN-LSTM", "## 3.1. Процес навчання моделі та первинна оцінка точності прогнозування\n\n### 3.1.1. Параметри та процес навчання моделі CNN-LSTM")
ch5_clean = ch5_clean.replace("## 5.2. Оцінка точності прогнозування на тестовому наборі даних", "### 3.1.2. Оцінка точності прогнозування на тестовому наборі даних")
ch5_clean = ch5_clean.replace("## 5.3. Порівняльний аналіз фактичної та прогнозованої генерації ФЕС", "### 3.1.3. Порівняльний аналіз фактичної та прогнозованої генерації ФЕС")

ch6_clean = ch6_raw.replace("# Розділ 6. Реалізація донавчання моделі в реальному часі\n", "").replace("# Розділ 6. Реалізація донавчання моделі в реальному часі", "")
ch6_clean = ch6_clean.replace("## 6.1. Концепція та проблеми зносу моделей у задачах сонячної генерації (Data Drift)", "## 3.2. Проблема зносу моделей (Data Drift) та метод адаптивного донавчання\n\n### 3.2.1. Концепція та проблеми зносу моделей")
ch6_clean = ch6_clean.replace("## 6.2. Метод адаптивного донавчання (Fine-Tuning) та запобігання катастрофічному забуванню", "### 3.2.2. Метод адаптивного донавчання (Fine-Tuning) та запобігання катастрофічному забуванню")
ch6_clean = ch6_clean.replace("## 6.3. Алгоритм та архітектурна логіка мультимасштабного онлайн-навчання", "## 3.3. Практична реалізація мультимасштабного онлайн-навчання та інтеграція реєстру моделей\n\n### 3.3.1. Алгоритм та архітектурна логіка мультимасштабного онлайн-навчання")

ch7_clean = ch7_raw.replace("# Розділ 7. Практична реалізація та дослідження донавчання\n", "").replace("# Розділ 7. Практична реалізація та дослідження донавчання", "")
ch7_clean = ch7_clean.replace("## 7.1. Структура розробленого програмного забезпечення", "### 3.3.2. Структура розробленого програмного забезпечення")
ch7_clean = ch7_clean.replace("## 7.2. Опис розробленого REST API та інтеграції реєстру моделей", "### 3.3.3. Опис розробленого REST API та інтеграції реєстру моделей")
ch7_clean = ch7_clean.replace("## 7.3. Результати симуляційного порівняльного аналізу стратегій ансамблювання", "## 3.4. Результати симуляційного порівняльного аналізу\n\n### 3.4.1. Результати симуляційного порівняльного аналізу стратегій ансамблювання")

# Replace directory structure text tree code block with markdown image reference
tree_pattern = re.compile(r'Загальна структура каталогів та файлів проекту виглядає наступним чином:\s*\n\s*```.*?```', re.DOTALL)
ch7_clean = tree_pattern.sub(
    'Загальна структура каталогів та файлів проекту виглядає наступним чином:\n\n'
    '![Структура каталогів та файлів проекту](/docs/images/project_structure.png)\n'
    '<p align="center"><em>Рисунок 7.1. Структура каталогів та файлів проекту</em></p>',
    ch7_clean
)

ch3_conclusions = """## Висновки до розділу 3

У третьому розділі було реалізовано програмні компоненти системи, проведено навчання моделі та досліджено її ефективність. Базова модель CNN-LSTM показала високу точність прогнозування на тестовій вибірці з похибкою MAPE = 9.06% та MAE = 0.2711 кВт.

Для вирішення проблеми зносу моделей (Data Drift), викликаного сезонними та кліматичними змінами, впроваджено метод онлайн-навчання та темпорального ансамблювання моделей (Base + Year + Month). Експериментальні дослідження підтвердили перевагу запропонованого підходу: використання ковзного вікна адаптивного донавчання знизило похибку MAPE до 8.54% (покращення точності на 5.77% відносно статичної базової моделі), повністю розв'язавши проблему катастрофічного забування глобальних закономірностей. Створено реєстр моделей `ModelRegistry` для потокобезпечного керування версіями ваг нейромережі в реальному часі."""

ch3_body = f"""# Розділ 3. Реалізація, навчання та дослідження ефективності системи

{ch5_clean.strip()}

{ch6_clean.strip()}

{ch7_clean.strip()}

{ch3_conclusions.strip()}
"""

# Chapter 3 Numbering Maps
ch3_figs = {
    '5.1': '3.1', '5.2': '3.2', '6.1': '3.3', '7.1': '3.4'
}
ch3_tabs = {
    '5.1': '3.1', '7.1': '3.2'
}
ch3_eqs = {
    '5.1': '3.1', '5.2': '3.2',
    '6.1': '3.3', '6.2': '3.4', '6.3': '3.5'
}

ch3_body = renumber_text(ch3_body, ch3_figs, ch3_tabs, ch3_eqs)
write_file("chapter3.md", ch3_body)
print("  Chapter 3 generated successfully.")


# ----------------- RECONSTRUCT CHAPTER 4 -----------------
print("\nRebuilding Chapter 4...")
ch8_clean = ch8_raw.replace("# Розділ 8. Економічний аналіз та розрахунки\n", "").replace("# Розділ 8. Економічний аналіз та розрахунки", "")
ch8_clean = ch8_clean.replace("## 8.1.", "## 4.1.").replace("## 8.2.", "## 4.2.")

ch4_conclusions = """## Висновки до розділу 4

У четвертому розділі проведено техніко-економічне обґрунтування впровадження розробленого рішення. Розрахунок нормованої вартості електроенергії (LCOE) підтвердив конкурентоспроможність сонячної генерації із собівартістю 3.63 грн/кВт-год, що нижче за традиційну вугільну (4.24 грн/кВт-год) та газову (4.96 грн/кВт-год) генерацію в Україні.

Досліджено фінансові втрати від небалансів на балансуючому ринку за тарифом 4.5 грн/кВт-год. Доведено, що використання розробленої системи прогнозування CNN-LSTM знижує витрати на сплату штрафів за дисбаланси на **81.93%**. Річний економічний ефект для дахової ФЕС потужністю 30 кВт становить 48 443 грн/рік, а при масштабуванні до промислової СЕС потужністю 10 МВт економія досягає **16 147 746 грн на рік**, що робить впровадження системи високорентабельним інвестиційним проектом."""

ch4_body = f"""# Розділ 4. Економічне обґрунтування

{ch8_clean.strip()}

{ch4_conclusions.strip()}
"""

# Chapter 4 Numbering Maps
ch4_figs = {'8.1': '4.1'}
ch4_tabs = {'8.1': '4.1', '8.2': '4.2'}
ch4_eqs = {
    '8.1': '4.1', '8.2': '4.2', '8.3': '4.3'
}

ch4_body = renumber_text(ch4_body, ch4_figs, ch4_tabs, ch4_eqs)
write_file("chapter4.md", ch4_body)
print("  Chapter 4 generated successfully.")

print("\n=== REBUILD AND RENUMBERING COMPLETED ===")
