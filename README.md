# YouTube Comment Sentiment Analysis Pipeline

## Overview

This project builds an automated data pipeline for YouTube comment sentiment analysis.  
It collects comments from YouTube videos using the YouTube Data API, processes and labels comment sentiment with Python, stores the cleaned data in Google BigQuery, visualizes insights in Power BI, and sends Gmail alerts when new comments are detected.

The project is designed as an end-to-end data analytics workflow, combining data collection, cloud automation, data warehousing, dashboard reporting, and notification alerts.

---

## Project Architecture

```text
Cloud Scheduler
→ Cloud Run
→ YouTube Data API
→ Python ETL
→ Google BigQuery
→ Power BI Dashboard
→ Gmail Email Alert

```
## Features
- Collect YouTube comments from multiple videos.
- Clean and transform raw comment text using Python.
- Classify comments into Positive, Negative, and Neutral sentiment.
- Store processed comment data in Google BigQuery.
- Prevent duplicate records by checking comment_id.
- Automate the ETL process using Google Cloud Run and Cloud Scheduler.
- Send Gmail alerts when new comments are detected.
- Build an interactive Power BI dashboard for sentiment and engagement analysis.
  
## Repository Structure
```text
youtube-comment-sentiment-analysis/
│
├── Cloud_run/
│   ├── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .dockerignore
│
├── notebooks/
│   └── youtube_comment_analysis.ipynb
│
├── dashboard/
│   └── youtube_comment_sentiment_dashboard.pbix
│
├── assets/
│   └── dashboard.png
│
├── .env.example
├── .gitignore
├── LICENSE
└── README.md

```
  
## Tools & Technologies
| Category        | Tools                             |
| --------------- | --------------------------------- |
| Programming     | Python                            |
| Data Processing | Pandas                            |
| API             | YouTube Data API                  |
| Cloud Platform  | Google Cloud Run, Cloud Scheduler |
| Data Warehouse  | Google BigQuery                   |
| Dashboard       | Power BI                          |
| Notification    | Gmail SMTP                        |
| Deployment      | Docker                            |
| Version Control | Git, GitHub                       |
## Dataset
The dataset is collected from YouTube comments using the YouTube Data API.

Main fields include:
| Column           | Description                                  |
| ---------------- | -------------------------------------------- |
| `video_id`       | YouTube video ID                             |
| `video_name`     | Custom video name                            |
| `comment_id`     | Unique comment ID                            |
| `author`         | Comment author                               |
| `comment_text`   | Original comment text                        |
| `clean_text`     | Cleaned comment text                         |
| `sentiment`      | Sentiment label: positive, negative, neutral |
| `sentiment_vi`   | Vietnamese sentiment label                   |
| `like_count`     | Number of likes on the comment               |
| `reply_count`    | Number of replies                            |
| `published_at`   | Comment published time                       |
| `crawl_time`     | Time when the comment was collected          |
| `date`           | Comment date                                 |
| `hour`           | Comment hour                                 |
| `comment_length` | Length of cleaned comment                    |
| `word_count`     | Number of words in the comment               |

The transform step also accepts offline comment rows with `text`, `comment`,
`message`, `feedback`, or `review` columns. This supports Xquik export CSVs and
other comment datasets while preserving the BigQuery output schema.

## Data Pipeline
- Cloud Scheduler triggers the Cloud Run service automatically.
- Cloud Run executes the Python ETL script.
- The script collects comments from selected YouTube videos.
- Raw comments are cleaned and transformed.
- Sentiment labels are assigned using keyword-based rules.
- Existing comment IDs are checked in BigQuery.
- Only new comments are inserted into BigQuery.
- If new comments are detected, an email alert is sent.
- Power BI connects to BigQuery and refreshes the latest data.
## Power BI Dashboard
The Power BI dashboard provides an overview of YouTube comment sentiment and engagement.

Main dashboard components:
- Total comments
- Positive comments
- Negative comments
- Neutral comments
- Sentiment distribution
- Comments by video
- Sentiment by video
- Comments by hour
- Top comments by likes
## Email Alert System
The system sends an email notification when new comments are detected.

The email includes:

- Number of new comments
- Video name
- Sentiment label
- Like count
  

## How to Run locally
1. clone the repository
```
git clone https://github.com/TheViet94/youtube-comment-sentiment-analysis.git
cd youtube-comment-sentiment-analysis

```
2. Install dependencies
```
pip install -r Cloud_run/requirements.txt

```
3. Set environment variables
Create a .env file based on .env.example.
required variables:
```
YOUTUBE_API_KEY=YOUR_YOUTUBE_API_KEY
PROJECT_ID=YOUR_GCP_PROJECT_ID
DATASET_ID=youtube_comment_analysis
TABLE_ID=youtube_comments
BQ_LOCATION=asia-southeast1

GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=YOUR_GMAIL_APP_PASSWORD
TO_EMAIL=receiver_email@gmail.com

```
## Cloud Deloyment
The ETL service is deployed on Google Cloud Run.

Example deployment command:
```
gcloud run deploy youtube-comment-etl \
  --source Cloud_run \
  --region asia-southeast1 \
  --allow-unauthenticated

```
Cloud Scheduler is used to trigger the Cloud Run endpoint automatically.

## Results & Insights

Key insights from the dashboard:

Neutral comments account for the largest proportion.
Positive comments are significantly higher than negative comments.
Negative comments make up a small percentage of total comments.
Some videos generate more engagement than others.
Comment activity is concentrated during specific hours of the day.
Top liked comments help identify the most noticeable audience reactions.

## Future Improvements
Use a machine learning or transformer-based NLP model for more accurate sentiment classification.
Add topic modeling to identify common themes in negative comments.
Publish the dashboard to Power BI Service for scheduled refresh.
Add alert rules for high negative comment volume.
Store email alert logs in BigQuery.
Add video metadata such as title, views, likes, and publish date.

## Author
Developed by TheViet94.
