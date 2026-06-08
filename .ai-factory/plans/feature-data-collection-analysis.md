# План впровадження: Збір та аналіз первинних даних

Branch: feature/data-collection-analysis
Created: 2026-06-08

## Settings
- Testing: yes
- Logging: verbose
- Docs: yes

## Roadmap Linkage
Milestone: "Віха 1: Збір та аналіз первинних даних"
Rationale: "Цей план охоплює збір первинних історичних даних сонячної генерації з реального відкриваного набору даних (30 кВт ФЕС на даху навчального закладу), отримання відповідних метео-даних з Open-Meteo, проведення аналізу та написання підрозділу дипломної роботи."

## Commit Plan
- **Commit 1** (після кроків 1-2): "feat: implement weather client and PV dataset loader"
- **Commit 2** (після кроків 3-4): "feat: implement data pipeline and save raw dataset"
- **Commit 3** (після кроків 5-6): "feat: perform correlation analysis and generate plots"
- **Commit 4** (після кроків 7): "docs: write chapter 1 data collection and analysis draft for thesis"

## Tasks

### Phase 1: Setup and Infrastructure
- [ ] Task 1: Створення клієнта погоди (Weather Client)
  - **Опис**: Реалізувати асинхронний клієнт `app/infrastructure/weather/client.py` з використанням `httpx.AsyncClient` для отримання історичних годинних погодних даних з Open-Meteo API за заданими координатами ФЕС та часовим діапазоном (2017-2019 роки). Клієнт повинен отримувати температуру (`temperature_2m`), хмарність (`cloud_cover`), відносну вологість (`relative_humidity_2m`), пряму нормальну інсоляцію (`direct_normal_irradiance` - DNI), дифузну горизонтальну інсоляцію (`diffuse_horizontal_irradiance` - DHI), глобальну горизонтальну інсоляцію (`global_horizontal_irradiance` - GHI).
  - **Логування**:
    - Логувати початок запиту (URL, координати, дати) на рівні `DEBUG`.
    - Логувати успішне отримання відповіді та кількість отриманих записів на рівні `INFO`.
    - Логувати HTTP-помилки або таймаути на рівні `ERROR` з детальним описом.
    - Рівень логування має керуватися через конфігурацію додатку.
  - **Тестування**: Написати тест у `tests/test_weather_client.py` для перевірки запитів до API (з використанням `pytest-mock` або `respx` для симуляції відповідей API).
  - **Файли**: [client.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/app/infrastructure/weather/client.py), [test_weather_client.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/tests/test_weather_client.py)

- [ ] Task 2: Створення завантажувача даних генерації ФЕС (PV Dataset Loader)
  - **Опис**: Реалізувати завантажувач та парсер даних генерації ФЕС у `app/infrastructure/solar/dataset_loader.py`. Він повинен завантажувати реальний набір даних сонячної генерації ФЕС потужністю 30 кВт з публічного репозиторію (у форматі HDF5 або CSV) та вилучати похвилинні дані вихідної потужності (кВт). Скрипт має підтримувати кешування локально для уникнення повторного завантаження великих файлів.
  - **Логування**:
    - Логувати початок завантаження набору даних (розмір, джерело) на рівні `INFO`.
    - Логувати етапи парсингу та розпакування даних на рівні `DEBUG`.
    - Логувати кількість успішно імпортованих записів генерації на рівні `INFO`.
    - Логувати помилки зчитування HDF5/CSV на рівні `ERROR`.
  - **Тестування**: Написати тест у `tests/test_dataset_loader.py` для перевірки коректності читання формату даних (використовуючи невеликий локальний тестовий файл-мок).
  - **Файли**: [dataset_loader.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/app/infrastructure/solar/dataset_loader.py), [test_dataset_loader.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/tests/test_dataset_loader.py)
<!-- Commit checkpoint: tasks 1-2 -->

### Phase 2: Data Pipeline
- [ ] Task 3: Конвеєр збору та об'єднання даних (Data Pipeline & Alignment)
  - **Опис**: Створити конвеєр збору та агрегації даних у `app/core/data/pipeline.py`. Конвеєр повинен зчитувати похвилинні дані генерації ФЕС, агрегувати їх до годинного інтервалу (середнє або сумарне значення), синхронізувати за часовою міткою (з урахуванням часових поясів) з годинними метеорологічними даними від Open-Meteo та зберігати результуючий набір даних у CSV-файл `data/raw/pv_weather_data.csv`.
  - **Логування**:
    - Логувати ініціалізацію конвеєра та параметри вирівнювання часу на рівні `INFO`.
    - Логувати проміжні розміри даних до та після агрегації на рівні `DEBUG`.
    - Логувати кількість пропущених або пошкоджених записів на рівні `WARN`.
    - Логувати успішне збереження файлу `pv_weather_data.csv` на рівні `INFO`.
    - Логувати критичні збої обробки часових рядів на рівні `ERROR`.
  - **Тестування**: Написати тест у `tests/test_pipeline.py` для перевірки синхронізації та агрегації тестових послідовностей різної частоти.
  - **Файли**: [pipeline.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/app/core/data/pipeline.py), [config.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/app/core/config.py), [test_pipeline.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/tests/test_pipeline.py)

