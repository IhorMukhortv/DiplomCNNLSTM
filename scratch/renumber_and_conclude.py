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

# 1. Conclusions texts
conclusions = {
    1: """## Висновки до розділу 1

У першому розділі було здійснено детальний аналіз теоретичних засад функціонування фотоелектричних станцій та досліджено характер впливу метеорологічних факторів на інтенсивність сонячної генерації. Проведений кореляційний аналіз підтвердив, що глобальне горизонтальне випромінювання (GHI) має найсильніший прямий лінійний зв'язок із потужністю генерації ФЕС (коефіцієнт Пірсона $r = +0.9034$, Спірмена $\\rho = +0.9102$). Температура повітря та відносна вологість чинять суттєвий непрямий вплив, коригуючи ККД сонячних панелей та розсіюючи світло в атмосфері.

Обґрунтовано вибір гібридної нейромережевої архітектури CNN-LSTM як найбільш перспективного підходу для короткострокового прогнозування. Поєднання одновимірних згорткових шарів (Conv1D) для виявлення просторових і міжінформаційних залежностей та осередків LSTM для моделювання довгострокової динаміки часових рядів дозволяє ефективно враховувати як сезонні кліматичні закономірності, так і швидкозмінні погодні флуктуації.""",

    2: """## Висновки до розділу 2

У другому розділі було спроектовано архітектуру та інфраструктурне забезпечення комп'ютерно-інтегрованої системи прогнозування. Розроблено математичний опис шарів гібридної моделі CNN-LSTM та алгоритм передобробки вхідних часових рядів із застосуванням нормалізації методом ковзного вікна.

Проектування бази даних виконано на основі технології TimescaleDB (розширення PostgreSQL), де створення гіпертаблиці `pv_telemetry` із тижневим інтервалом секціонування дозволило вирішити проблему зниження швидкості запису мільйонів записів та переповнення індексів у RAM. Реалізація асинхронного REST API на базі фреймворку FastAPI із автоматичним генератором документації OpenAPI забезпечує високу швидкість обробки конкурентних запитів прогнозування та зручність інтеграції системи із промисловими стандартами SCADA і диспетчерськими центрами.""",

    3: """## Висновки до розділу 3

У третьому розділі було реалізовано програмні компоненти системи, проведено навчання моделі та досліджено її ефективність. Базова модель CNN-LSTM показала високу точність прогнозування на тестовій вибірці з похибкою MAPE = 9.06% та MAE = 0.2711 кВт.

Для вирішення проблеми зносу моделей (Data Drift), викликаного сезонними та кліматичними змінами, впроваджено метод онлайн-навчання та темпорального ансамблювання моделей (Base + Year + Month). Експериментальні дослідження підтвердили перевагу запропонованого підходу: використання ковзного вікна адаптивного донавчання знизило похибку MAPE до 8.54% (покращення точності на 5.77% відносно статичної базової моделі), повністю розв'язавши проблему катастрофічного забування глобальних закономірностей. Створено реєстр моделей `ModelRegistry` для потокобезпечного керування версіями ваг нейромережі в реальному часі.""",

    4: """## Висновки до розділу 4

У четвертому розділі проведено техніко-економічне обґрунтування впровадження розробленого рішення. Розрахунок нормованої вартості електроенергії (LCOE) підтвердив конкурентоспроможність сонячної генерації із собівартістю 3.63 грн/кВт-год, що нижче за традиційну вугільну (4.24 грн/кВт-год) та газову (4.96 грн/кВт-год) генерацію в Україні.

Досліджено фінансові втрати від небалансів на балансуючому ринку за тарифом 4.5 грн/кВт-год. Доведено, що використання розробленої системи прогнозування CNN-LSTM знижує витрати на сплату штрафів за дисбаланси на **81.93%**. Річний економічний ефект для дахової ФЕС потужністю 30 кВт становить 48 443 грн/рік, а при масштабуванні до промислової СЕС потужністю 10 МВт економія досягає **16 147 746 грн на рік**, що робить впровадження системи високорентабельним інвестиційним проектом."""
}

# Mappings
fig_map = {
    '1.2': '1.1', '1.3': '1.2', '1.4': '1.3', '2.1': '1.4',
    '4.1': '2.1',
    '5.1': '3.1', '5.2': '3.2', '6.1': '3.3', '7.1': '3.4',
    '8.1': '4.1'
}

tab_map = {
    '1.1': '1.1',
    '4.1': '2.1',
    '5.1': '3.1', '7.1': '3.2',
    '8.1': '4.1', '8.2': '4.2'
}

