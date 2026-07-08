from pathlib import Path
import tempfile
import unittest

from datapipeline import run_pipeline
from datapipeline.pipeline import write_reports


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw_orders.csv"


class PipelineTests(unittest.TestCase):
    def test_pipeline_creates_summary(self):
        result = run_pipeline(DATA_PATH)

        self.assertEqual(result.summary["rows_processed"], 14)
        self.assertEqual(result.summary["clean_records"], 8)
        self.assertEqual(result.summary["rejected_records"], 6)
        self.assertEqual(result.summary["pipeline_score"], 46)

    def test_pipeline_standardizes_clean_records(self):
        result = run_pipeline(DATA_PATH)
        first_row = result.cleaned_rows[0]

        self.assertEqual(first_row["customer_id"], "C-224")
        self.assertEqual(first_row["region"], "Northeast")
        self.assertEqual(first_row["status"], "Delivered")
        self.assertEqual(first_row["revenue"], "258.00")

    def test_reports_are_written(self):
        result = run_pipeline(DATA_PATH)

        with tempfile.TemporaryDirectory() as tmp_dir:
            write_reports(result, Path(tmp_dir))

            self.assertTrue((Path(tmp_dir) / "clean_orders.csv").exists())
            self.assertTrue((Path(tmp_dir) / "pipeline_issues.csv").exists())
            self.assertTrue((Path(tmp_dir) / "pipeline_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
