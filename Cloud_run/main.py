from flask import Flask, jsonify
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
import pandas as pd
import re
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from comment_import import normalize_comment_dataframe

app = Flask(__name__)

# =========================================================
# ENV CONFIG
# =========================================================
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
PROJECT_ID = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
DATASET_ID = os.environ.get("DATASET_ID", "youtube_comment_analysis")
TABLE_ID = os.environ.get("TABLE_ID", "youtube_comments")

BQ_TABLE = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}" if PROJECT_ID else None

# Có thể override VIDEO_IDS bằng biến môi trường:
# VIDEO_IDS="id1,id2,id3"
DEFAULT_VIDEO_IDS = [
    "3cYi5t9UvzY",
    "C1hKP_HZi5I",
    "A_Hg-07y7Nc",
    "OTfyxNL9KdI",
    "KnOMfSBv7n8"
]

VIDEO_IDS = [
    video_id.strip()
    for video_id in os.environ.get("VIDEO_IDS", ",".join(DEFAULT_VIDEO_IDS)).split(",")
    if video_id.strip()
]

DEFAULT_VIDEO_NAME_MAP = {
    "3cYi5t9UvzY": "Video 1",
    "C1hKP_HZi5I": "Video 2",
    "A_Hg-07y7Nc": "Video 3",
    "OTfyxNL9KdI": "Video 4",
    "KnOMfSBv7n8": "Video 5"
}

# Có thể override VIDEO_NAME_MAP bằng JSON env nếu cần.
# Ví dụ: VIDEO_NAME_MAP='{"abc":"Video 1","xyz":"Video 2"}'
try:
    VIDEO_NAME_MAP = json.loads(os.environ.get("VIDEO_NAME_MAP", "{}")) or DEFAULT_VIDEO_NAME_MAP
except json.JSONDecodeError:
    VIDEO_NAME_MAP = DEFAULT_VIDEO_NAME_MAP

# Nếu muốn test nhanh, đặt MAX_COMMENTS_PER_VIDEO=300.
# Mặc định 0 = crawl toàn bộ comment gốc có thể lấy được.
MAX_COMMENTS_PER_VIDEO = int(os.environ.get("MAX_COMMENTS_PER_VIDEO", "0"))

# Gmail SMTP config for email alert
# Set these in Cloud Run Environment variables:
# GMAIL_USER = Gmail account used to send email
# GMAIL_APP_PASSWORD = Gmail App Password, not normal Gmail password
# TO_EMAIL = email address that receives alerts
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
TO_EMAIL = os.environ.get("TO_EMAIL")

