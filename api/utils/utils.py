import pandas as pd
from datetime import datetime, timedelta


def get_start_end_date(days_before: int) -> tuple[str, str]:
    """
    Get the start date for the extract.
    """
    start_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_before)).strftime('%Y-%m-%d') if days_before > 0 else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    return start_date, end_date

def make_where_string(filter: dict) -> str:
    """
    Make the where string for the query.
    """
    conditions = []
    for key, value in filter.items():
        conditions.append(f"{key} {value["operator"]} '{value["value"]}'")

    return " and ".join(conditions)

def make_aggr_logic(mode: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Make the aggr logic for the query.
    """
    modes = {
        "day": "D",
        "week": "W",
        "month": "ME",
        "year": "YE"
    }
    df = df.set_index('transaction_timestamp').resample(modes[mode]).agg({'transaction_revenue': 'sum'}).reset_index()

    return df

df = pd.DataFrame({
    "transaction_timestamp": ["2025-01-01", "2025-01-02", "2025-01-03"],
    "transaction_revenue": [100, 200, 300]
})

aggr = {"mode": "day", "activated": True}

df['transaction_timestamp'] = pd.to_datetime(df['transaction_timestamp'])

print(make_aggr_logic(aggr["mode"], df))