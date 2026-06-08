import pytest
import numpy as np
from app.core.economic_analysis import LcoeCalculator, ImbalanceCostCalculator


def test_lcoe_calculation_basic():
    """Перевірка базового розрахунку LCOE."""
    # CAPEX = 1000, OPEX = 20/рік, Fuel = 0, Generation = 1000/рік, r = 0.10, N = 10 років.
    # Дисконтована сума витрат = 1000 + Sum(t=1..10) [ 20 / 1.1^t ]
    # Дисконтована сума генерації = Sum(t=1..10) [ 1000 / 1.1^t ]
    # оскільки OPEX та Generation константні, річний OPEX / річна Generation = 20 / 1000 = 0.02
    # LCOE = (1000 + 20 * Factor) / (1000 * Factor) = (1000 / (1000 * Factor)) + 0.02
    # де Factor = Sum(t=1..10) [ 1 / 1.1^t ] = 6.144567
    # LCOE = (1000 / 6144.567) + 0.02 = 0.16274 + 0.02 = 0.18274
    
    lcoe = LcoeCalculator.calculate_lcoe(
        capex_per_kw=1000.0,
        opex_fixed_per_kw_year=20.0,
        fuel_cost_per_kwh=0.0,
        annual_generation_kwh_per_kw=1000.0,
        discount_rate=0.10,
        lifetime_years=10
    )
    
    assert lcoe == pytest.approx(0.18274, abs=1e-4)


def test_lcoe_with_fuel():
    """Перевірка розрахунку LCOE для паливних станцій."""
    # Вугільна генерація: CAPEX = 3000, OPEX = 40, Fuel = 0.04, Generation = 5000, r = 0.10, N = 20 років.
    lcoe = LcoeCalculator.calculate_lcoe(
        capex_per_kw=3000.0,
        opex_fixed_per_kw_year=40.0,
        fuel_cost_per_kwh=0.04,
        annual_generation_kwh_per_kw=5000.0,
        discount_rate=0.10,
        lifetime_years=20
    )
    assert lcoe > 0.04  # LCOE має бути більшим за паливну складову


def test_lcoe_invalid_inputs():
    """Перевірка викиду винятків при некоректних вхідних даних LCOE."""
    with pytest.raises(ValueError):
        LcoeCalculator.calculate_lcoe(
            capex_per_kw=1000.0,
            opex_fixed_per_kw_year=20.0,
            fuel_cost_per_kwh=0.0,
            annual_generation_kwh_per_kw=0.0,  # Нульова генерація
            discount_rate=0.10,
            lifetime_years=10
        )

    with pytest.raises(ValueError):
        LcoeCalculator.calculate_lcoe(
            capex_per_kw=1000.0,
            opex_fixed_per_kw_year=20.0,
            fuel_cost_per_kwh=0.0,
            annual_generation_kwh_per_kw=1000.0,
            discount_rate=-0.05,  # Від'ємна ставка дисконтування
            lifetime_years=10
        )


def test_imbalance_penalty_calculation():
    """Перевірка розрахунку штрафів за небаланси."""
    actual = [10.0, 15.0, 20.0, 5.0]
    predicted = [12.0, 14.0, 25.0, 5.0]
    # Помилки: |10-12|=2, |15-14|=1, |20-25|=5, |5-5|=0. Сума помилок = 8.
    # Ціна = 4.5 грн/кВт-год. Штраф = 8 * 4.5 = 36.0.
    
    penalty = ImbalanceCostCalculator.calculate_imbalance_penalty(
        actual=actual,
        predicted=predicted,
        imbalance_price_per_kwh=4.5
    )
    
    assert penalty == pytest.approx(36.0)


def test_imbalance_penalty_dimension_mismatch():
    """Перевірка винятку при різній довжині вхідних масивів."""
    actual = [10.0, 15.0]
    predicted = [12.0]
    
    with pytest.raises(ValueError):
        ImbalanceCostCalculator.calculate_imbalance_penalty(
            actual=actual,
            predicted=predicted,
            imbalance_price_per_kwh=4.5
        )


def test_savings_calculation():
    """Перевірка розрахунку економії."""
    # MAE baseline = 0.2711 кВт, MAE proposed = 0.2500 кВт.
    # Різниця = 0.0211 кВт. Годин = 8760. Ціна = 4.5 грн.
    # Економія = 0.0211 * 8760 * 4.5 = 831.762 грн.
    
    savings = ImbalanceCostCalculator.calculate_savings(
        mae_baseline_kw=0.2711,
        mae_proposed_kw=0.2500,
        hours=8760,
        imbalance_price_per_kwh=4.5
    )
    
    assert savings == pytest.approx(831.762, abs=1e-3)
