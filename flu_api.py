# flu_api.py
"""
Functions to fetch influenza surveillance data from Delphi Epidata (FluView).
"""

import pandas as pd
from delphi_epidata import Epidata
from epiweeks import Week


def fetch_fluview_hhs(start_epiweek=200920, end_epiweek=999999) -> pd.DataFrame:
    """
    Fetch FluView ILI data for all 10 HHS regions from Delphi Epidata API.

    Parameters
    ----------
    start_epiweek : int
        First epiweek to include (Default: 20th week of 2009).
    end_epiweek : int
        Last epiweek to include (Default: Most current week).

    Returns
    -------
    pd.DataFrame
        FluView ILI data for HHS regions with columns such as:
        ['release_date', 'region', 'issue', 'epiweek', 'lag', 'num_ili',
         'num_patients', 'num_providers', 'wili', 'ili', etc.]
    """
    regions = [f"hhs{i}" for i in range(1, 11)]

    res = Epidata.fluview(
        regions=regions,
        epiweeks=Epidata.range(start_epiweek, end_epiweek)
    )

    if res.get("result") != 1 or "epidata" not in res:
        raise RuntimeError(f"Failed to fetch data: {res.get('message')}")

    df = pd.DataFrame(res["epidata"])
    return df

def clean_fluview_data(df) -> pd.DataFrame:
    df['region'] = df['region'].str.replace('hhs', '').astype(int)
    df['release_date'] = pd.to_datetime(df['release_date'])
    df['week_start'] = df['epiweek'].apply(lambda ew: Week(ew // 100, ew % 100).startdate())
    return df[['region', 'release_date', 'week_start', 'num_patients', 'num_ili', 'ili', 'wili']]


if __name__ == "__main__":
    # Example usage: fetch and preview
    df = clean_fluview_data(fetch_fluview_hhs())
    print(df.head())
    print(f"Fetched {len(df)} rows")
