"""
Time-slot maths for the doctors' weekly schedules. Pure functions, easy to test.

A schedule looks like: {"days": ["Mon", "Wed"], "start": "10:00", "end": "14:00", "slot_minutes": 30}
Days and times are in the clinic's time zone (CLINIC_TIMEZONE); results are in UTC.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import get_settings

settings = get_settings()

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_AHEAD = 7        # how many days (starting today) can be booked
MIN_LEAD_HOURS = 2    # a slot must start at least this long from now


def clinic_tz() -> ZoneInfo:
    return ZoneInfo(settings.clinic_timezone)


def _parse_time(text: str) -> time:
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def slots_by_day(schedule: dict, now_utc: datetime) -> dict[date, list[datetime]]:
    """
    {clinic-local date: [slot start times in UTC]} for the next DAYS_AHEAD days.
    Only slots that are still bookable (at least MIN_LEAD_HOURS away) are included.
    """
    tz = clinic_tz()
    today = now_utc.astimezone(tz).date()
    earliest = now_utc + timedelta(hours=MIN_LEAD_HOURS)
    step = timedelta(minutes=schedule["slot_minutes"])
    start_t, end_t = _parse_time(schedule["start"]), _parse_time(schedule["end"])

    result: dict[date, list[datetime]] = {}
    for offset in range(DAYS_AHEAD):
        day = today + timedelta(days=offset)
        if DAY_NAMES[day.weekday()] not in schedule["days"]:
            continue

        current = datetime.combine(day, start_t, tzinfo=tz)
        end = datetime.combine(day, end_t, tzinfo=tz)
        slots: list[datetime] = []
        while current + step <= end:
            as_utc = current.astimezone(timezone.utc)
            if as_utc >= earliest:
                slots.append(as_utc)
            current += step
        if slots:
            result[day] = slots
    return result


def day_label(day: date) -> str:
    return day.strftime("%a %d %b")  # Wed 14 Oct


def time_label(start_utc: datetime) -> str:
    return start_utc.astimezone(clinic_tz()).strftime("%H:%M")


def full_label(start_utc: datetime) -> str:
    return start_utc.astimezone(clinic_tz()).strftime("%a %d %b, %H:%M")


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")