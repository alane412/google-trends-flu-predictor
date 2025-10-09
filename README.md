# Predict the rate of influenza using Google Trends

## Introduction
This project explores whether search trends related to influenza symptoms can help predict rates of influenza infection in the United States.
The dashboard integrates CDC FluView surveillance data (ILI/WILI rates) with Google Trends data for flu-related search terms across HHS regions and seasons.

The goal is to visualize and model how public search behavior aligns with — or potentially anticipates — official surveillance signals of flu activity.

![Dashboard Demo](dashboard_demo.gif)

## Analysis

## Technology Used
- **Python**: Data ingestion, transformation, API development, linear regression model

-  **Flask**: Backend REST API to serve cleaned and merged data

-  **Google BigQuery**: Centralized data warehouse for all raw and processed datasets

-  **Google Cloud Run**: Hosting the Flask API as a serverless application

-  **Google Cloud Scheduler**: Automates weekly updates of FluView and Google Trends data

-  **Power BI**: Interactive dashboard for time-series visualization and regional comparisons
## Data Sources
-  **CDC FluView API**
  - Weekly influenza-like illness (ILI) by region and season
  - https://www.cdc.gov/flu/weekly/fluviewinteractive.htm
- Google Trends (via Pytrends)
  - Weekly search interest for influenza-related terms
  - Pytrends is a Python library that serves as an unofficial API for Google Trends, allowing automated retrieval of serach interest data directly from Google. It simulates user intereactions with the Google Trends web interface, enabling queries for specific keywords, time ranges, and regions, and returns normalized serach-volumne data.