# =========================================================
# SENTIMENT KEYWORDS
# =========================================================
# Gan nhan sentiment theo 3 nhom: khen, che, con lai
praise_keywords = {
    # Khen hay / hấp dẫn
    "hay", "hay qua", "hay quá", "qua hay", "quá hay",
    "hay vai", "hay vãi", "hay thật", "hay that",
    "hay lắm", "hay lam", "hay nha", "hay nhe",
    "rất hay", "rat hay", "video hay", "clip hay",
    "nội dung hay", "noi dung hay",
    "cuốn", "cuon", "cuốn quá", "cuon qua",
    "cuốn thật", "cuon that", "xem cuốn", "xem cuon",
    "đáng xem", "dang xem",

    # Khen đỉnh / chất lượng
    "đỉnh", "dinh", "đỉnh quá", "dinh qua",
    "đỉnh vãi", "dinh vai", "đỉnh thật sự", "dinh that su",
    "xuất sắc", "xuat sac", "tuyệt", "tuyet",
    "tuyệt vời", "tuyet voi", "tuyệt vời quá", "tuyet voi qua",
    "chất", "chat", "chất lượng", "chat luong",
    "xịn", "xin", "xịn quá", "xin qua",
    "làm tốt", "lam tot", "quá tốt", "qua tot",

    # Khen vui / hài
    "vui", "vui quá", "vui qua", "vui ghê", "vui ghe",
    "vui thật", "vui that", "hài", "hai",
    "hài hước", "hai huoc", "hài quá", "hai qua",
    "cười", "cuoi", "cười xỉu", "cuoi xiu",
    "cười đau bụng", "cuoi dau bung",
    "haha", "hahaha", "hehe", "kkk",

    # Khen người / nhân vật
    "đáng yêu", "dang yeu", "dễ thương", "de thuong",
    "dễ thương quá", "de thuong qua",
    "cute", "cute quá", "cute qua",
    "giỏi", "gioi", "đẹp", "dep",
    "thương", "thuong", "thương quá", "thuong qua",

    # Thích / yêu thích / hâm mộ
    "thích", "thich", "yêu", "yeu", "iu",
    "mê", "me", "hâm mộ", "ham mo",
    "idol", "fan", "fan cứng", "fan cung",

    # Cảm ơn / biết ơn
    "cảm ơn", "cam on", "cám ơn", "cam ơn",
    "thanks", "thank", "thank you", "tks", "thx",
    "cảm ơn anh", "cam on anh",
    "cảm ơn chị", "cam on chi",
    "cảm ơn team", "cam on team",
    "cảm ơn mọi người", "cam on moi nguoi",

    # Ủng hộ / theo dõi
    "ủng hộ", "ung ho",
    "luôn ủng hộ", "luon ung ho",
    "ủng hộ anh", "ung ho anh",
    "ủng hộ team", "ung ho team",
    "theo dõi", "theo doi",
    "sub rồi", "sub roi",
    "đăng ký rồi", "dang ky roi",

    # Động viên / chúc mừng
    "chúc mừng", "chuc mung",
    "chúc anh", "chuc anh",
    "chúc team", "chuc team",
    "cố lên", "co len",
    "cố gắng", "co gang",
    "cố gắng lên", "co gang len",
    "thành công", "thanh cong",
    "mạnh khỏe", "manh khoe",
    "may mắn", "may man",

    # Mong chờ / hóng nội dung mới
    "hóng", "hong",
    "hóng tập sau", "hong tap sau",
    "mong ra tập mới", "mong ra tap moi",
    "mong anh làm tiếp", "mong anh lam tiep",
    "ra tiếp đi", "ra tiep di",
    "phần sau", "phan sau",
    "tập sau", "tap sau",
    "làm tiếp", "lam tiep",

    # Từ cảm xúc tích cực ngắn
    "ok", "oke", "ổn", "rất ổn", "rat on",
    "ngon", "tuyệt cú mèo", "tuyet cu meo"
}
criticism_keywords = {
    # Chê dở / chán / tệ
    "dở", "dở quá", "do qua",
    "tệ", "te", "tệ quá", "te qua",
    "chán", "chan", "chán quá", "chan qua",
    "nhạt", "nhat", "nhạt quá", "nhat qua",
    "không hay", "khong hay", "ko hay", "k hay",
    "không còn hay", "khong con hay",

    # Chê nhảm / xàm / vô nghĩa
    "nhảm", "nham", "xàm", "xam",
    "xàm quá", "xam qua",
    "tào lao", "tao lao",
    "vớ vẩn", "vo van",
    "vô lý", "vo ly",
    "rác", "rac",

    # Không thích / thất vọng
    "không thích", "khong thich", "ko thích", "ko thich", "k thích", "k thich",
    "ghét", "ghet",
    "thất vọng", "that vong",
    "không vui", "khong vui", "ko vui", "k vui",
    "không ổn", "khong on", "ko ổn", "ko on",

    # Chê chất lượng / nội dung
    "kém", "kem",
    "xấu", "xau",
    "nội dung chán", "noi dung chan",
    "nội dung nhảm", "noi dung nham",
    "khó hiểu", "kho hieu",
    "không đáng xem", "khong dang xem",
    "phí thời gian", "phi thoi gian",

    # Phàn nàn cách làm video
    "câu view", "cau view",
    "giả tạo", "gia tao",
    "làm màu", "lam mau",
    "diễn", "dien",
    "phản cảm", "phan cam",
    "lố", "lố quá", "lo qua",
    "vô duyên", "vo duyen",
    "nói nhiều", "noi nhieu",
    "ồn ào", "on ao",
    "la hét", "la het",
    "bớt lại", "bot lai",

    # Bực tức / khó chịu
    "cay", "tức", "tuc",
    "bực", "buc",
    "khó chịu", "kho chiu",
    "ức chế", "uc che",
    "xem mà tức", "coi mà tức",
    "coi mà bực", "xem mà bực",

    # Công bằng / lừa / toxic
    "bất công", "bat cong",
    "không công bằng", "khong cong bang",
    "thiên vị", "thien vi",
    "lừa", "lua",
    "toxic",
    "spam"
}
# =========================================================
# BIGQUERY SCHEMA
# =========================================================
BQ_SCHEMA = [
    bigquery.SchemaField("video_id", "STRING"),
    bigquery.SchemaField("video_name", "STRING"),
    bigquery.SchemaField("comment_id", "STRING"),
    bigquery.SchemaField("author", "STRING"),
    bigquery.SchemaField("comment_text", "STRING"),
    bigquery.SchemaField("clean_text", "STRING"),
    bigquery.SchemaField("sentiment", "STRING"),
    bigquery.SchemaField("sentiment_vi", "STRING"),
    bigquery.SchemaField("like_count", "INTEGER"),
    bigquery.SchemaField("reply_count", "INTEGER"),
    bigquery.SchemaField("published_at", "TIMESTAMP"),
    bigquery.SchemaField("updated_at", "TIMESTAMP"),
    bigquery.SchemaField("crawl_time", "TIMESTAMP"),
    bigquery.SchemaField("date", "DATE"),
    bigquery.SchemaField("year", "INTEGER"),
    bigquery.SchemaField("month", "INTEGER"),
    bigquery.SchemaField("day", "INTEGER"),
    bigquery.SchemaField("hour", "INTEGER"),
    bigquery.SchemaField("comment_length", "INTEGER"),
    bigquery.SchemaField("word_count", "INTEGER"),
]

