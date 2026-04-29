from __future__ import annotations

import unittest

from pricer.engines.bonus_certificate import (
    BonusCertificateInputs,
    payoff_at_maturity,
    price_bonus_certificate,
)


class BonusCertificateEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference_inputs = BonusCertificateInputs(
            underlying=100.0,
            bonus_level=120.0,
            barrier=70.0,
            cap=140.0,
            maturity_years=1.0,
            put_volatility=0.22,
            call_volatility=0.18,
            rate=0.05,
            dividend_yield=0.02,
            parity=1.0,
        )

    def test_reference_case_matches_teacher_pricer_style_values(self) -> None:
        outputs = price_bonus_certificate(self.reference_inputs)

        self.assertAlmostEqual(outputs.underlying_pv, 98.0199, places=4)
        self.assertAlmostEqual(outputs.put_down_and_out_value, 16.8388, places=4)
        self.assertAlmostEqual(outputs.short_call_value, -0.3726, places=4)
        self.assertAlmostEqual(outputs.certificate_price, 114.4861, places=4)
        self.assertAlmostEqual(outputs.barrier_distance_pct, 30.00, places=2)
        self.assertAlmostEqual(outputs.bonus_return_pct, 4.82, places=2)
        self.assertAlmostEqual(outputs.breakeven, 114.49, places=2)
        self.assertAlmostEqual(outputs.max_return_pct, 22.29, places=2)

    def test_payoff_respects_barrier_bonus_and_cap(self) -> None:
        self.assertAlmostEqual(payoff_at_maturity(self.reference_inputs, 60.0, barrier_breached=True), 60.0)
        self.assertAlmostEqual(payoff_at_maturity(self.reference_inputs, 80.0, barrier_breached=False), 120.0)
        self.assertAlmostEqual(payoff_at_maturity(self.reference_inputs, 130.0, barrier_breached=False), 130.0)
        self.assertAlmostEqual(payoff_at_maturity(self.reference_inputs, 150.0, barrier_breached=False), 140.0)


if __name__ == "__main__":
    unittest.main()
