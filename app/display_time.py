"""Display event instants in Vietnam; source reporting dates keep their own calendar."""
from datetime import datetime, timedelta, timezone

VIETNAM = timezone(timedelta(hours=7))


def vietnam_time(value):
    if not value:
        return 'Chưa ghi nhận'
    try:
        stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(VIETNAM).strftime('%H:%M %d/%m/%Y GMT+7')
    except (TypeError, ValueError, OverflowError):
        return 'Chưa ghi nhận'
