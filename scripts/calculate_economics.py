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
        "capex_per_kw": 900.0,
        "opex_fixed_per_kw_year": 20.0,
        "fuel_cost_per_kwh": 0.0,
        "annual_generation_kwh_per_kw": 1314.0,  # КВВП = 15% (1314 год)
        "discount_rate": discount_rate,
        "lifetime_years": 25
    }
    
    # 2. Газотурбінна ТЕС
    gas_params = {
        "capex_per_kw": 1100.0,
        "opex_fixed_per_kw_year": 25.0,
        "fuel_cost_per_kwh": 0.07,  # Паливна складова
        "annual_generation_kwh_per_kw": 2628.0,  # КВВП = 30% (піковий режим)
        "discount_rate": discount_rate,
        "lifetime_years": 30
    }
    
    # 3. Вугільна ТЕС
    coal_params = {
        "capex_per_kw": 3000.0,
        "opex_fixed_per_kw_year": 40.0,
        "fuel_cost_per_kwh": 0.04,  # Паливна складова (дешевше за газ)
        "annual_generation_kwh_per_kw": 5256.0,  # КВВП = 60% (базовий режим)
        "discount_rate": discount_rate,
        "lifetime_years": 40
    }

    # Розрахунок LCOE ($ за кВт-год)
    solar_lcoe = LcoeCalculator.calculate_lcoe(**solar_params)
    gas_lcoe = LcoeCalculator.calculate_lcoe(**gas_params)
    coal_lcoe = LcoeCalculator.calculate_lcoe(**coal_params)

    # Виведення результатів LCOE
    print("\n" + "="*80)
    print("ПОРІВНЯЛЬНИЙ АНАЛІЗ LCOE ДЛЯ РІЗНИХ ТИПІВ ГЕНЕРАЦІЇ ($/кВт-год)")
    print("="*80)
    print(f"{'Тип генерації':<20} | {'CAPEX ($/кВт)':<13} | {'OPEX ($/кВт*рік)':<16} | {'Паливо ($/кВт-год)':<19} | {'LCOE ($/кВт-год)':<17}")
    print("-"*80)
    print(f"{'Сонячна ФЕС':<20} | {solar_params['capex_per_kw']:<13.1f} | {solar_params['opex_fixed_per_kw_year']:<16.1f} | {solar_params['fuel_cost_per_kwh']:<19.2f} | {solar_lcoe:<17.4f}")
    print(f"{'Вугільна ТЕС':<20} | {coal_params['capex_per_kw']:<13.1f} | {coal_params['opex_fixed_per_kw_year']:<16.1f} | {coal_params['fuel_cost_per_kwh']:<19.2f} | {coal_lcoe:<17.4f}")
    print(f"{'Газотурбінна ТЕС':<20} | {gas_params['capex_per_kw']:<13.1f} | {gas_params['opex_fixed_per_kw_year']:<16.1f} | {gas_params['fuel_cost_per_kwh']:<19.2f} | {gas_lcoe:<17.4f}")
    print("="*80)

    # =========================================================================
    # Частина 2: Розрахунок штрафів за небаланси та економії
    # =========================================================================
    # Ціна небалансу на ринку України (~4.5 грн/кВт-год або $0.11/кВт-год)
    imbalance_price_usd = 0.11
    imbalance_price_uah = 4.5
    hours_per_year = 8760

    # 2.1 Розрахунок для тестової ФЕС (30 кВт)
    # Показники точності (MAE):
    # - Традиційна модель (Persistence) має MAE ~ 1.50 кВт (без ML)
    # - Базова модель CNN-LSTM має MAE = 0.2711 кВт (згідно з табл. 7.1)
    # - Мультимасштабний ансамбль має MAE = 0.2974 кВт (але значно нижчий MAPE = 8.54% проти 9.06%)
    # Для розрахунку фінансового ефекту порівняємо ML-прогнозування з базовим підходом без ML (Persistence),
    # а також оцінимо вплив покращення MAPE (якість профілю генерації) для великої ФЕС.
    mae_persistence = 1.50
    mae_base = 0.2711
    mae_ensemble = 0.2974  # MAE на тестовому тижні

    # Річні штрафи для ФЕС 30 кВт ($)
    penalty_persistence_30kw = mae_persistence * hours_per_year * imbalance_price_usd
    penalty_base_30kw = mae_base * hours_per_year * imbalance_price_usd
    penalty_ensemble_30kw = mae_ensemble * hours_per_year * imbalance_price_usd

    # Річні заощадження від впровадження ML порівняно з Persistence для 30 кВт ($ та грн)
    savings_base_30kw_usd = ImbalanceCostCalculator.calculate_savings(mae_persistence, mae_base, hours_per_year, imbalance_price_usd)
    savings_base_30kw_uah = ImbalanceCostCalculator.calculate_savings(mae_persistence, mae_base, hours_per_year, imbalance_price_uah)

    savings_ensemble_30kw_usd = ImbalanceCostCalculator.calculate_savings(mae_persistence, mae_ensemble, hours_per_year, imbalance_price_usd)
    savings_ensemble_30kw_uah = ImbalanceCostCalculator.calculate_savings(mae_persistence, mae_ensemble, hours_per_year, imbalance_price_uah)

    # 2.2 Масштабування до промислової ФЕС (10 МВт = 10000 кВт)
    # Коефіцієнт масштабування = 10000 / 30 = 333.33
    scale_factor = 10000.0 / 30.0
    
    penalty_persistence_10mw = penalty_persistence_30kw * scale_factor
    penalty_base_10mw = penalty_base_30kw * scale_factor
    penalty_ensemble_10mw = penalty_ensemble_30kw * scale_factor

    savings_base_10mw_usd = savings_base_30kw_usd * scale_factor
    savings_base_10mw_uah = savings_base_30kw_uah * scale_factor
    savings_ensemble_10mw_usd = savings_ensemble_30kw_usd * scale_factor
    savings_ensemble_10mw_uah = savings_ensemble_30kw_uah * scale_factor

    # Зниження штрафів у відсотках
    pct_reduction_base = ((penalty_persistence_30kw - penalty_base_30kw) / penalty_persistence_30kw) * 100
    pct_reduction_ensemble = ((penalty_persistence_30kw - penalty_ensemble_30kw) / penalty_persistence_30kw) * 100

    print("\n" + "="*80)
    print("ЕКОНОМІЧНИЙ ЕФЕКТ ВІД ЗНИЖЕННЯ ШТРАФІВ ЗА ДИСБАЛАНСИ")
    print("="*80)
    print(f"{'Показник / Сценарій':<35} | {'Без ML (Persistence)':<20} | {'Модель CNN-LSTM':<18}")
    print("-"*80)
    print(f"{'Середня помилка MAE (30 кВт), кВт':<35} | {mae_persistence:<20.2f} | {mae_base:<18.4f}")
    print(f"{'Річний штраф (30 кВт), грн':<35} | {penalty_persistence_30kw*imbalance_price_uah/imbalance_price_usd:<20.2f} | {penalty_base_30kw*imbalance_price_uah/imbalance_price_usd:<18.2f}")
    print(f"{'Річний штраф (30 кВт), $':<35} | {penalty_persistence_30kw:<20.2f} | {penalty_base_30kw:<18.2f}")
    print(f"{'Річна економія (30 кВт), грн':<35} | {'-':<20} | {savings_base_30kw_uah:<18.2f}")
    print(f"{'Річна економія (30 кВт), $':<35} | {'-':<20} | {savings_base_30kw_usd:<18.2f}")
    print("-"*80)
    print(f"{'Середня помилка MAE (10 МВт), кВт':<35} | {mae_persistence*scale_factor:<20.1f} | {mae_base*scale_factor:<18.1f}")
    print(f"{'Річний штраф (10 МВт), грн':<35} | {penalty_persistence_10mw*imbalance_price_uah/imbalance_price_usd:<20.2f} | {penalty_base_10mw*imbalance_price_uah/imbalance_price_usd:<18.2f}")
    print(f"{'Річний штраф (10 МВт), $':<35} | {penalty_persistence_10mw:<20.2f} | {penalty_base_10mw:<18.2f}")
    print(f"{'Річна економія (10 МВт), грн':<35} | {'-':<20} | {savings_base_10mw_uah:<18.2f}")
    print(f"{'Річна економія (10 МВт), $':<35} | {'-':<20} | {savings_base_10mw_usd:<18.2f}")
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
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.003, f"${yval:.4f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    plt.title("Порівняльний аналіз LCOE (нормованої вартості електроенергії)", fontsize=14, fontweight="bold", pad=15)
    plt.ylabel("LCOE ($ за кВт-год)", fontsize=12, labelpad=10)
    plt.ylim(0, max(lcoe_values) + 0.02)
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
