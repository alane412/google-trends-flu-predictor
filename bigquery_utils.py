# bigquery_utils.py
"""
Utility functions for uploading dataframes to Google BigQuery.
"""


from google.cloud import bigquery
import pandas as pd

def upload_to_bigquery(df, project_id, dataset_id, table_id):
    """
    Upload a pandas DataFrame to BigQuery, replacing the table contents.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to upload.
    project_id : str
        GCP project ID.
    dataset_id : str
        BigQuery dataset ID.
    table_id : str
        BigQuery table name.
    """
    client = bigquery.Client(project=project_id)

    # Build full table reference: project.dataset.table
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE  # always replace
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # Wait for completion

    return f"Replaced {table_ref} with {len(df)} rows"


def load_view_from_bigquery(project_id: str, dataset_id: str, view_id: str):
    """
    Loads a BigQuery view as a pandas DataFrame.

    Parameters
    ----------
    project_id : str
        GCP project ID.
    dataset_id : str
        BigQuery dataset ID.
    view_id : str
        Name of the BigQuery view.
    """
    client = bigquery.Client(project=project_id)
    full_id = f"{project_id}.{dataset_id}.{view_id}"

    # Use SQL query to pull all rows from the view
    query = f"SELECT * FROM `{full_id}`"
    return client.query(query).to_dataframe()





