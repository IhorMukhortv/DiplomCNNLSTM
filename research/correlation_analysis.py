import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr
from app.core.config import settings

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("correlation_analysis")


def calculate_correlations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Розраховує коефіцієнти кореляції Пірсона та Спірмена.
    """
    features = [
        "temperature_2m",
        "relative_humidity_2m",
        "cloud_cover",
        "direct_normal_irradiance",
        "diffuse_horizontal_irradiance",
        "global_horizontal_irradiance"
    ]
    target = "active_power_kw"

    results = []
    for feat in features:
        # Видаляємо пропуски для розрахунку кореляції
        df_clean = df[[feat, target]].dropna()
        if len(df_clean) < 2:
            continue
            
        p_val, p_sig = pearsonr(df_clean[feat], df_clean[target])
        s_val, s_sig = spearmanr(df_clean[feat], df_clean[target])
        
        results.append({
            "Параметр погоди": feat,
            "Пірсон (r)": p_val,
            "Пірсон p-value": p_sig,
            "Спірмен (rho)": s_val,
            "Спірмен p-value": s_sig
        })
        
    return pd.DataFrame(results)


def plot_correlation_heatmap(df: pd.DataFrame, output_dir: str):
    """
    Малює теплову карту кореляційної матриці.
    """
    cols = [
        "active_power_kw",
        "temperature_2m",
        "relative_humidity_2m",
        "cloud_cover",
        "direct_normal_irradiance",
        "diffuse_horizontal_irradiance",
        "global_horizontal_irradiance"
    ]
    
    # Створюємо україномовні назви для графіка
    ukr_labels = {
        "active_power_kw": "Генерація ФЕС",
        "temperature_2m": "Температура",
        "relative_humidity_2m": "Вологість",
        "cloud_cover": "Хмарність",
        "direct_normal_irradiance": "Пряма інсоляція (DNI)",
        "diffuse_horizontal_irradiance": "Дифузна інсоляція (DHI)",
        "global_horizontal_irradiance": "Глобальна інсоляція (GHI)"
    }
    
    df_sub = df[cols].rename(columns=ukr_labels)
    corr_matrix = df_sub.corr(method="pearson")
    
    plt.figure(figsize=(10, 8))
    sns.set_theme(style="white")
    
    # Генеруємо маску для верхнього трикутника
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    
    cmap = sns.diverging_palette(230, 20, as_cmap=True)
    
    sns.heatmap(
        corr_matrix,
        mask=mask,
        cmap=cmap,
        vmax=1.0,
        vmin=-1.0,
        center=0,
        square=True,
        linewidths=.5,
        cbar_kws={"shrink": .7, "label": "Коефіцієнт кореляції Пірсона"},
        annot=True,
        fmt=".2f"
    )
    
    plt.title("Матриця кореляції метеорологічних факторів та генерації ФЕС", fontsize=14, pad=15)
    plt.tight_layout()
    
    file_path = os.path.join(output_dir, "correlation_heatmap.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    logger.info(f"Збережено теплову карту: {file_path}")


def plot_scatter_plots(df: pd.DataFrame, output_dir: str):
    """
    Малює точкові графіки залежності генерації від інсоляції та температури.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # 1. Глобальна інсоляція (GHI) vs Генерація
    sns.scatterplot(
        data=df,
        x="global_horizontal_irradiance",
        y="active_power_kw",
        alpha=0.4,
        color="goldenrod",
        ax=axes[0]
    )
    axes[0].set_title("Залежність генерації від глобальної інсоляції (GHI)")
    axes[0].set_xlabel("Глобальна інсоляція GHI (Вт/м²)")
    axes[0].set_ylabel("Потужність генерації ФЕС (кВт)")
    axes[0].grid(True, linestyle="--", alpha=0.5)
    
    # 2. Температура vs Генерація
    sns.scatterplot(
        data=df,
        x="temperature_2m",
        y="active_power_kw",
        alpha=0.4,
        color="crimson",
        ax=axes[1]
    )
    axes[1].set_title("Залежність генерації від температури повітря")
    axes[1].set_xlabel("Температура повітря (°C)")
    axes[1].set_ylabel("Потужність генерації ФЕС (кВт)")
    axes[1].grid(True, linestyle="--", alpha=0.5)
    
    plt.suptitle("Аналіз розсіювання факторів впливу на сонячну генерацію", fontsize=16)
    plt.tight_layout()
    
    file_path = os.path.join(output_dir, "scatter_analysis.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    logger.info(f"Збережено точкові графіки: {file_path}")


def plot_seasonal_diurnals(df: pd.DataFrame, output_dir: str):
    """
    Малює середньодобові сезонні профілі інсоляції та генерації ФЕС.
    """
    df_copy = df.copy()
    df_copy["hour"] = pd.to_datetime(df_copy["timestamp"]).dt.hour
    df_copy["month"] = pd.to_datetime(df_copy["timestamp"]).dt.month
    
    # Визначення сезону
    def get_season(month):
        if month in [12, 1, 2]:
            return "Зима"
        elif month in [3, 4, 5]:
            return "Весна"
        elif month in [6, 7, 8]:
            return "Літо"
        else:
            return "Осінь"
            
    df_copy["Сезон"] = df_copy["month"].apply(get_season)
    
    # Агрегація за сезоном та годинами
    diurnal = df_copy.groupby(["Сезон", "hour"])[["active_power_kw", "global_horizontal_irradiance"]].mean().reset_index()
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Кольори сезонів
    colors = {
        "Літо": "orange",
        "Весна": "green",
        "Осінь": "brown",
        "Зима": "blue"
    }
    
    # 1. Добовий профіль інсоляції (GHI)
    sns.lineplot(
        data=diurnal,
        x="hour",
        y="global_horizontal_irradiance",
        hue="Сезон",
        palette=colors,
        marker="o",
        ax=axes[0]
    )
    axes[0].set_title("Середньодобова глобальна інсоляція за сезонами")
    axes[0].set_xlabel("Година доби (UTC)")
    axes[0].set_ylabel("Глобальна інсоляція GHI (Вт/м²)")
    axes[0].set_xticks(range(0, 24, 2))
    axes[0].grid(True, linestyle="--", alpha=0.5)
    
    # 2. Добовий профіль генерації ФЕС
    sns.lineplot(
        data=diurnal,
        x="hour",
        y="active_power_kw",
        hue="Сезон",
        palette=colors,
        marker="s",
        ax=axes[1]
    )
    axes[1].set_title("Середньодобова генерація ФЕС за сезонами")
    axes[1].set_xlabel("Година доби (UTC)")
    axes[1].set_ylabel("Потужність ФЕС (кВт)")
    axes[1].set_xticks(range(0, 24, 2))
    axes[1].grid(True, linestyle="--", alpha=0.5)
    
    plt.suptitle("Добові профілі сонячної активності та виробітку енергії", fontsize=16)
    plt.tight_layout()
    
    file_path = os.path.join(output_dir, "seasonal_diurnal_profiles.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    logger.info(f"Збережено сезонні профілі: {file_path}")


def main():
    csv_path = os.path.join(settings.RAW_DATA_DIR, "pv_weather_data.csv")
    if not os.path.exists(csv_path):
        logger.error(f"Файл даних не знайдено: {csv_path}. Спочатку запустіть збір даних.")
        return

    logger.info(f"Завантаження даних з {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Розрахунок кореляції
    logger.info("Розрахунок коефіцієнтів кореляції...")
    corr_df = calculate_correlations(df)
    
    # Вивід результатів у лог
    print("\n" + "="*80)
    print("      РЕЗУЛЬТАТИ КОРЕЛЯЦІЙНОГО АНАЛІЗУ МЕТЕОРОЛОГІЧНИХ ЧИННИКІВ")
    print("="*80)
    for idx, row in corr_df.iterrows():
        print(f"Параметр: {row['Параметр погоди']}")
        print(f"  - Коефіцієнт Пірсона (r):   {row['Пірсон (r)']:+.4f} (p-value: {row['Пірсон p-value']:.2e})")
        print(f"  - Коефіцієнт Спірмена (rho): {row['Спірмен (rho)']:+.4f} (p-value: {row['Спірмен p-value']:.2e})")
        print("-"*80)
    
    # Генерація графіків
    logger.info("Генерація та збереження графіків...")
    output_dir = settings.PLOTS_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    plot_correlation_heatmap(df, output_dir)
    plot_scatter_plots(df, output_dir)
    plot_seasonal_diurnals(df, output_dir)
    
    logger.info("Аналіз та візуалізацію успішно завершено.")


if __name__ == "__main__":
    main()
