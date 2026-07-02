import unittest
from unittest.mock import patch, MagicMock
import subprocess
from pathlib import Path
import sys

# Ensure parent directory is in python path to allow importing tools
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.run_tests.tool import run_tests, SANDBOX_DIR


class TestRunTests(unittest.TestCase):
    def setUp(self):
        # Create sandbox and a dummy test file
        self.sandbox = SANDBOX_DIR
        self.sandbox.mkdir(exist_ok=True)
        self.test_file = self.sandbox / "test_dummy.py"
        self.test_file.write_text("def test_dummy(): pass", encoding="utf-8")

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()

    @patch("subprocess.run")
    def test_all_tests_pass(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = """
============================= test session starts =============================
collected 3 items

test_dummy.py::test_one PASSED                                        [ 33%]
test_dummy.py::test_two PASSED                                        [ 66%]
test_dummy.py::test_three PASSED                                       [100%]

============================== 3 passed in 0.05s ===============================
"""
        mock_proc.stderr = ""
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        result = run_tests("test_dummy.py")
        self.assertEqual(result["passed"], 3)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["summary"], "3 passed")
        self.assertEqual(result["failures"], [])
        self.assertFalse(result["timed_out"])
        self.assertIsNone(result["error"])

    @patch("subprocess.run")
    def test_some_tests_fail(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = """
============================= test session starts =============================
collected 4 items

test_dummy.py::test_one PASSED                                        [ 25%]
test_dummy.py::test_two PASSED                                        [ 50%]
test_dummy.py::test_three PASSED                                      [ 75%]
test_dummy.py::test_edge_case FAILED                                  [100%]

=================================== FAILURES ===================================
________________________________ test_edge_case ________________________________

    def test_edge_case():
>       assert 0 == 1
E       assert 0 == 1

test_dummy.py:10: AssertionError
=========================== short test summary info ============================
FAILED test_dummy.py::test_edge_case - assert 0 == 1
========================= 1 failed, 3 passed in 0.05s ==========================
"""
        mock_proc.stderr = ""
        mock_proc.returncode = 1
        mock_run.return_value = mock_proc

        result = run_tests("test_dummy.py")
        self.assertEqual(result["passed"], 3)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["summary"], "3 passed, 1 failed")
        self.assertEqual(result["failures"], ["FAILED test_dummy.py::test_edge_case — assert 0 == 1"])
        self.assertFalse(result["timed_out"])
        self.assertIsNone(result["error"])

    @patch("subprocess.run")
    def test_test_file_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["pytest"], timeout=10)

        result = run_tests("test_dummy.py")
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["summary"], "0 passed")
        self.assertEqual(result["failures"], [])
        self.assertTrue(result["timed_out"])
        self.assertIsNone(result["error"])

    def test_path_traversal_blocked(self):
        result = run_tests("../outside_sandbox.py")
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["summary"], "0 passed")
        self.assertEqual(result["failures"], [])
        self.assertFalse(result["timed_out"])
        self.assertIn("Path traversal blocked", result["error"])

    def test_file_not_found(self):
        result = run_tests("non_existent_file.py")
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["summary"], "0 passed")
        self.assertEqual(result["failures"], [])
        self.assertFalse(result["timed_out"])
        self.assertIn("File not found", result["error"])


if __name__ == "__main__":
    unittest.main()
