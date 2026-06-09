import os
import threading
import tensorflow as tf
import logging
from typing import List, Dict, Optional
from app.core.models.cnn_lstm import build_cnn_lstm_model

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Потокобезпечний реєстр мультимасштабного темпорального ансамблю моделей.

    Архітектура натхненна EMA (Exponential Moving Average) з трейдингу:
      - base:  Базова модель (аналог EMA-200) — навчена на всьому датасеті,
               ловить глобальні патерни та довгострокову сезонність.
      - year:  Річна модель (аналог EMA-50) — донавчена на ~8760 годин (~1 рік)
               локальних даних, ловить сезонні тренди та деградацію панелей.
      - month: Місячна модель (аналог EMA-12) — донавчена на ~720 годин (~1 місяць)
               локальних даних, ловить актуальні погодні патерни та локальні умови.

    Прогноз = середнє(base, year, month), що забезпечує:
      - Стабільність завдяки базовій моделі (якір)
      - Адаптивність до середньострокових змін (рік)
      - Реактивність на поточні умови (місяць)
    """

    # Імена слотів моделей
    SLOT_BASE = "base"
    SLOT_YEAR = "year"
    SLOT_MONTH = "month"

    def __init__(self, model_path: str = "app/core/models/saved_model.keras"):
        self.model_path = model_path

        # Визначаємо шляхи для кожного масштабу
        dir_name = os.path.dirname(model_path)
        self._slot_paths: Dict[str, str] = {
            self.SLOT_BASE: model_path,
            self.SLOT_YEAR: os.path.join(dir_name, "saved_model_year.keras"),
            self.SLOT_MONTH: os.path.join(dir_name, "saved_model_month.keras"),
        }

        # Кеш моделей у пам'яті
        self._models: Dict[str, Optional[tf.keras.Model]] = {
            self.SLOT_BASE: None,
            self.SLOT_YEAR: None,
            self.SLOT_MONTH: None,
        }

        # Зворотна сумісність з тестами та monkeypatch
        self._model = None

        # Шляхи старого формату для зворотної сумісності
        self.v1_path = os.path.join(dir_name, "saved_model_v1.keras")
        self.v2_path = os.path.join(dir_name, "saved_model_v2.keras")
        self.v3_path = os.path.join(dir_name, "saved_model_v3.keras")

        self._lock = threading.Lock()

    def get_models(self) -> List[tf.keras.Model]:
        """
        Повертає список усіх наявних моделей для мультимасштабного ансамблю.
        Порядок: [base, year, month]. Відсутні слоти пропускаються.
        Базова модель присутня завжди.
        """
        with self._lock:
            # Завантажуємо базову модель, якщо ще не завантажена
            if self._models[self.SLOT_BASE] is None:
                self._load_base_model()

            # Спроба завантажити year/month, якщо файли є, а в кеші ще немає
            for slot in [self.SLOT_YEAR, self.SLOT_MONTH]:
                path = self._slot_paths[slot]
                if self._models[slot] is None and os.path.exists(path):
                    self._models[slot] = self._load_model_file(path, slot)

            models_list = []
            for slot in [self.SLOT_BASE, self.SLOT_YEAR, self.SLOT_MONTH]:
                if self._models[slot] is not None:
                    models_list.append(self._models[slot])

            return models_list

    def get_model_labels(self) -> List[str]:
        """Повертає мітки наявних моделей у тому ж порядку, що й get_models()."""
        with self._lock:
            labels = []
            for slot in [self.SLOT_BASE, self.SLOT_YEAR, self.SLOT_MONTH]:
                if self._models[slot] is not None:
                    labels.append(slot)
                elif os.path.exists(self._slot_paths[slot]):
                    labels.append(slot)
            return labels

    def save_slot_model(self, model: tf.keras.Model, slot: str) -> None:
        """
        Зберігає модель у вказаний іменований слот (year або month).

        Аргументи:
            model: Навчена/донавчена модель Keras.
            slot: Ім'я слоту — 'year' або 'month'.
        """
        if slot not in [self.SLOT_YEAR, self.SLOT_MONTH]:
            raise ValueError(f"Невідомий слот: {slot}. Допустимі: 'year', 'month'.")

        with self._lock:
            path = self._slot_paths[slot]
            logger.info(f"Реєстр моделей: Збереження моделі у слот '{slot}' за шляхом {path}...")
            os.makedirs(os.path.dirname(path), exist_ok=True)

            try:
                model.save(path)
                self._models[slot] = model
                self._model = model  # Зворотна сумісність
                logger.info(f"Реєстр моделей: Модель '{slot}' успішно збережено.")
            except Exception as e:
                logger.error(f"Реєстр моделей: Помилка збереження моделі '{slot}': {e}")
                raise

    def save_new_version(self, model: tf.keras.Model) -> None:
        """
        Метод зворотної сумісності. Зберігає модель як 'month' (найактуальніший слот).
        """
        self.save_slot_model(model, self.SLOT_MONTH)

    def save_model(self, model: tf.keras.Model) -> None:
        """Метод зворотної сумісності для збереження моделі як базової."""
        with self._lock:
            logger.info(f"Реєстр моделей: Збереження моделі у файл {self.model_path}...")
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            model.save(self.model_path)
            self._models[self.SLOT_BASE] = model
            self._model = model
            logger.info("Реєстр моделей: Успішно збережено модель у базовий файл.")

    def get_model(self) -> tf.keras.Model:
        """
        Зберігаємо сумісність з одиночним інтерфейсом.
        Повертає найновішу (month > year > base) модель.
        """
        models = self.get_models()
        # Повертаємо останню з наявних (month, якщо є, інакше year, інакше base)
        return models[-1] if models else None

    def reload_model(self) -> tf.keras.Model:
        """Перезавантажує всі наявні моделі з диска."""
        with self._lock:
            logger.info("Реєстр моделей: Перезавантаження всіх моделей з диска...")

            # Скидаємо кеш
            for slot in [self.SLOT_BASE, self.SLOT_YEAR, self.SLOT_MONTH]:
                self._models[slot] = None
            self._model = None

            # Завантажуємо базову
            self._load_base_model()

            # Завантажуємо year та month за наявності
            for slot in [self.SLOT_YEAR, self.SLOT_MONTH]:
                path = self._slot_paths[slot]
                if os.path.exists(path):
                    self._models[slot] = self._load_model_file(path, slot)
                    self._model = self._models[slot]

            # Повертаємо найновішу модель
            for slot in [self.SLOT_MONTH, self.SLOT_YEAR, self.SLOT_BASE]:
                if self._models[slot] is not None:
                    return self._models[slot]
            return self._models[self.SLOT_BASE]

    def _load_base_model(self) -> None:
        """Завантажує базову модель з диска."""
        if os.path.exists(self.model_path):
            try:
                self._models[self.SLOT_BASE] = tf.keras.models.load_model(self.model_path)
                self._model = self._models[self.SLOT_BASE]
                logger.info(f"Реєстр моделей: Успішно завантажено базову модель з {self.model_path}")
            except Exception as e:
                logger.error(f"Реєстр моделей: Помилка завантаження базової моделі: {e}")
                self._models[self.SLOT_BASE] = build_cnn_lstm_model(input_shape=(24, 7))
                self._model = self._models[self.SLOT_BASE]
        else:
            logger.warning(f"Реєстр моделей: Базову модель {self.model_path} не знайдено. Ініціалізація дефолтної.")
            self._models[self.SLOT_BASE] = build_cnn_lstm_model(input_shape=(24, 7))
            self._model = self._models[self.SLOT_BASE]

    def _load_model_file(self, path: str, label: str) -> Optional[tf.keras.Model]:
        """Помічник для завантаження окремого файлу моделі."""
        try:
            model = tf.keras.models.load_model(path)
            logger.info(f"Реєстр моделей: Успішно завантажено модель '{label}' з {path}")
            return model
        except Exception as e:
            logger.error(f"Реєстр моделей: Не вдалося завантажити '{label}' з {path}: {e}")
            return None


# Ініціалізуємо синглтон реєстру
model_registry = ModelRegistry()
