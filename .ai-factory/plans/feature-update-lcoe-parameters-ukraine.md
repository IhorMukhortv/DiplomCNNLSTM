# План впровадження: Оновлення параметрів LCOE для умов України (2026 рік)

Цей план присвячений оновленню базових техніко-економічних параметрів розрахунку LCOE для ТЕС та ГТУ відповідно до реальних умов України на 2026 рік, адаптації розрахункових скриптів, оновленню модульних тестів та внесенню змін до розділів дипломної роботи (Розділи 4 та 8) для забезпечення економічної достовірності.

## Settings
- Testing: yes
- Logging: verbose
- Docs: yes

## Roadmap Linkage
Milestone: "Віха 8: Економічний аналіз та розрахунки (Частина 3)"
Rationale: "Коригування параметрів LCOE та оновлення тексту дипломної роботи для ТЕС та ГТУ забезпечує економічну реалістичність розрахунків та ДСТУ-відповідність розділів 4 і 8."

## Research Context
<!-- aif:active-summary:start -->
Тема: Коригування параметрів LCOE ТЕС та ГТУ для умов України (2026 рік)
Мета: Забезпечити економічну реалістичність розрахунків LCOE в коді та розділах дипломної роботи (Розділи 4 та 8), оновивши параметри вугільної та газової генерацій.
Обмеження:
- Враховувати український енергетичний контекст на 2026 рік.
- Залишити базову ставку дисконтування 10% як академічний стандарт, але навести аналіз чутливості при 12% та 15%.
Рішення:
- СЕС (30 кВт): без змін (CAPEX = 36000 грн/кВт, OPEX = 800 грн/кВт, КВВП = 15%, N = 25 років).
- Вугільна ТЕС: паливна складова $C_{\text{fuel}}$ піднімається з 1.60 грн/кВт-год до 3.00 грн/кВт-год, термін служби N скорочується до 20 років.
- Газова ТЕС: паливна складова $C_{\text{fuel}}$ піднімається з 2.80 грн/кВт-год до 6.00 грн/кВт-год, КВВП знижується до 10% для пікового режиму (OCGT) або залишається 30% для маневреного напівпіку. (Узгоджується піковий режим 10% як базовий для демонстрації максимальної цінності прогнозування СЕС).
- Розраховані нові орієнтовні показники LCOE при r=10%: СЕС ~3.63 грн/кВт-год, ТЕС ~5.99 грн/кВт-год (при N=20), ГТУ (пікова) ~12.47 грн/кВт-год.
<!-- aif:active-summary:end -->

## Tasks

### Phase 1: Update Calculations and Tests
- [ ] Task 1: Оновлення техніко-економічних параметрів у скрипті `scripts/calculate_economics.py`
  - **Опис**: Оновити параметри розрахунку LCOE у скрипті [calculate_economics.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/scripts/calculate_economics.py):
    - Вугільна ТЕС (`coal_params`): `fuel_cost_per_kwh` змінити на `3.00`, `lifetime_years` змінити на `20`.
    - Газотурбінна ТЕС (`gas_params`): `fuel_cost_per_kwh` змінити на `6.00`, КВВП (`annual_generation_kwh_per_kw` при КВВП = 10%) змінити на `876.0` (8760 * 0.10). Також у коментарі додати позначення "піковий режим (OCGT)".
  - **Логування**:
    - Переконатися, що логування початку та завершення розрахунків у `scripts/calculate_economics.py` залишається на рівні `INFO`.
  - **Файли**: [calculate_economics.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/scripts/calculate_economics.py)

- [ ] Task 2: Перевірка та адаптація модульних тестів `tests/test_economic_analysis.py`
  - **Опис**: Переконатися, що зміни параметрів не ламають абстрактні тести. Запустити pytest. За потреби адаптувати тести, якщо виникнуть помилки.
  - **Логування**:
    - Логування під час тестування стандартне для pytest.
  - **Файли**: [test_economic_analysis.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/tests/test_economic_analysis.py)

### Phase 2: Update Thesis Documents
- [ ] Task 3: Оновлення тексту та таблиць у розділах дипломної роботи
  - **Опис**: Оновити наступні файли:
    - [chapter4.md](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/chapter4.md): оновити опис параметрів вугільної та газової ТЕС (пункти 2 та 3 у списку), оновити Таблицю 4.1 з новими параметрами та новими розрахованими LCOE (СЕС = 3.63, ТЕС = 5.99, ГТУ = 12.47), а також текстові висновки під таблицею та висновки до розділу 4. Додати опис впливу підвищення ставок дисконтування до 12% та 15% як аналіз фінансової чутливості.
    - [chapter8_economic_analysis.md](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/chapter8_economic_analysis.md): аналогічно оновити вхідні параметри, Таблицю 8.1, нові значення LCOE, аналіз чутливості та висновки.
    - [conclusions.md](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/conclusions.md): оновити LCOE вугільної генерації до 5.99 грн/кВт-год та газової до 12.47 грн/кВт-год у пункті 3.
  - **Логування**:
    - Немає програмного логування.
  - **Файли**: 
    - [chapter4.md](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/chapter4.md)
    - [chapter8_economic_analysis.md](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/chapter8_economic_analysis.md)
    - [conclusions.md](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/conclusions.md)

- [ ] Task 4: Компіляція дипломної роботи та генерація фінальних файлів
  - **Опис**: Запустити скрипт компіляції [compile_thesis.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/scripts/compile_thesis.py) для оновлення документа Word [diploma_work.docx](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/docs/thesis/diploma_work.docx). Перевірити коректність роботи скрипта і відсутність помилок компіляції Pandoc.
  - **Логування**:
    - Логування у `compile_thesis.py` має рівень `DEBUG`.
  - **Файли**: [compile_thesis.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/scripts/compile_thesis.py)

## Verification Plan

### Automated Tests
- Запустити тести: `pytest tests/test_economic_analysis.py -v`
- Запустити розрахунки економіки: `python scripts/calculate_economics.py`
- Запустити компіляцію дипломної роботи: `python scripts/compile_thesis.py`

### Manual Verification
- Перевірити оновлений графік `docs/images/lcoe_comparison.png` на відповідність новим даним (СЕС = 3.63, ТЕС = 5.99, ГТУ = 12.47).
- Перевірити оновлені документи `chapter4.md` та `chapter8_economic_analysis.md` на наявність коректних описів.
