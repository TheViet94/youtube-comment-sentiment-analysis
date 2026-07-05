import unittest

import pandas as pd

from comment_import import find_column, normalize_comment_dataframe


class CommentImportTest(unittest.TestCase):
    def test_find_column_accepts_xquik_text_alias(self):
        df = pd.DataFrame({"text": ["Great episode"], "createdAt": ["2026-01-01"]})
        self.assertEqual(find_column(df, ("comment_text", "text")), "text")

    def test_normalize_comment_dataframe_adds_required_defaults(self):
        df = pd.DataFrame({"text": [" Great episode ", "", None], "createdAt": ["2026-01-01", "", ""]})
        normalized_df = normalize_comment_dataframe(df)
        self.assertEqual(list(normalized_df["comment_text"]), ["Great episode"])
        self.assertEqual(list(normalized_df["video_id"]), ["external"])
        self.assertEqual(list(normalized_df["comment_id"]), ["external-1"])

    def test_normalize_comment_dataframe_rejects_missing_comment_column(self):
        df = pd.DataFrame({"rating": [5]})
        with self.assertRaisesRegex(ValueError, "comment column"):
            normalize_comment_dataframe(df)


if __name__ == "__main__":
    unittest.main()