OUTPUT_COLUMNS = [
    "video_id",
    "video_name",
    "comment_id",
    "author",
    "comment_text",
    "clean_text",
    "sentiment",
    "sentiment_vi",
    "like_count",
    "reply_count",
    "published_at",
    "updated_at",
    "crawl_time",
    "date",
    "year",
    "month",
    "day",
    "hour",
    "comment_length",
    "word_count",
]

# =========================================================
# DATA PROCESSING
# =========================================================
def clean_comment(text):
    if pd.isna(text):
        return ""

    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#", " ", text)
    text = re.sub(r"[^a-zA-ZÀ-ỹ0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def count_keyword_matches(text, keywords):
    """
    Dem tu khoa sentiment an toan hon:
    - Neu keyword la cum tu: match dung cum tu trong comment.
    - Neu keyword la 1 tu: chi match khi no la token rieng, tranh match sai trong tu khac.
    """
    text = str(text).lower()
    padded_text = f" {text} "
    tokens = set(text.split())
    score = 0

    for keyword in keywords:
        keyword = str(keyword).lower().strip()

        if not keyword:
            continue

        if " " in keyword:
            if f" {keyword} " in padded_text:
                score += 1
        else:
            if keyword in tokens:
                score += 1

    return score


def label_sentiment(text):
    text = str(text).lower()

    praise_score = count_keyword_matches(text, praise_keywords)
    criticism_score = count_keyword_matches(text, criticism_keywords)

    if praise_score > criticism_score:
        return "positive"
    if criticism_score > praise_score:
        return "negative"
    return "neutral"


def get_sentiment_vi(sentiment):
    mapping = {
        "positive": "Tích cực",
        "negative": "Tiêu cực",
        "neutral": "Trung bình",
    }
    return mapping.get(sentiment, "Trung bình")


def crawl_comments_from_video(youtube, video_id):
    comments = []
    next_page_token = None

    while True:
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token,
                textFormat="plainText",
                order="time",
            )
            response = request.execute()

        except HttpError as error:
            print(f"Error crawling video {video_id}: {error}")
            break

        for item in response.get("items", []):
            top_comment = item["snippet"]["topLevelComment"]
            snippet = top_comment["snippet"]

            comments.append(
                {
                    "video_id": video_id,
                    "video_name": VIDEO_NAME_MAP.get(video_id, "Unknown Video"),
                    "comment_id": top_comment.get("id"),
                    "author": snippet.get("authorDisplayName"),
                    "comment_text": snippet.get("textDisplay"),
                    "like_count": snippet.get("likeCount", 0),
                    "published_at": snippet.get("publishedAt"),
                    "updated_at": snippet.get("updatedAt"),
                    "reply_count": item["snippet"].get("totalReplyCount", 0),
                }
            )

            if MAX_COMMENTS_PER_VIDEO and len(comments) >= MAX_COMMENTS_PER_VIDEO:
                return comments

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

    return comments


