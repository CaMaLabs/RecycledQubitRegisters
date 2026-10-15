#!/usr/bin/env python3
"""Pure-Python tests for the fail-closed IBM Runtime plan guard."""
import unittest

from ibm_runtime_guard import RuntimePlanGuardError, assert_open_plan_submission


class FakeBackend:
    name = "ibm_fez"


class FakeService:
    def __init__(self, active, rows):
        self._active = active
        self._rows = rows

    def active_instance(self):
        return self._active

    def instances(self):
        return self._rows


class RuntimeGuardTests(unittest.TestCase):
    def test_open_plan_passes(self):
        svc = FakeService(
            "crn:open",
            [
                {"crn": "crn:open", "name": "open-instance", "plan": "open"},
                {"crn": "crn:paid", "name": "paid-instance", "plan": "pay-as-you-go"},
            ],
        )
        receipt = assert_open_plan_submission(svc, FakeBackend())
        self.assertTrue(receipt["open_plan_verified"])
        self.assertEqual(receipt["plan"], "open")

    def test_paid_plan_fails_closed(self):
        svc = FakeService(
            "crn:paid",
            [{"crn": "crn:paid", "name": "paid-instance", "plan": "pay-as-you-go"}],
        )
        with self.assertRaises(RuntimePlanGuardError):
            assert_open_plan_submission(svc, FakeBackend())

    def test_unknown_active_instance_fails_closed(self):
        svc = FakeService(
            "crn:unknown",
            [{"crn": "crn:open", "name": "open-instance", "plan": "open"}],
        )
        with self.assertRaises(RuntimePlanGuardError):
            assert_open_plan_submission(svc, FakeBackend())

    def test_duplicate_match_fails_closed(self):
        svc = FakeService(
            "same",
            [
                {"crn": "same", "name": "a", "plan": "open"},
                {"crn": "x", "name": "same", "plan": "open"},
            ],
        )
        with self.assertRaises(RuntimePlanGuardError):
            assert_open_plan_submission(svc, FakeBackend())


if __name__ == "__main__":
    unittest.main()