- [ ] Task 4: Скрипт запуску конвеєра (Data CLI / Entrypoint)
  - **Опис**: Створити CLI-скрипт `scripts/collect_data.py` для зручного запуску всього процесу завантаження, агрегації та збереження даних за вказаний період років (2017-2019).
  - **Логування**:
    - Логувати запуск скрипта з аргументами командного рядка на рівні `INFO`.
    - Логувати загальний час виконання та статус успішності на рівні `INFO`.
    - Логувати помилки валідації аргументів на рівні `ERROR`.
  - **Тестування**: Перевірити поведінку CLI при запуску з некоректними аргументами.
  - **Файли**: [collect_data.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/scripts/collect_data.py)
<!-- Commit checkpoint: tasks 3-4 -->

### Phase 3: Correlation Analysis
- [ ] Task 5: Реалізація аналізу та візуалізації даних (Data Analysis Script)
  - **Опис**: Створити скрипт `research/correlation_analysis.py` для завантаження зібраного CSV-файлу, розрахунку матриці кореляції Пірсона та Спірмена між генерацією ФЕС та метеорологічними параметрами (GHI, DNI, DHI, температура, хмарність, вологість).
  - **Логування**:
    - Логувати завантаження даних та кількість пропущених значень на рівні `DEBUG`.
    - Логувати розраховані значення коефіцієнтів кореляції для ключових пар на рівні `INFO`.
    - Логувати помилки при розрахунку або відсутність необхідних колонок на рівні `ERROR`.
  - **Файли**: [correlation_analysis.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/research/correlation_analysis.py)

- [ ] Task 6: Генерація графіків для дипломної роботи (Plot Generation)
  - **Опис**: Додати до `research/correlation_analysis.py` функціонал для побудови та збереження графіків у каталог `docs/images/`:
    - Теплова карта кореляції (correlation heatmap).
    - Точкові графіки залежності (scatter plots) генерації від GHI та температури.
    - Добові профілі генерації та інсоляції для типових днів різних сезонів (літо, зима, весна/осінь).
  - **Логування**:
    - Логувати генерацію та збереження кожного окремого графіка (шлях до файлу) на рівні `INFO`.
    - Логувати помилки візуалізації на рівні `ERROR`.
  - **Файли**: [correlation_analysis.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/research/correlation_analysis.py)
<!-- Commit checkpoint: tasks 5-6 -->

### Phase 4: Thesis Chapter Writing
- [ ] Task 7: Написання тексту підрозділу дипломної роботи (Thesis Subsection Draft)
  - **Опис**: Написати 3-5 сторінок тексту підрозділу дипломної роботи "Збір та аналіз первинних даних" у файлі `docs/thesis/chapter1_data_collection_analysis.md`. Текст має містити детальний опис фізичного впливу метеорологічних факторів на генерацію, опис процесу отримання метеоданих (через Open-Meteo API), опис експериментального набору даних реальної ФЕС потужністю 30 кВт (без згадки назви SKIPP'D та Stanford University; опис має бути узагальненим як реальна ФЕС на даху навчального закладу в помірному кліматі США), таблицю розрахованих коефіцієнтів кореляції, аналіз отриманих залежностей та посилання на згенеровані графіки. Форматування має відповідати вимогам ДСТУ (шрифт Times New Roman 14пт, інтервал 1.5, абзацний відступ, формули по центру з номерами праворуч).
  - **Файли**: [chapter1_data_collection_analysis.md](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/chapter1_data_collection_analysis.md)
<!-- Commit checkpoint: tasks 7 -->

## Verification Plan

### Automated Tests
- Запуск pytest для перевірки клієнта погоди, завантажувача даних та конвеєра:
  `pytest tests/`

### Manual Verification
- Запуск скрипта збору даних за допомогою CLI:
  `python scripts/collect_data.py --start_date 2017-01-01 --end_date 2019-12-31 --lat 37.43 --lon -122.17`
- Запуск кореляційного аналізу:
  `python research/correlation_analysis.py`
- Візуальний контроль згенерованих графіків у `docs/images/` та перевірка файлу підрозділу `docs/thesis/chapter1_data_collection_analysis.md` на відповідність вимогам форматування ДСТУ та відсутність заборонених назв.
