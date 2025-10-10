import os
import json
import time
import random
import pandas as pd
from pytrends.request import TrendReq

from bigquery_utils import upload_to_bigquery

# -------------------------------
# Load HHS regions dictionary
# -------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "HHS_regions_to_states.json")

regions_list = []
with open(JSON_PATH, "r") as f:
    for line in f:
        if line.strip():
            regions_list.append(json.loads(line))

# Convert to dict {region_id: [states]}
HHS_REGION_TO_STATES = {
    item['region_id']: item['states']
    for item in regions_list
}

# -------------------------------
# Config
# -------------------------------
KW_LIST = ["flu", "fever", "cough", "flu symptoms", "sore throat", "doordash", "uber eats", "postmates"]
TIMEFRAME = "today 5-y"
ALL_STATE_CSV_PATH = "country_trends.csv"

# -------------------------------
# Helper: safe build with retries
# -------------------------------
def safe_build_payload(pytrends, *args, **kwargs):
    for attempt in range(5):
        try:
            pytrends.build_payload(*args, **kwargs)
            return
        except Exception as e:
            wait_time = 60 * (attempt + 1) + random.randint(0, 30)
            print(f"Rate limited or error ({e}). Sleeping {wait_time} sec...")
            time.sleep(wait_time)
    raise RuntimeError("Too many retries, stopping.")

# -------------------------------
# Helper: check if historical data already exists on Big Query project
# -------------------------------
from google.cloud import bigquery

PROJECT_ID = "flu-project-473220"
DATASET_ID = "google_trends"
TABLE_ID = "country_trends"

client = bigquery.Client(project=PROJECT_ID)

def historical_data_exists():
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    try:
        table = client.get_table(table_ref)  # Will raise NotFound if missing
        # Optionally, load it into a DataFrame
        historical_data = client.list_rows(table).to_dataframe()
        return historical_data
    except Exception as e:
        # More precise: from google.api_core.exceptions import NotFound
        print("No historical data in BigQuery, building country trends for the first time...")
        return None


# -------------------------------
# Get data for a single state, single keyword trend
# -------------------------------
def get_state_trend(pytrends, state, kw):
    print(f"Fetching {state} – {kw}...")
    for attempt in range(5):
        try:
            safe_build_payload(pytrends, kw, timeframe=TIMEFRAME, geo=f"US-{state}")
            df = pytrends.interest_over_time()
            break
        except Exception as e:
            wait = 60 * (attempt + 1) + random.randint(0, 30)
            print(f"Hit 429 on {state} {kw}. Sleeping {wait}s...")
            time.sleep(wait)
    else:
        print(f"Failed to fetch {state} {kw} after retries.")
        return None

    if df.empty:
        return None
    if "isPartial" in df.columns:
        df = df.drop(columns=["isPartial"])
    df["state"] = state
    return df.reset_index()


# -------------------------------
# Main: loop through regions/states and keywords
# -------------------------------
import os
import json
import time
import random
import pandas as pd
from pytrends.request import TrendReq
from google.cloud import bigquery
from bigquery_utils import upload_to_bigquery


# -------------------------------
# Config
# -------------------------------
KW_LIST = ["flu", "fever", "cough", "flu symptoms", "sore throat", "doordash", "uber eats", "postmates"]
TIMEFRAME = "today 5-y"               # folder for individual state CSVs
FINAL_CSV_PATH = "country_trends.csv"   # combined file

PROJECT_ID = "flu-project-473220"
DATASET_ID = "google_trends"
TABLE_ID = "country_trends"

client = bigquery.Client(project=PROJECT_ID)

# -------------------------------
# Helpers
# -------------------------------
def historical_data_exists():
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    try:
        table = client.get_table(table_ref)  # will raise NotFound if table doesn't exist
        row_count = table.num_rows

        if row_count == 0:
            print("Table exists but is empty. No historical data.")
            return None

        # If there are rows, fetch them
        historical_data = client.list_rows(table).to_dataframe()
        return historical_data

    except Exception:
        print("No table found in BigQuery, building from scratch...")
        return None


def safe_build_payload(pytrends, *args, **kwargs):
    for attempt in range(5):
        try:
            pytrends.build_payload(*args, **kwargs)
            return
        except Exception as e:
            wait_time = 60 * (attempt + 1) + random.randint(0, 30)
            print(f"Rate limited or error ({e}). Sleeping {wait_time}s...")
            time.sleep(wait_time)
    raise RuntimeError("Too many retries, stopping.")

