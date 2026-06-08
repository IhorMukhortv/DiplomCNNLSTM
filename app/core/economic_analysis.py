import logging
from typing import Union
import numpy as np

logger = logging.getLogger(__name__)


class LcoeCalculator:
    """
    Клас для розрахунку LCOE (Levelized Cost of Electricity) для різних джерел генерації.
    """

    @staticmethod
    def calculate_lcoe(
        capex_per_kw: float,
        opex_fixed_per_kw_year: float,
        fuel_cost_per_kwh: float,
        annual_generation_kwh_per_kw: float,
        discount_rate: float,
        lifetime_years: int
    ) -> float:
        """
        Розрахунок LCOE за стандартною дисконтованою формулою:
        LCOE = (CAPEX + Sum(t=1..N)[ (OPEX_fixed + Fuel_cost * Generation) / (1 + r)^t ]) /
               Sum(t=1..N)[ Generation / (1 + r)^t ]

        Параметри:
            capex_per_kw: Початкові капітальні витрати на 1 кВт встановленої потужності ($ або грн).
            opex_fixed_per_kw_year: Щорічні фіксовані витрати на експлуатацію та обслуговування на 1 кВт ($ або грн).
            fuel_cost_per_kwh: Витрати на паливо на 1 кВт-год генерації ($ або грн).
            annual_generation_kwh_per_kw: Річний обсяг генерації електроенергії на 1 кВт встановленої потужності (кВт-год).
            discount_rate: Ставка дисконтування (частка від 1, наприклад, 0.10 для 10%).
            lifetime_years: Термін служби об'єкта в роках.

        Повертає:
            Значення LCOE в одиницях валюти за кВт-год.
        """
        logger.debug(
            f"Ініціалізація розрахунку LCOE: CAPEX={capex_per_kw}, OPEX={opex_fixed_per_kw_year}, "
            f"Fuel={fuel_cost_per_kwh}, Gen={annual_generation_kwh_per_kw}, r={discount_rate}, N={lifetime_years}"
        )

        if discount_rate < 0 or lifetime_years <= 0 or annual_generation_kwh_per_kw <= 0:
            logger.error("Некоректні вхідні параметри для розрахунку LCOE (дисконтна ставка < 0, років <= 0 або річна генерація <= 0).")
            raise ValueError("Вхідні параметри розрахунку мають бути додатними числами.")

        total_discounted_cost = capex_per_kw
        total_discounted_generation = 0.0

        for t in range(1, lifetime_years + 1):
            discount_factor = (1 + discount_rate) ** t
            annual_cost = opex_fixed_per_kw_year + (fuel_cost_per_kwh * annual_generation_kwh_per_kw)
            
            total_discounted_cost += annual_cost / discount_factor
            total_discounted_generation += annual_generation_kwh_per_kw / discount_factor

        lcoe = total_discounted_cost / total_discounted_generation
        logger.info(f"Розраховано LCOE: {lcoe:.4f} за кВт-год")
        return lcoe


class ImbalanceCostCalculator:
    """
    Клас для розрахунку фінансових витрат від дисбалансів та оцінки економічної вигоди.
    """

    @staticmethod
    def calculate_imbalance_penalty(
        actual: Union[np.ndarray, list],
        predicted: Union[np.ndarray, list],
        imbalance_price_per_kwh: float
    ) -> float:
        """
        Розрахунок сумарного штрафу за дисбаланс за формулою:
        Penalty = Sum(|Actual_i - Predicted_i|) * Imbalance_price

        Параметри:
            actual: Масив або список фактичних значень генерації (кВт-год).
            predicted: Масив або список прогнозованих значень генерації (кВт-год).
            imbalance_price_per_kwh: Вартість 1 кВт-год небалансу на балансуючому ринку.

        Повертає:
            Загальна сума штрафу.
        """
        act_arr = np.array(actual)
        pred_arr = np.array(predicted)

        if act_arr.shape != pred_arr.shape:
            logger.error(f"Неспівпадіння розмірностей масивів: actual={act_arr.shape}, predicted={pred_arr.shape}")
            raise ValueError("Масиви фактичних та прогнозованих значень повинні мати однакову довжину.")

        if imbalance_price_per_kwh < 0:
            logger.error(f"Некоректна ціна небалансу: {imbalance_price_per_kwh}")
            raise ValueError("Ціна небалансу не може бути від'ємною.")

        absolute_errors = np.abs(act_arr - pred_arr)
        total_imbalance_kwh = np.sum(absolute_errors)
        total_penalty = total_imbalance_kwh * imbalance_price_per_kwh

        logger.info(
            f"Розрахунок небалансів: точок={len(act_arr)}, сумарний небаланс={total_imbalance_kwh:.2f} кВт-год, "
            f"загальний штраф={total_penalty:.2f}"
        )
        return total_penalty

    @staticmethod
    def calculate_savings(
        mae_baseline_kw: float,
        mae_proposed_kw: float,
        hours: int,
        imbalance_price_per_kwh: float
    ) -> float:
        """
        Спрощений розрахунок річної економії від підвищення точності прогнозування:
        Savings = Hours * (MAE_baseline - MAE_proposed) * Imbalance_price

        Параметри:
            mae_baseline_kw: Середня абсолютна помилка базової моделі (кВт).
            mae_proposed_kw: Середня абсолютна помилка пропонованої моделі (кВт).
            hours: Кількість годин у періоді розрахунку (наприклад, 8760 для року).
            imbalance_price_per_kwh: Вартість 1 кВт-год небалансу.

        Повертає:
            Сума економії в грошовому еквіваленті.
        """
        if hours < 0 or imbalance_price_per_kwh < 0:
            raise ValueError("Кількість годин та ціна небалансу мають бути додатними.")

        delta_mae = mae_baseline_kw - mae_proposed_kw
        savings = hours * delta_mae * imbalance_price_per_kwh

        logger.info(
            f"Оцінка економії: Delta MAE={delta_mae:.4f} кВт, годин={hours}, "
            f"ціна небалансу={imbalance_price_per_kwh:.2f}, очікувана економія={savings:.2f}"
        )
        return savings