eq_map = {
    '2.1': '1.1', '2.2': '1.2', '2.3': '1.3', '2.4': '1.4', '2.5': '1.5',
    '1.1': '1.6', '1.2': '1.7', '1.3': '1.8', '1.4': '1.9', '1.5': '1.10', '1.6': '1.11',
    '2.6': '1.12', '2.7': '1.13', '2.8': '1.14', '2.9': '1.15', '2.10': '1.16', '2.11': '1.17', '2.12': '1.18', '2.13': '1.19', '2.14': '1.20', '2.15': '1.21', '2.16': '1.22',
    '3.1': '2.1', '3.2': '2.2', '3.3': '2.3', '3.4': '2.4', '4.1': '2.5',
    '5.1': '3.1', '5.2': '3.2', '6.1': '3.3', '6.2': '3.4', '6.3': '3.5',
    '8.1': '4.1', '8.2': '4.2', '8.3': '4.3'
}

print("=== RUNNING RENUMBERING & CONCLUSIONS INSERTION ===")

for ch_num, ch_path in chapters.items():
    if not os.path.exists(ch_path):
        print(f"File {ch_path} not found.")
        continue
        
    print(f"\n--- Processing Chapter {ch_num} ({ch_path}) ---")
    
    with open(ch_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Step 1: Insert Conclusions
    # Find placeholder like "## Висновки до розділу X\n\n(Тут будуть...)"
    placeholder_pat = re.compile(rf'## Висновки до розділу {ch_num}\s*\n\s*\(.*?\)', re.DOTALL)
    if placeholder_pat.search(content):
        content = placeholder_pat.sub(conclusions[ch_num], content)
        print("  Conclusions placeholder replaced with actual text.")
    else:
        # Fallback if placeholder format varies
        if f"## Висновки до розділу {ch_num}" in content:
            # Replace from "## Висновки до розділу X" to the end
            idx = content.find(f"## Висновки до розділу {ch_num}")
            content = content[:idx] + conclusions[ch_num]
            print("  Conclusions replaced from header to end.")
        else:
            content += "\n\n" + conclusions[ch_num]
            print("  Conclusions appended to the end.")

    # Step 2: Phase 1 of Renumbering - replace with TEMPORARY placeholders
    # Sort old numbers by length descending to prevent partial replacements
    for old_num, new_num in sorted(fig_map.items(), key=lambda x: len(x[0]), reverse=True):
        fig_ref_pat = re.compile(rf'\b(рисунок|рисунка|рисунку|рисунком|рис\.)\s*{re.escape(old_num)}\b', re.IGNORECASE)
        def replace_fig(m):
            return f"{m.group(1)} __FIG_TEMP_{new_num}__"
        content, count = fig_ref_pat.subn(replace_fig, content)
        if count > 0:
            print(f"  Placeholder figures: {old_num} -> __FIG_TEMP_{new_num}__ ({count} times)")
            
    for old_num, new_num in sorted(tab_map.items(), key=lambda x: len(x[0]), reverse=True):
        tab_ref_pat = re.compile(rf'\b(таблиця|таблиці|таблицею|табл\.)\s*{re.escape(old_num)}\b', re.IGNORECASE)
        def replace_tab(m):
            return f"{m.group(1)} __TAB_TEMP_{new_num}__"
        content, count = tab_ref_pat.subn(replace_tab, content)
        if count > 0:
            print(f"  Placeholder tables: {old_num} -> __TAB_TEMP_{new_num}__ ({count} times)")

    for old_num, new_num in sorted(eq_map.items(), key=lambda x: len(x[0]), reverse=True):
        eq_ref_pat = re.compile(rf'\(\s*{re.escape(old_num)}\s*\)')
        content, count = eq_ref_pat.subn(f"(__EQ_TEMP_{new_num}__)", content)
        if count > 0:
            print(f"  Placeholder equations: ({old_num}) -> (__EQ_TEMP_{new_num}__) ({count} times)")

    # Step 3: Phase 2 of Renumbering - replace temporary placeholders with actual final values
    content, count_fig = re.subn(r'__FIG_TEMP_(.*?)__', r'\1', content)
    content, count_tab = re.subn(r'__TAB_TEMP_(.*?)__', r'\1', content)
    content, count_eq = re.subn(r'__EQ_TEMP_(.*?)__', r'\1', content)
    
    print(f"  Finalized placeholders: Figures={count_fig}, Tables={count_tab}, Equations={count_eq}")

    # Write back the updated file
    with open(ch_path, "w", encoding="utf-8") as f:
        f.write(content)
        
print("\n=== COMPLETED ===")
