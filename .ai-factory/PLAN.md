# План впровадження (Швидкий режим): Компіляція дипломної роботи у DOCX

Created: 2026-06-08

## Settings
- Testing: no
- Logging: verbose
- Docs: yes

## Tasks

### Phase 1: Dependency Setup
- [ ] Task 1: Встановлення бібліотеки python-docx
  - **Опис**: Встановити бібліотеку `python-docx` у віртуальне оточення проекту для можливості роботи з файлами Word.
  - **Команда**: `.venv\Scripts\pip install python-docx`

### Phase 2: Compiler Script Implementation
- [ ] Task 2: Створення скрипта компіляції (`scripts/compile_thesis.py`)
  - **Опис**: Реалізувати скрипт `scripts/compile_thesis.py` для об'єднання 11 файлів Markdown у правильному порядку, парсингу їхньої розмітки (заголовки, абзаци, списки, таблиці, формули та зображення) та збереження у файл `docs/thesis/diploma_work.docx` згідно з ДСТУ.
  - **Файли**: [compile_thesis.py](file:///C:/Users/igorl/Documents/antigravity/dazzling-rutherford/scripts/compile_thesis.py)

### Phase 3: Compilation and Verification
- [ ] Task 3: Запуск компіляції та перевірка результату
  - **Опис**: Запустити скрипт компіляції та переконатися, що файл `docs/thesis/diploma_work.docx` створено і він містить усі рисунки, таблиці та правильне форматування.

## Verification Plan

### Manual Verification
- Запуск:
  `$env:PYTHONPATH="."; .venv\Scripts\python scripts/compile_thesis.py`
- Перевірка файлу `docs/thesis/diploma_work.docx`.
