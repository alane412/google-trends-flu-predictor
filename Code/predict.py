import numpy as np
import pandas as pd

import predict_utils
from bigquery_utils import load_view_from_bigquery
from predict_utils import compute_averages_per_region, assign_flu_season, train_test_split, format_predictions_df
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

# ------------------------------------
# Load in and format combined table
# ------------------------------------

# load in combined table from BigQuery
combined_table = load_view_from_bigquery('flu-project-473220',
                                         'combined_data',
                                         'combined_table')

# compute averages per region (per date) as new cols
trend_cols = ["flu", "fever", "cough", "flu_symptoms", "sore_throat"]
combined_table = compute_averages_per_region(combined_table, trend_cols)
# drop state-level trend and 'wili' cols
combined_table = combined_table.drop(columns=trend_cols + ['wili'])
# drop duplicate cols
combined_table.drop_duplicates(inplace=True)

# assign flu season to each row
## Aug–Dec → current year season start
## # Aug–Dec → current year season start
combined_table['season'] = combined_table['week_start'].apply(assign_flu_season)



# -------------------------------------------------------------------
#  Create lagged predictors (Google Trends terms 1, 2, 3, 4 weeks before)
# -------------------------------------------------------------------
lags = [1, 2, 3, 4]

predictor_vars = [
    "flu_region_avg", "fever_region_avg", "cough_region_avg",
    "flu_symptoms_region_avg", "sore_throat_region_avg"
]

for lag in lags:
    for var in predictor_vars:
        combined_table[f"{var}_lag{lag}"] = combined_table.groupby("region")[var].shift(lag)

# Drop rows with any NaN (due to lagging)
combined_table = combined_table.dropna()
def get_combined_table():
    return combined_table


# -------------------------------------------------------------------
#  Fit linear regression model
# -------------------------------------------------------------------

target_col = "wili_region_avg"
all_lag_cols = [c for c in combined_table.columns if "_lag" in c]

# identify available lag numbers
lags_available = sorted({int(c.split("lag")[-1]) for c in all_lag_cols})

min_season = combined_table["season"].min() + 1
max_season = combined_table["season"].max()
cutoff_seasons = range(min_season, max_season + 1)

predictions_list = []
coef_list = []

# --------------------------------------------
# loop over cutoff seasons
# --------------------------------------------
for cutoff in cutoff_seasons:
    train, test = train_test_split(combined_table, cutoff)

    for max_lag_to_use in lags_available[::-1]:       # e.g., lag4 → lag4+3 → ...
        lags_in_rule = [l for l in lags_available if l >= max_lag_to_use]

        feature_cols = [
            c for c in all_lag_cols
            if int(c.split("lag")[-1]) in lags_in_rule
        ]

        # fit Linear Regression
        linreg = LinearRegression()
        linreg.fit(train[feature_cols], train[target_col])

        preds = linreg.predict(test[feature_cols])
        r2    = r2_score(test[target_col], preds)

        # create row-level errors
        abs_error = np.abs(preds - test[target_col].values)
        sq_error  = (preds - test[target_col].values) ** 2

        lag_rule_label = "+".join([f"lag{l}" for l in sorted(lags_in_rule)])

        # store predictions (row-level)
        df_preds = pd.DataFrame({
            "week_start":    test["week_start"].values,
            "region":        test["region"].values,
            "season_cutoff": cutoff,
            "lag_rule":      lag_rule_label,
            "actual":        test[target_col].values,
            "predicted":     preds,
            "abs_error":     abs_error,
            "sq_error":      sq_error,
            "r2_model":      r2       # same for all rows in this model
        })
        predictions_list.append(df_preds)

        # store coefficients (model-level)
        df_coef = pd.DataFrame({
            "season_cutoff": cutoff,
            "lag_rule":      lag_rule_label,
            "feature":       feature_cols,
            "coef":          linreg.coef_
        })
        coef_list.append(df_coef)

# --------------------------------------------
# combine results into final DataFrames
# --------------------------------------------
predictions_df  = pd.concat(predictions_list, ignore_index=True)
coefficients_df = pd.concat(coef_list, ignore_index=True)

# sort by model + coefficient value (keeps directionality)
coefficients_df = coefficients_df.sort_values(
    by=["season_cutoff", "lag_rule", "coef"],
    ascending=[True, True, False]
)

def get_preds():
    return format_predictions_df(predictions_df), format_predictions_df(coefficients_df)

