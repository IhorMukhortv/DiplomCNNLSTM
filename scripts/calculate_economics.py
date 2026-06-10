import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from app.core.economic_analysis import LcoeCalculator, ImbalanceCostCalculator

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("calculate_economics")

def main():
    logger.info("Початок виконання економічних розрахунків...")

    # =========================================================================
    # Частина 1: Розрахунок LCOE для трьох типів генерації
    # =========================================================================
    # Параметри розрахунку
    discount_rate = 0.10
    
    # 1. Сонячна ФЕС (30 кВт)
    solar_params = {
        "capex_per_kw": 36000.0,            # 900.0 * 40
        "opex_fixed_per_kw_year": 800.0,     # 20.0 * 40
        "fuel_cost_per_kwh": 0.0,
        "annual_generation_kwh_per_kw": 1314.0,  # КВВП = 15% (1314 год)
        "discount_rate": discount_rate,
        "lifetime_years": 25
    }
    
    # 2. Газотурбінна ТЕС
    gas_params = {
        "capex_per_kw": 44000.0,            # 1100.0 * 40
        "opex_fixed_per_kw_year": 1000.0,    # 25.0 * 40
        "fuel_cost_per_kwh": 2.80,          # 0.07 * 40
        "annual_generation_kwh_per_kw": 2628.0,  # КВВП = 30% (піковий режим)
        "discount_rate": discount_rate,
        "lifetime_years": 30
    }
    
    # 3. Вугільна ТЕС
    coal_params = {
        "capex_per_kw": 120000.0,           # 3000.0 * 40
        "opex_fixed_per_kw_year": 1600.0,    # 40.0 * 40
        "fuel_cost_per_kwh": 1.60,          # 0.04 * 40
        "annual_generation_kwh_per_kw": 5256.0,  # КВВП = 60% (базовий режим)
        "discount_rate": discount_rate,
        "lifetime_years": 40
    }

    # Розрахунок LCOE (грн за кВт-год)
    solar_lcoe = LcoeCalculator.calculate_lcoe(**solar_params)
    gas_lcoe = LcoeCalculator.calculate_lcoe(**gas_params)
    coal_lcoe = LcoeCalculator.calculate_lcoe(**coal_params)

    # Виведення результатів LCOE
    print("\n" + "="*100)
    print("ПОРІВНЯЛЬНИЙ АНАЛІЗ LCOE ДЛЯ РІЗНИХ ТИПІВ ГЕНЕРАЦІЇ (грн/кВт-год)")
    print("="*100)
    print(f"{'Тип генерації':<20} | {'CAPEX (грн/кВт)':<15} | {'OPEX (грн/кВт*рік)':<18} | {'Паливо (грн/кВт-год)':<20} | {'LCOE (грн/кВт-год)':<19}")
    print("-"*100)
    print(f"{'Сонячна ФЕС':<20} | {solar_params['capex_per_kw']:<15.1f} | {solar_params['opex_fixed_per_kw_year']:<18.1f} | {solar_params['fuel_cost_per_kwh']:<20.2f} | {solar_lcoe:<19.4f}")
    print(f"{'Вугільна ТЕС':<20} | {coal_params['capex_per_kw']:<15.1f} | {coal_params['opex_fixed_per_kw_year']:<18.1f} | {coal_params['fuel_cost_per_kwh']:<20.2f} | {coal_lcoe:<19.4f}")
    print(f"{'Газотурбінна ТЕС':<20} | {gas_params['capex_per_kw']:<15.1f} | {gas_params['opex_fixed_per_kw_year']:<18.1f} | {gas_params['fuel_cost_per_kwh']:<20.2f} | {gas_lcoe:<19.4f}")
    print("="*100)

    # =========================================================================
    # Частина 2: Розрахунок штрафів за небаланси та економії
    # =========================================================================
    # Ціна небалансу на ринку України (4.5 грн/кВт-год)
    imbalance_price_uah = 4.5
    hours_per_year = 8760

    # 2.1 Розрахунок для тестової ФЕС (30 кВт)
    # Показники точності (MAE):
    # - Традиційна модель (Persistence) має MAE ~ 1.50 кВт (без ML)
    # - Базова модель CNN-LSTM має MAE = 0.2711 кВт (згідно з табл. 7.1)
    # - Мультимасштабний ансамбль має MAE = 0.2974 кВт
    mae_persistence = 1.50
    mae_base = 0.2711
    mae_ensemble = 0.2974  # MAE на тестовому тижні

    # Річні штрафи для ФЕС 30 кВт (грн)
    penalty_persistence_30kw_uah = mae_persistence * hours_per_year * imbalance_price_uah
    penalty_base_30kw_uah = mae_base * hours_per_year * imbalance_price_uah
    penalty_ensemble_30kw_uah = mae_ensemble * hours_per_year * imbalance_price_uah

    # Річні заощадження від впровадження ML порівняно з Persistence для 30 кВт (грн)
    savings_base_30kw_uah = ImbalanceCostCalculator.calculate_savings(mae_persistence, mae_base, hours_per_year, imbalance_price_uah)
    savings_ensemble_30kw_uah = ImbalanceCostCalculator.calculate_savings(mae_persistence, mae_ensemble, hours_per_year, imbalance_price_uah)

    # 2.2 Масштабування до промислової ФЕС (10 МВт = 10000 кВт)
    # Коефіцієнт масштабування = 10000 / 30 = 333.33
    scale_factor = 10000.0 / 30.0
    
    penalty_persistence_10mw_uah = penalty_persistence_30kw_uah * scale_factor
    penalty_base_10mw_uah = penalty_base_30kw_uah * scale_factor
    penalty_ensemble_10mw_uah = penalty_ensemble_30kw_uah * scale_factor

    savings_base_10mw_uah = savings_base_30kw_uah * scale_factor
    savings_ensemble_10mw_uah = savings_ensemble_30kw_uah * scale_factor

    # Зниження штрафів у відсотках
    pct_reduction_base = ((penalty_persistence_30kw_uah - penalty_base_30kw_uah) / penalty_persistence_30kw_uah) * 100
    pct_reduction_ensemble = ((penalty_persistence_30kw_uah - penalty_ensemble_30kw_uah) / penalty_persistence_30kw_uah) * 100

    print("\n" + "="*80)
    print("ЕКОНОМІЧНИЙ ЕФЕКТ ВІД ЗНИЖЕННЯ ШТРАФІВ ЗА ДИСБАЛАНСИ")
    print("="*80)
    print(f"{'Показник / Сценарій':<35} | {'Без ML (Persistence)':<20} | {'Модель CNN-LSTM':<18}")
    print("-"*80)
    print(f"{'Середня помилка MAE (30 кВт), кВт':<35} | {mae_persistence:<20.2f} | {mae_base:<18.4f}")
    print(f"{'Річний штраф (30 кВт), грн':<35} | {penalty_persistence_30kw_uah:<20.2f} | {penalty_base_30kw_uah:<18.2f}")
    print(f"{'Річна економія (30 кВт), грн':<35} | {'-':<20} | {savings_base_30kw_uah:<18.2f}")
    print("-"*80)
    print(f"{'Середня помилка MAE (10 МВт), кВт':<35} | {mae_persistence*scale_factor:<20.1f} | {mae_base*scale_factor:<18.1f}")
    print(f"{'Річний штраф (10 МВт), грн':<35} | {penalty_persistence_10mw_uah:<20.2f} | {penalty_base_10mw_uah:<18.2f}")
    print(f"{'Річна економія (10 МВт), грн':<35} | {'-':<20} | {savings_base_10mw_uah:<18.2f}")
    print(f"{'Зниження штрафів, %':<35} | {'-':<20} | {pct_reduction_base:<18.2f}%")
    print("="*80)

    # =========================================================================
    # Частина 3: Побудова та збереження графіка порівняння LCOE
    # =========================================================================
    # Перевіримо наявність директорії docs/images
    images_dir = os.path.join("docs", "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir, exist_ok=True)
        logger.info(f"Створено директорію для графіків: {images_dir}")

    # Створення стовпчастої діаграми
    generations = ["Сонячна ФЕС", "Вугільна ТЕС", "Газотурбінна ТЕС"]
    lcoe_values = [solar_lcoe, coal_lcoe, gas_lcoe]
    colors = ["#f39c12", "#7f8c8d", "#e74c3c"]  # Помаранчевий, Сірий, Червоний

    plt.figure(figsize=(10, 6))
    bars = plt.bar(generations, lcoe_values, color=colors, width=0.5, edgecolor="black", linewidth=1.2)
    
    # Додавання значень над стовпчиками
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.08, f"{yval:.2f} грн", ha="center", va="bottom", fontsize=11, fontweight="bold")

    plt.title("Порівняльний аналіз LCOE (нормованої вартості електроенергії)", fontsize=14, fontweight="bold", pad=15)
    plt.ylabel("LCOE (грн за кВт-год)", fontsize=12, labelpad=10)
    plt.ylim(0, max(lcoe_values) + 0.8)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    
    # Оформлення стилю рамки
    plt.gca().spines["top"].set_visible(False)
    plt.gca().spines["right"].set_visible(False)
    plt.gca().spines["left"].set_linewidth(1.2)
    plt.gca().spines["bottom"].set_linewidth(1.2)
    
    plot_path = os.path.join(images_dir, "lcoe_comparison.png")
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    logger.info(f"Порівняльний графік LCOE успішно збережено у: {plot_path}")

if __name__ == "__main__":
    main()
