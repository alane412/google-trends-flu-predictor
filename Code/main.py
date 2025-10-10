# main.py
from flask import Flask, jsonify
from flask_cors import CORS
import logging

from flu_api import fetch_fluview_hhs, clean_fluview_data
from build_gtrends_flu import main as build_gtrends_flu
from bigquery_utils import upload_to_bigquery
from predict import get_preds


# Flask app
app = Flask(__name__)
CORS(app)  # so Power BI / browser clients can call it
logging.basicConfig(level=logging.INFO)
logger = app.logger

PROJECT_ID = "flu-project-473220" 
DATASET_ID = 'flu_data'       
TABLE_ID = "flu_data"      


@app.get("/")
def root():
    return {"ok": True}

# -------------------------------
# Fluview endpoints
# -------------------------------

@app.get("/flu")
def flu():
    """Return flu data as JSON (no BigQuery)."""
    try:
        df = clean_fluview_data(fetch_fluview_hhs())
        records = df.to_dict(orient="records")
        return jsonify(records)
    except Exception as e:
        logger.exception("Error fetching flu data")
        return jsonify({"error": str(e)}), 500


@app.post("/flu/upload")
def flu_upload():
    """Fetch flu data and upload to BigQuery."""
    try:
        df = clean_fluview_data(fetch_fluview_hhs())
        upload_to_bigquery(df, 
                           project_id=PROJECT_ID,
                           dataset_id=DATASET_ID,
                           table_id=TABLE_ID)
        return jsonify({"status": "success", "rows": len(df)})
    except Exception as e:
        logger.exception("Error uploading flu data to BigQuery")
        return jsonify({"error": str(e)}), 500



# -------------------------------
# Google Trends endpoints
# -------------------------------
PROJECT_ID = "flu-project-473220"
DATASET_ID = "google_trends"
TABLE_ID = "country_trends"

@app.post("/trends/update")
def trends_update():
    """Run Google Trends builder and upload to BigQuery."""
    try:
        df = build_gtrends_flu()  # your main() from build_gtrends_flu.py
        upload_to_bigquery(df, project_id=PROJECT_ID, dataset_id=DATASET_ID, table_id="country_trends")
        return jsonify({"status": "success", "rows": len(df)})
    except Exception as e:
        logger.exception("Error building/uploading trends data")
        return jsonify({"error": str(e)}), 500


@app.get("/trends")
def trends_preview():
    """Run Google Trends builder but just return JSON (no upload)."""
    try:
        df = build_gtrends_flu()
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        logger.exception("Error fetching trends data")
        return jsonify({"error": str(e)}), 500


# -------------------------------
# Prediction endpoints
# -------------------------------
@app.get("/preds")
def preds_preview():
    """Run the Lasso prediction pipeline and return predictions & coefficients as JSON."""
    try:
        predictions_df, coefficients_df = get_preds()

        return jsonify({
            "predictions": predictions_df.to_dict(orient="records"),
            "coefficients": coefficients_df.to_dict(orient="records")
        })
    except Exception as e:
        logger.exception("Error generating predictions")
        return jsonify({"error": str(e)}), 500

@app.post("/preds/update")
def preds_update():
    """Run the Lasso prediction pipeline and upload predictions to BigQuery."""
    try:
        predictions_df, coefficients_df = get_preds()

        # Upload predictions
        upload_to_bigquery(
            predictions_df,
            project_id=PROJECT_ID,
            dataset_id="predictions",
            table_id="predictions_table"
        )

        # Upload coefficients separately
        upload_to_bigquery(
            coefficients_df,
            project_id=PROJECT_ID,
            dataset_id="predictions",
            table_id="coefficients_table"
        )

        return jsonify({
            "status": "success",
            "pred_rows": len(predictions_df),
            "coef_rows": len(coefficients_df)
        })
    except Exception as e:
        logger.exception("Error uploading predictions to BigQuery")
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
