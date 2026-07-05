import pandas as pd


COMMENT_COLUMN_ALIASES = (
    "comment_text",
    "text",
    "comment",
    "comments",
    "message",
    "feedback",
    "review",
)

CREATED_AT_ALIASES = (
    "published_at",
    "publishedat",
    "created_at",
    "createdat",
    "date",
)


def normalize_column_name(column_name):
    return str(column_name).strip().lower().replace(" ", "_").replace("-", "_")


def find_column(df, aliases):
    normalized_columns = [normalize_column_name(column) for column in df.columns]
    for alias in aliases:
        if alias in normalized_columns:
            return df.columns[normalized_columns.index(alias)]
    return None


def normalize_comment_dataframe(df):
    comment_column = find_column(df, COMMENT_COLUMN_ALIASES)
    if comment_column is None:
        aliases = ", ".join(COMMENT_COLUMN_ALIASES)
        raise ValueError(f"Input rows must include one comment column: {aliases}.")

    normalized_df = df.copy()
    normalized_df = normalized_df.dropna(subset=[comment_column])
    normalized_df[comment_column] = normalized_df[comment_column].astype(str).str.strip()
    normalized_df = normalized_df[normalized_df[comment_column] != ""].copy()

    if normalized_df.empty:
        raise ValueError("Input rows do not contain any valid comment text.")

    normalized_df["comment_text"] = normalized_df[comment_column]

    created_at_column = find_column(normalized_df, CREATED_AT_ALIASES)
    if created_at_column is not None:
        normalized_df["published_at"] = normalized_df[created_at_column]

    if "video_id" not in normalized_df:
        normalized_df["video_id"] = "external"
    if "video_name" not in normalized_df:
        normalized_df["video_name"] = "External Comments"
    if "comment_id" not in normalized_df:
        normalized_df["comment_id"] = [f"external-{index + 1}" for index in range(len(normalized_df))]
    if "author" not in normalized_df:
        normalized_df["author"] = "Unknown"
    if "like_count" not in normalized_df:
        normalized_df["like_count"] = 0
    if "reply_count" not in normalized_df:
        normalized_df["reply_count"] = 0
    if "published_at" not in normalized_df:
        normalized_df["published_at"] = pd.NaT
    if "updated_at" not in normalized_df:
        normalized_df["updated_at"] = normalized_df["published_at"]

    return normalized_df
