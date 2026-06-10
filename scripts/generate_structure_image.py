import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_tree_image(output_path):
    # Дані для структури каталогів
    # (префікс, назва, коментар, тип)
    tree_data = [
        ("", "app/", "", "Folder"),
        ("├── ", "api/", "# Презентаційний шар (FastAPI)", "Folder"),
        ("│   ├── ", "v1/", "# Перша версія API", "Folder"),
        ("│   │   ├── ", "endpoints/", "# Модулі кінцевих точок API", "Folder"),
        ("│   │   │   ├── ", "predict.py", "# Розрахунок прогнозів та донавчання", "File"),
        ("│   │   │   └── ", "telemetry.py", "# Запис нової телеметрії", "File"),
        ("│   │   └── ", "router.py", "# Головний маршрутизатор версії v1", "File"),
        ("│   └── ", "schemas/", "# Схеми валідації Pydantic", "Folder"),
        ("│       └── ", "telemetry.py", "# Схеми для даних телеметрії", "File"),
        ("├── ", "core/", "# Шар бізнес-логіки та ML", "Folder"),
        ("│   ├── ", "data/", "# Модулі обробки даних", "Folder"),
        ("│   │   └── ", "dataset.py", "# MinMaxScaler, розбиття та ковзне вікно", "File"),
        ("│   ├── ", "models/", "# ML-моделі та алгоритми навчання", "Folder"),
        ("│   │   ├── ", "cnn_lstm.py", "# Архітектура мережі CNN-LSTM", "File"),
        ("│   │   ├── ", "metrics.py", "# Функції розрахунку MAE, RMSE, MAPE", "File"),
        ("│   │   └── ", "online_learning.py", "# Логіка онлайн-донавчання моделей", "File"),
        ("│   └── ", "config.py", "# Глобальні налаштування (Pydantic Settings)", "File"),
        ("├── ", "infrastructure/", "# Шар інфраструктури", "Folder"),
        ("│   ├── ", "db/", "# Підключення до БД (TimescaleDB)", "Folder"),
        ("│   │   ├── ", "models.py", "# Опис ORM-моделей SQLAlchemy", "File"),
        ("│   │   └── ", "session.py", "# Асинхронний сешн-факторі та ініціалізація", "File"),
        ("│   └── ", "storage/", "# Збереження моделей", "Folder"),
        ("│       └── ", "model_registry.py", "# Потокобезпечний реєстр моделей", "File"),
        ("└── ", "main.py", "# Точка входу в FastAPI додаток", "File")
    ]

    # Переконаємося, що директорія існує
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Розміри фігури та налаштування
    fig, ax = plt.subplots(figsize=(10.5, 7.8), dpi=300)
    ax.set_facecolor("#f8fafc") # Slate 50 background
    fig.patch.set_facecolor("#f8fafc")

    # Ховаємо осі
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Малюємо вікно "IDE" з тінню
    # Тінь
    shadow = patches.FancyBboxPatch(
        (0.04, 0.03), 0.92, 0.93,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor="#0f172a", alpha=0.06, edgecolor="none", zorder=1
    )
    ax.add_patch(shadow)

    # Основне вікно
    window = patches.FancyBboxPatch(
        (0.03, 0.04), 0.92, 0.93,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor="#ffffff", edgecolor="#e2e8f0", linewidth=1.5, zorder=2
    )
    ax.add_patch(window)

    # Панель заголовка вікна
    header = patches.FancyBboxPatch(
        (0.03, 0.90), 0.92, 0.07,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor="#f1f5f9", edgecolor="#e2e8f0", linewidth=1.5, zorder=3
    )
    ax.add_patch(header)
    
    # Зафарбовуємо нижню частину заголовка, щоб приховати скруглення на стику з тілом
    header_fill = patches.Rectangle(
        (0.031, 0.90), 0.918, 0.02,
        facecolor="#f1f5f9", edgecolor="none", zorder=4
    )
    ax.add_patch(header_fill)
    
    # Лінія роздільника заголовка
    ax.plot(
        [0.03, 0.95], [0.90, 0.90],
        color="#e2e8f0", linewidth=1.5, zorder=5
    )

    # Кнопки macOS (червона, жовта, зелена)
    btn_y = 0.935
    colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
    for idx, color in enumerate(colors):
        btn = patches.Circle((0.06 + idx * 0.02, btn_y), radius=0.008, facecolor=color, edgecolor="none", zorder=6)
        ax.add_patch(btn)

    # Заголовок вікна
    ax.text(
        0.5, btn_y, "Project Directory Structure (app/)",
        color="#475569", fontsize=11, fontweight="bold",
        horizontalalignment="center", verticalalignment="center", zorder=6,
        fontfamily="monospace"
    )

    # Рендеринг дерева
    start_y = 0.85
    end_y = 0.08
    n_lines = len(tree_data)
    dy = (start_y - end_y) / n_lines

    # Параметри шрифту
    char_width = 0.0105  # емпірично підібрана ширина символу для monospace розміру 10.5
    comment_x = 0.52     # позиція вирівнювання коментарів

    for idx, (prefix, name, comment, file_type) in enumerate(tree_data):
        y = start_y - idx * dy
        
        # 1. Малюємо префікс структури (лінії дерева)
        if prefix:
            ax.text(
                0.06, y, prefix,
                color="#94a3b8", fontsize=10.5, fontfamily="monospace",
                verticalalignment="center", zorder=6
            )
            
        # Обчислюємо позицію для імені вузла
        name_x = 0.06 + len(prefix) * char_width
        
        # 2. Малюємо ім'я вузла
        if file_type == "Folder":
            # Жирний синій/темно-сірий для папок
            color = "#1e3a8a"  # Dark Blue
            weight = "bold"
        else:
            # Звичайний темно-сірий для файлів
            color = "#0f172a"  # Slate 900
            weight = "normal"
            
        ax.text(
            name_x, y, name,
            color=color, fontsize=10.5, fontfamily="monospace", fontweight=weight,
            verticalalignment="center", zorder=6
        )
        
        # 3. Малюємо коментар, якщо він є
        if comment:
            # Курсивний зелено-сірий для коментарів
            ax.text(
                comment_x, y, comment,
                color="#059669", fontsize=10, fontfamily="monospace", style="italic",
                verticalalignment="center", zorder=6
            )

    # Зберігаємо зображення
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Structure image saved successfully to {output_path}")

if __name__ == "__main__":
    generate_tree_image("docs/images/project_structure.png")
