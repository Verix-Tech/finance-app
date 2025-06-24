from datetime import datetime, timedelta

def get_start_end_date(days_before: int) -> tuple[str, str]:
    """
    Get the start date for the extract.
    """
    start_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_before)).strftime('%Y-%m-%d') if days_before > 0 else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    return start_date, end_date