def transform_comments(raw_comments):
    df = pd.DataFrame(raw_comments)

    if df.empty:
        return df

    df = normalize_comment_dataframe(df)
    df = df.dropna(subset=["comment_text"])
    df["author"] = df["author"].fillna("Unknown")
    df = df.drop_duplicates(subset=["video_id", "comment_id"])

    df["clean_text"] = df["comment_text"].apply(clean_comment)
    df = df[df["clean_text"] != ""].copy()

    df["sentiment"] = df["clean_text"].apply(label_sentiment)
    df["sentiment_vi"] = df["sentiment"].apply(get_sentiment_vi)

    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce", utc=True)
    df["crawl_time"] = datetime.now(timezone.utc)

    df["date"] = df["published_at"].dt.date
    df["year"] = df["published_at"].dt.year.astype("Int64")
    df["month"] = df["published_at"].dt.month.astype("Int64")
    df["day"] = df["published_at"].dt.day.astype("Int64")
    df["hour"] = df["published_at"].dt.hour.astype("Int64")

    df["comment_length"] = df["clean_text"].astype(str).str.len()
    df["word_count"] = df["clean_text"].astype(str).str.split().str.len()

    df["like_count"] = pd.to_numeric(df["like_count"], errors="coerce").fillna(0).astype(int)
    df["reply_count"] = pd.to_numeric(df["reply_count"], errors="coerce").fillna(0).astype(int)

    return df[OUTPUT_COLUMNS]



# =========================================================
# EMAIL ALERT
# =========================================================
def build_sample_comments_text(df, limit=5):
    """
    Build a short plain-text preview of newly crawled comments for the alert email.
    """
    if df is None or df.empty:
        return "Không có bình luận mới."

    lines = []

    for index, row in df.head(limit).reset_index(drop=True).iterrows():
        video_name = row.get("video_name", "Unknown Video")
        sentiment = row.get("sentiment_vi", row.get("sentiment", "unknown"))
        like_count = row.get("like_count", 0)
        comment_text = str(row.get("comment_text", "")).replace("\n", " ").strip()

        if len(comment_text) > 250:
            comment_text = comment_text[:250] + "..."

        lines.append(
            f"{index + 1}. [{video_name}] [{sentiment}] [likes: {like_count}] {comment_text}"
        )

    return "\n".join(lines)


def send_email_alert(new_comments_count, sample_comments):
    """
    Send an email alert when new YouTube comments are inserted into BigQuery.
    This function uses Gmail SMTP with a Gmail App Password.
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not TO_EMAIL:
        print("Email alert skipped: missing GMAIL_USER, GMAIL_APP_PASSWORD, or TO_EMAIL")
        return False

    subject = f"YouTube Alert - Có {new_comments_count} bình luận mới"

    body = f"""
