import sys
import unittest
from unittest.mock import patch
import pytest

# Mock requests since we don't have internet access for pip install
class MockRequests:
    class RequestException(Exception): pass
    class Timeout(Exception): pass
    def get(self, *args, **kwargs): pass

sys.modules['requests'] = MockRequests()

from app.ml.scraper import init_db

def test_init_db_valid_columns():
    # Should run without raising any exceptions
    init_db()

@patch('app.ml.scraper.MIGRATION_COLUMNS', [("invalid_col", "TEXT")])
def test_init_db_invalid_column():
    with pytest.raises(ValueError, match="Invalid column or type: invalid_col TEXT"):
        init_db()

@patch('app.ml.scraper.MIGRATION_COLUMNS', [("grain_bill", "INTEGER")])
def test_init_db_invalid_type():
    with pytest.raises(ValueError, match="Invalid column or type: grain_bill INTEGER"):
        init_db()
