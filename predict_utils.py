def compute_averages_per_region(combined_table, trend_cols):
    region_avgs = (
        combined_table
        .groupby(["region", "week_start"])[trend_cols + ["wili"]]
        .mean()
        .reset_index()
    )
    # Rename columns to have _region_avg suffix
    region_avgs = region_avgs.rename(
        columns={col: f"{col}_region_avg" for col in trend_cols + ["wili"]}
    )

    # Merge back into original DataFrame
    combined_table = combined_table.merge(
        region_avgs, on=["region", "week_start"], how="left"
    )
    return combined_table


def assign_flu_season(date):
    year = date.year
    if date.month >= 8:   # Aug–Dec → current year season start
        return year
    else:                 # Jan–Jun → previous year season start
        return year-1


def train_test_split(combined_table, test_season_start):
    """returns (train, test) dfs from combined_table)"""
    train = combined_table[combined_table["season"] < test_season_start].copy()
    test = combined_table[combined_table["season"] >= test_season_start].copy()
    return train.reset_index(drop=True), test.reset_index(drop=True)

def format_predictions_df(predictions_df):
    # Create a mapping dictionary
    lag_label_map = {
        'lag1+lag2+lag3+lag4': '1-4 Weeks Before',
        'lag2+lag3+lag4': '2-4 Weeks Before',
        'lag3+lag4': '3-4 Weeks Before',
        'lag4': '4 Weeks Before'
    }
    predictions_df['Lag Window'] = predictions_df['lag_rule'].map(lag_label_map)

    def clean_features(name: str) -> str:
        return name.split("_region")[0].replace("_", " ").title()

    if 'feature' in predictions_df.columns:
        # Apply the function to the entire column
        predictions_df["feature"] = predictions_df["feature"].apply(clean_features)

    return predictions_df










