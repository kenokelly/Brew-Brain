"""
Tests for Phase 5 Pi Stability changes:
- parse_tilt_csv returns list of dicts (not a DataFrame)
- check_temp_stability works with list-of-dicts input
- get_page_content returns None on 403 (no Playwright fallback)
- compare_recipe_prices_async returns a job ID and populates result
"""

import unittest
import io
import time
from unittest.mock import patch, MagicMock


class TestParseTiltCSV(unittest.TestCase):
    """Tests for the stdlib-based CSV parser (replaces Pandas)."""

    def test_returns_list_of_dicts(self):
        from app.services.alerts import parse_tilt_csv

        csv_data = "Timepoint,Temp,SG\n1,20.1,1.050\n2,20.2,1.048\n3,20.0,1.045\n"
        result = parse_tilt_csv(csv_data)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], dict)
        self.assertIn("Temp", result[0])
        self.assertAlmostEqual(result[0]["Temp"], 20.1)

    def test_handles_bytes_input(self):
        from app.services.alerts import parse_tilt_csv

        csv_bytes = b"Time,Temp,SG\n1,19.5,1.055\n"
        result = parse_tilt_csv(csv_bytes)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["Temp"], 19.5)

    def test_handles_file_stream(self):
        from app.services.alerts import parse_tilt_csv

        csv_data = "TimeCol,Temp,SG\n1,21.0,1.040\n2,21.1,1.038\n"
        stream = io.StringIO(csv_data)
        result = parse_tilt_csv(stream)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_returns_none_on_empty(self):
        from app.services.alerts import parse_tilt_csv

        result = parse_tilt_csv("")
        self.assertIsNone(result)

    def test_numeric_conversion(self):
        from app.services.alerts import parse_tilt_csv

        csv_data = "label,Temp,SG\nreading1,20.5,1.050\n"
        result = parse_tilt_csv(csv_data)

        # Numeric fields should be floats
        self.assertIsInstance(result[0]["Temp"], float)
        self.assertIsInstance(result[0]["SG"], float)
        # Non-numeric field stays as string
        self.assertIsInstance(result[0]["label"], str)


class TestCheckTempStability(unittest.TestCase):
    """Tests for the list-of-dicts stability checker."""

    def test_stable_temps(self):
        from app.services.alerts import check_temp_stability

        readings = [{"temp": 20.0 + i * 0.01} for i in range(25)]
        result = check_temp_stability(readings, target_temp=20.0, threshold=1.0, is_list=True)

        self.assertEqual(result["status"], "stable")
        self.assertLessEqual(result["max_deviation"], 1.0)

    def test_unstable_temps(self):
        from app.services.alerts import check_temp_stability

        readings = [{"temp": 18.0}, {"temp": 22.0}, {"temp": 17.0}, {"temp": 23.0}]
        result = check_temp_stability(readings, target_temp=20.0, threshold=1.0, is_list=True)

        self.assertEqual(result["status"], "unstable")
        self.assertGreater(result["max_deviation"], 1.0)

    def test_empty_data(self):
        from app.services.alerts import check_temp_stability

        result = check_temp_stability([], target_temp=20.0, is_list=True)
        self.assertEqual(result["status"], "error")

    def test_missing_temp_column(self):
        from app.services.alerts import check_temp_stability

        readings = [{"gravity": 1.050}, {"gravity": 1.048}]
        result = check_temp_stability(readings, target_temp=20.0, is_list=True)
        self.assertEqual(result["status"], "error")
        self.assertIn("Temperature column not found", result["message"])

    def test_from_csv_stream(self):
        from app.services.alerts import check_temp_stability

        csv_data = "Time,Temp,SG\n" + "\n".join(
            f"{i},{20.0 + i * 0.01},{1.050 - i * 0.001}" for i in range(25)
        )
        result = check_temp_stability(csv_data, target_temp=20.0, threshold=1.0, is_list=False)

        self.assertEqual(result["status"], "stable")


class TestGetPageContentNoPlaywright(unittest.TestCase):
    """Verifies Playwright fallback is removed."""

    @patch("app.services.sourcing.requests.get")
    def test_returns_none_on_403(self, mock_get):
        from app.services.sourcing import get_page_content
        import requests as req

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        http_err = req.exceptions.HTTPError("403 Forbidden", response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_err
        mock_get.return_value = mock_resp

        result = get_page_content("https://example.com", retries=0)
        self.assertIsNone(result)

    @patch("app.services.sourcing.requests.get")
    def test_success_returns_html(self, mock_get):
        from app.services.sourcing import get_page_content

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html>OK</html>"
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = get_page_content("https://example.com", retries=0)
        self.assertEqual(result, "<html>OK</html>")


class TestAsyncPriceComparison(unittest.TestCase):
    """Tests for the async job wrapper."""

    @patch("app.services.sourcing.compare_recipe_prices")
    def test_async_returns_job_id(self, mock_compare):
        from app.services.sourcing import compare_recipe_prices_async, get_job_status

        mock_compare.return_value = {"total_tmm": 10.0, "total_geb": 12.0}

        job_id = compare_recipe_prices_async(
            recipe_details={"hops": [], "fermentables": [], "yeasts": []}
        )

        self.assertIsInstance(job_id, str)
        self.assertEqual(len(job_id), 36)  # UUID format

        # Wait for thread to complete
        for _ in range(20):
            status = get_job_status(job_id)
            if status["status"] == "done":
                break
            time.sleep(0.1)

        status = get_job_status(job_id)
        self.assertEqual(status["status"], "done")
        self.assertEqual(status["result"]["total_tmm"], 10.0)

    @patch("app.services.sourcing.compare_recipe_prices")
    def test_async_handles_error(self, mock_compare):
        from app.services.sourcing import compare_recipe_prices_async, get_job_status

        mock_compare.side_effect = RuntimeError("API down")

        job_id = compare_recipe_prices_async(
            recipe_details={"hops": [], "fermentables": [], "yeasts": []}
        )

        for _ in range(20):
            status = get_job_status(job_id)
            if status["status"] in ("done", "error"):
                break
            time.sleep(0.1)

        status = get_job_status(job_id)
        self.assertEqual(status["status"], "error")
        self.assertIn("API down", status["error"])

    def test_nonexistent_job(self):
        from app.services.sourcing import get_job_status

        result = get_job_status("nonexistent-uuid")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
