import argparse
import asyncio
import logging
import sys
from app.core.config import settings
from app.core.data.pipeline import DataPipeline

# Конфігурація логування
logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("collect_data")


async def main():
    parser = argparse.ArgumentParser(
        description="CLI для збору та об'єднання даних сонячної генерації та погоди."
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default="2017-03-01",
        help="Початкова дата у форматі YYYY-MM-DD (за замовчуванням: 2017-03-01)"
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default="2019-12-31",
        help="Кінцева дата у форматі YYYY-MM-DD (за замовчуванням: 2019-12-31)"
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=settings.STATION_LATITUDE,
        help=f"Широта ФЕС (за замовчуванням: {settings.STATION_LATITUDE})"
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=settings.STATION_LONGITUDE,
        help=f"Довгота ФЕС (за замовчуванням: {settings.STATION_LONGITUDE})"
    )

    args = parser.parse_args()

    # Оновлюємо конфігурацію тимчасово для запуску
    settings.STATION_LATITUDE = args.lat
    settings.STATION_LONGITUDE = args.lon

    logger.info("Ініціалізація конвеєра даних...")
    pipeline = DataPipeline()
    
    try:
        output_path = await pipeline.run(
            start_date=args.start_date,
            end_date=args.end_date
        )
        logger.info(f"Процес завершено успішно! Файл збережено в: {output_path}")
    except Exception as e:
        logger.critical(f"Помилка під час збору даних: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
