# План впровадження: Економічний аналіз та розрахунки

Branch: feature/economic-analysis-lcoe
Created: 2026-06-08

## Settings
- Testing: yes
- Logging: verbose
- Docs: yes

## Roadmap Linkage
Milestone: "Віха 8: Економічний аналіз та розрахунки (Частина 3)"
Rationale: "Цей план охоплює створення математичних та програмних інструментів для розрахунку LCOE сонячної, газової та вугільної генерацій, розрахунок фінансового ефекту від точності прогнозування небалансів ФЕС, а також написання Розділу 8 дипломної роботи відповідно до вимог оформлення."

## Commit Plan
- **Commit 1**: "feat: implement economic analysis module and LCOE calculations"
- **Commit 2**: "test: add unit tests for economic analysis calculations"
- **Commit 3**: "feat: add CLI script for economic analysis and generate LCOE comparison plot"
- **Commit 4**: "docs: write chapter 8 economic analysis for thesis"

## Tasks

### Phase 1: Core Economic Logic
- [ ] Task 1: Реалізація модуля економічного аналізу (Economic Analysis Module)
  - **Опис**: Створити модуль `app/core/economic_analysis.py` з функціоналом для розрахунку:
    - LCOE (Levelized Cost of Electricity) за стандартною дисконтованою формулою.
    - Втрат від дисбалансів (imbalance penalties) на основі фактичної генерації ФЕС, прогнозованої генерації та вартості небалансу.
    - Фінансового ефекту (заощадження від підвищення точності) при переході від однієї моделі прогнозування до іншої.
  - **Логування**:
    - Логувати виклик розрахунку LCOE з вхідними параметрами на рівні `DEBUG`.
    - Логувати результати розрахунку LCOE на рівні `INFO`.
    - Логувати розрахунок небалансів для вхідного часового ряду (кількість точок, загальний обсяг небалансів) на рівні `INFO`.
    - Логувати помилки у вхідних даних (від'ємні значення, ділення на нуль) на рівні `ERROR`.
  - **Файли**: [economic_analysis.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/app/core/economic_analysis.py)

- [ ] Task 2: Написання модульних тестів (Unit Tests)
  - **Опис**: Створити файл `tests/test_economic_analysis.py` для перевірки всіх математичних розрахунків модуля `economic_analysis.py` (тест розрахунку LCOE, тест розрахунку вартості небалансів з відомими значеннями похибки).
  - **Файли**: [test_economic_analysis.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/tests/test_economic_analysis.py)
<!-- Commit checkpoint: tasks 1-2 -->

### Phase 2: Scripts and Visualization
- [ ] Task 3: Створення CLI-скрипта розрахунків та генерації графіків (Economics CLI)
  - **Опис**: Реалізувати скрипт `scripts/calculate_economics.py`, який:
    - Запускає розрахунки LCOE для трьох типів генерацій (сонячна, газова, вугільна) з базовими параметрами.
    - Завантажує останні дані прогнозів (з результатів симуляції або оцінки) та розраховує економічні втрати від небалансів ФЕС для базової моделі та запропонованого ансамблю.
    - Масштабує розрахунки до 10 МВт промислової ФЕС.
    - Генерує та зберігає порівняльний графік LCOE у `docs/images/lcoe_comparison.png`.
  - **Логування**:
    - Логувати початок виконання економічних розрахунків на рівні `INFO`.
    - Логувати проміжні результати розрахунку економії на рівні `DEBUG`.
    - Логувати успішне створення графіків та звітів на рівні `INFO`.
  - **Файли**: [calculate_economics.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/scripts/calculate_economics.py)
<!-- Commit checkpoint: tasks 3 -->

### Phase 3: Thesis Writing
- [ ] Task 4: Написання тексту Розділу 8 дипломної роботи (Thesis Chapter Writing)
  - **Опис**: Написати підрозділ дипломної роботи у файлі `docs/thesis/chapter8_economic_analysis.md` (3-5 сторінок). Розділ повинен містити вступ, опис методології LCOE, таблицю параметрів розрахунку, порівняльний графік LCOE, опис балансуючого ринку України, формули штрафів за небаланси, результати розрахунку витрат та економії при покращенні MAPE/MAE нашою моделлю (для тестової 30 кВт ФЕС та масштабованої 10 МВт ФЕС), висновки про фінансову доцільність. Оформлення має бути за ДСТУ.
  - **Файли**: [chapter8_economic_analysis.md](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/chapter8_economic_analysis.md)
<!-- Commit checkpoint: tasks 4 -->

## Verification Plan

### Automated Tests
- Запуск pytest для перевірки економічних розрахунків:
  `pytest tests/test_economic_analysis.py -v`

### Manual Verification
- Запуск скрипта розрахунків:
  `python scripts/calculate_economics.py`
- Перевірка наявності згенерованого графіка `docs/images/lcoe_comparison.png`.
- Візуальний контроль та вичитка файлу `docs/thesis/chapter8_economic_analysis.md` на предмет академічного стилю та відповідності правилам оформлення.
