
from datetime import datetime, date
from zoneinfo import ZoneInfo

from adhanpy.PrayerTimes import PrayerTimes
from adhanpy.calculation import CalculationParameters
from adhanpy.calculation.Madhab import Madhab


# Prayer Times configuration
LOCATION = "Piscataway, New Jersey"
COORDINATES = (40.5548, -74.4643)  # Approximate city center
TIMEZONE = ZoneInfo("America/New_York")

# ISNA calculation angles
parameters = CalculationParameters(
    fajr_angle=15.0,
    isha_angle=15.0
)

# Hanafi Asr calculation
parameters.madhab = Madhab.HANAFI


def get_prayer_times(target_date=None):
    """Calculate daily prayer times for Piscataway."""

    if target_date is None:
        target_date = date.today()

    calculation_date = datetime.combine(
        target_date,
        datetime.min.time()
    )

    times = PrayerTimes(
        COORDINATES,
        calculation_date,
        calculation_parameters=parameters,
        time_zone=TIMEZONE
    )

    return {
        "Fajr": times.fajr,
        "Sunrise": times.sunrise,
        "Dhuhr": times.dhuhr,
        "Asr": times.asr,
        "Maghrib": times.maghrib,
        "Isha": times.isha,
    }


def display_prayer_times():
    """Display today's prayer schedule."""

    print("\n" + "=" * 38)
    print("        PRAYER TIMES")
    print("=" * 38)
    print(f"Location: {LOCATION}")
    print(f"Date: {date.today()}")
    print("-" * 38)

    prayers = get_prayer_times()

    for prayer, prayer_time in prayers.items():
        print(
            f"{prayer:<12} "
            f"{prayer_time.strftime('%I:%M %p')}"
        )

    print("=" * 38)


if __name__ == "__main__":
    display_prayer_times()

