import os
import pytest
from unittest.mock import patch, MagicMock
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_TAB_ALIGNMENT

# Імпортуємо функції з нашого компілятора
# Вони будуть визначені у scripts/compile_thesis.py
from scripts.compile_thesis import (
    find_pandoc,
    clean_text_backslashes,
    clean_latex_formula,
    parse_math_to_runs,
    preprocess_markdown,
)

def test_find_pandoc():
    # Перевіряємо, що функція пошуку знаходить pandoc.exe
    pandoc_path = find_pandoc()
    assert pandoc_path is not None
    assert os.path.exists(pandoc_path) or pandoc_path == "pandoc"

def test_clean_text_backslashes():
    # Тест на очищення екранованих символів у тексті
    text = "Успіх на \\%100\\_гарантовано, див. \\#1 та \\$20."
    cleaned = clean_text_backslashes(text)
    assert cleaned == "Успіх на %100_гарантовано, див. #1 та $20."

def test_clean_latex_formula():
    # Тест на перетворення LaTeX формул
    formula = r"LCOE = \frac{CAPEX + \sum_{t=1}^{N} \frac{OPEX_t + F_t}{(1 + r)^t}}{\sum_{t=1}^{N} \frac{E_t}{(1 + r)^t}}"
    cleaned = clean_latex_formula(formula)
    assert "∑" in cleaned
    assert "/" in cleaned
    assert "CAPEX" in cleaned

def test_parse_math_to_runs():
    # Тест на парсинг індексів у формулі
    text = "F_t = C_fuel × E_t"
    runs = parse_math_to_runs(text)
    # Очікувані фрагменти:
    # F (normal), t (sub), = C (normal), fuel (sub), × E (normal), t (sub)
    assert len(runs) >= 6
    assert runs[0][0] == "F"
    assert runs[0][1] is False # is_sub
    assert runs[1][0] == "t"
    assert runs[1][1] is True  # is_sub


def test_preprocess_markdown():
    # Тест 1: формули з номерами зовні
    input_text = "$$GHI = DNI \\cdot \\cos(\\theta) + DHI$$ (1.1)"
    processed = preprocess_markdown(input_text)
    assert "[EQNO: (1.1)]" in processed
    assert "$$GHI = DNI \\cdot \\cos(\\theta) + DHI$$" in processed

    # Тест 2: формули без номерів
    input_text = "$$P_{PV} = P_{STC}$$"
    processed = preprocess_markdown(input_text)
    assert "[EQNO:" not in processed

    # Тест 3: зображення - вилучення alt text та провідних косих рисок
    input_text = "![Теплова карта кореляції](/docs/images/correlation_heatmap.png)"
    processed = preprocess_markdown(input_text)
    assert processed.strip() == "![](docs/images/correlation_heatmap.png)"