Có {new_comments_count} bình luận mới được ghi nhận.

Một số bình luận mới:
{sample_comments}

Dữ liệu đã được cập nhật vào BigQuery.
Bạn có thể mở Power BI Desktop và bấm Refresh để xem dashboard mới nhất.
"""

    message = MIMEMultipart()
    message["From"] = GMAIL_USER
    message["To"] = TO_EMAIL
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, TO_EMAIL, message.as_string())

        print("Email alert sent successfully")
        return True

    except Exception as error:
        # Do not fail the whole ETL if email sending fails.
        print(f"Email alert failed: {error}")
        return False


# =========================================================
# BIGQUERY
# =========================================================
def get_bigquery_client():
    return bigquery.Client(project=PROJECT_ID)


def ensure_table_exists():
    client = get_bigquery_client()

    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        dataset_ref.location = os.environ.get("BQ_LOCATION", "asia-southeast1")
        client.create_dataset(dataset_ref)
        print(f"Created dataset: {PROJECT_ID}.{DATASET_ID}")

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    try:
        client.get_table(table_ref)
    except NotFound:
        table = bigquery.Table(table_ref, schema=BQ_SCHEMA)
        client.create_table(table)
        print(f"Created table: {table_ref}")


def get_existing_comment_ids():
    client = get_bigquery_client()
    query = f"SELECT DISTINCT comment_id FROM `{BQ_TABLE}`"

    try:
        result = client.query(query).result()
        return {row.comment_id for row in result}
    except Exception as error:
        print(f"Could not load existing comment IDs: {error}")
        return set()


def upload_to_bigquery(df):
    client = get_bigquery_client()

    job_config = bigquery.LoadJobConfig(
        schema=BQ_SCHEMA,
        write_disposition="WRITE_APPEND",
    )

    job = client.load_table_from_dataframe(
        df,
        BQ_TABLE,
        job_config=job_config,
    )

    job.result()
    return len(df)


# =========================================================
# CLOUD RUN ROUTES
# =========================================================
@app.route("/", methods=["GET", "POST"])
def run_etl():
    if not YOUTUBE_API_KEY:
        return jsonify({"error": "Missing YOUTUBE_API_KEY"}), 500

    if not PROJECT_ID:
        return jsonify({"error": "Missing PROJECT_ID"}), 500

    ensure_table_exists()

    youtube = build(
        serviceName="youtube",
        version="v3",
        developerKey=YOUTUBE_API_KEY,
    )

    all_comments = []

    for video_id in VIDEO_IDS:
        print(f"Crawling video: {video_id}")
        video_comments = crawl_comments_from_video(youtube, video_id)
        print(f"Video {video_id}: crawled {len(video_comments)} comments")
        all_comments.extend(video_comments)

    df = transform_comments(all_comments)

    if df.empty:
        return jsonify({"message": "No valid comments crawled"}), 200

    existing_ids = get_existing_comment_ids()
    df_new = df[~df["comment_id"].isin(existing_ids)].copy()

    if df_new.empty:
        return jsonify(
            {
                "message": "No new comments to upload",
                "crawled_rows": len(df),
                "uploaded_rows": 0,
                "table": BQ_TABLE,
            }
        ), 200

    uploaded_rows = upload_to_bigquery(df_new)

    sample_comments = build_sample_comments_text(df_new, limit=5)
    email_sent = send_email_alert(
        new_comments_count=uploaded_rows,
        sample_comments=sample_comments,
    )

    return jsonify(
        {
            "message": "ETL completed",
            "crawled_rows": len(df),
            "uploaded_rows": uploaded_rows,
            "email_sent": email_sent,
            "table": BQ_TABLE,
        }
    ), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200