def get_state_trend(pytrends, state, kw):
    print(f"Fetching {state} – {kw}...")
    for attempt in range(5):
        try:
            safe_build_payload(pytrends, kw, timeframe=TIMEFRAME, geo=f"US-{state}")
            df = pytrends.interest_over_time()
            break
        except Exception as e:
            wait = 60 * (attempt + 1) + random.randint(0, 30)
            print(f"Hit 429 on {state} {kw}. Sleeping {wait}s...")
            time.sleep(wait)
    else:
        print(f"Failed to fetch {state} {kw} after retries.")
        return None

    if df.empty:
        return None
    if "isPartial" in df.columns:
        df = df.drop(columns=["isPartial"])
    df["state"] = state
    return df.reset_index()

# -------------------------------
# Main function
# -------------------------------
def main():
    pytrends = TrendReq(hl="en-US", tz=360)
    historical_data = historical_data_exists()

    if historical_data is None:
        print("Building full 5-year dataset...")
        all_states_df = pd.DataFrame()

        for region, states in HHS_REGION_TO_STATES.items():
            print(f"=== Region {region} ===")
            for state in states:
                kw_dfs = []
                for kw in KW_LIST:
                    df_kw = get_state_trend(pytrends, state, kw=[kw])
                    if df_kw is not None:
                        df_kw = df_kw.rename(columns={kw: f"{kw}"})
                        kw_dfs.append(df_kw[['date', kw]])
                    time.sleep(30)  # wait between keywords

                if not kw_dfs:
                    continue

                state_df = kw_dfs[0]
                for df_kw in kw_dfs[1:]:
                    state_df = state_df.merge(df_kw, on='date', how='outer')

                state_df['state'] = state
                state_df['region'] = int(region)

                # Save each state's DataFrame
                state_csv_path = os.path.join(f"trends_{state}.csv")
                state_df.to_csv(state_csv_path, index=False)
                print(f"Saved {state_csv_path}")

                all_states_df = pd.concat([all_states_df, state_df], ignore_index=True)
                time.sleep(120 + random.randint(0, 60))  # wait between states

        all_states_df = all_states_df.sort_values(by=["date", "region"])
        all_states_df.to_csv(FINAL_CSV_PATH, index=False)
        print(f"Saved combined CSV: {FINAL_CSV_PATH}")
        return all_states_df

    else:
        print("Historical data found in BigQuery.")
        print("Fetching most recent week only...")
        most_recent_date_hist = historical_data["date"].max()
        update_df = pd.DataFrame()

        for region, states in HHS_REGION_TO_STATES.items():
            for state in states:
                kw_dfs = []
                for kw in KW_LIST:
                    df_kw = get_state_trend(pytrends, state, kw=[kw])
                    if df_kw is not None:
                        df_kw = df_kw.rename(columns={kw: f"{kw}"})
                        kw_dfs.append(df_kw[['date', kw]])
                    time.sleep(30)

                if not kw_dfs:
                    continue

                state_df = kw_dfs[0]
                for df_kw in kw_dfs[1:]:
                    state_df = state_df.merge(df_kw, on='date', how='outer')

                state_df['state'] = state
                state_df['region'] = int(region)

                # Keep only new rows
                new_state_df = state_df[state_df['date'] > most_recent_date_hist]

                # Save each state CSV regardless (optional)
                state_csv_path = os.path.join(f"trends_{state}.csv")
                state_df.to_csv(state_csv_path, index=False)
                print(f"Saved {state_csv_path}")

                update_df = pd.concat([update_df, new_state_df], ignore_index=True)
                time.sleep(120 + random.randint(0, 60))

        if not update_df.empty:
            combined = pd.concat([historical_data, update_df], ignore_index=True)
            combined = combined.sort_values(by=["date", "region"])
            combined.to_csv(FINAL_CSV_PATH, index=False)
            print(f"Updated combined CSV: {FINAL_CSV_PATH}")
            # upload_to_bigquery(combined, PROJECT_ID, DATASET_ID, TABLE_ID)
            # print("Appended update into BigQuery.")
            return combined
        else:
            print("No new data this week.")
            return historical_data


if __name__ == "__main__":
    combined_df = main()
    print("Done. Final combined DataFrame shape:", combined_df.shape)







