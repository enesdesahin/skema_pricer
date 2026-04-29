from __future__ import annotations

import unittest

from pricer.engines.bonds import BondInputs, CallableBondInputs, price_bond, price_callable_bond


class BondEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference_inputs = BondInputs(
            face=1000.0,
            coupon_rate=0.05,
            maturity_years=10.0,
            ytm=0.05,
            frequency=2,
            settlement_days=0,
            notional=1_000_000.0,
            shift_bp=1.0,
        )

    def test_reference_case_matches_teacher_pricer_style_values(self) -> None:
        outputs = price_bond(self.reference_inputs)

        self.assertAlmostEqual(outputs.dirty_price, 1000.00, places=2)
        self.assertAlmostEqual(outputs.clean_price, 1000.00, places=2)
        self.assertAlmostEqual(outputs.accrued_interest, 0.0000, places=4)
        self.assertAlmostEqual(outputs.macaulay_duration, 7.9894, places=4)
        self.assertAlmostEqual(outputs.modified_duration, 7.7946, places=4)
        self.assertAlmostEqual(outputs.convexity, 73.6287, places=4)
        self.assertAlmostEqual(outputs.dv01_per_bond, 0.7795, places=4)
        self.assertAlmostEqual(outputs.pv01_notional, 779.46, places=2)
        self.assertAlmostEqual(outputs.pnl_for_shift, -779.09, places=2)

    def test_accrued_interest_reduces_clean_price(self) -> None:
        inputs = BondInputs(
            face=1000.0,
            coupon_rate=0.06,
            maturity_years=5.0,
            ytm=0.05,
            frequency=2,
            settlement_days=45,
        )

        outputs = price_bond(inputs)

        self.assertGreater(outputs.accrued_interest, 0.0)
        self.assertAlmostEqual(outputs.clean_price, outputs.dirty_price - outputs.accrued_interest, places=10)

    def test_positive_yield_shift_generates_negative_pnl(self) -> None:
        outputs = price_bond(self.reference_inputs)

        self.assertLess(outputs.pnl_for_shift, 0.0)

    def test_callable_reference_case_matches_teacher_pricer_style_values(self) -> None:
        outputs = price_callable_bond(
            CallableBondInputs(
                bond=self.reference_inputs,
                call_price=1000.0,
                first_call_year=5.0,
                rate_volatility=0.20,
                tree_steps=6,
            )
        )

        self.assertAlmostEqual(outputs.callable_price, 951.1451, places=4)
        self.assertAlmostEqual(outputs.option_value, 27.1843, places=4)
        self.assertAlmostEqual(outputs.yield_to_call, 0.05, places=4)
        self.assertAlmostEqual(outputs.yield_to_worst, 0.05, places=4)


if __name__ == "__main__":
    unittest.main()
