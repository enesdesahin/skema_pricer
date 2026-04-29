from __future__ import annotations

import unittest

from pricer.engines.discount_certificate import (
    DiscountCertificateInputs,
    payoff_at_maturity,
    price_discount_certificate,
)


class DiscountCertificateEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference_inputs = DiscountCertificateInputs(
            underlying=100.0,
            cap=110.0,
            maturity_years=1.0,
            volatility=0.20,
            rate=0.05,
            dividend_yield=0.02,
            parity=1.0,
        )

    def test_reference_case_matches_teacher_pricer_style_values(self) -> None:
        outputs = price_discount_certificate(self.reference_inputs)

        self.assertAlmostEqual(outputs.underlying_pv, 98.0199, places=4)
        self.assertAlmostEqual(outputs.short_call_value, -5.1886, places=4)
        self.assertAlmostEqual(outputs.certificate_price, 92.8313, places=4)
        self.assertAlmostEqual(outputs.discount_pct, 7.17, places=2)
        self.assertAlmostEqual(outputs.max_return_pct, 18.49, places=2)
        self.assertAlmostEqual(outputs.max_payoff, 110.00, places=2)
        self.assertAlmostEqual(outputs.breakeven, 92.83, places=2)
        self.assertAlmostEqual(outputs.sideways_return_pct, 7.72, places=2)

    def test_payoff_is_capped_at_maturity(self) -> None:
        self.assertAlmostEqual(payoff_at_maturity(self.reference_inputs, 80.0), 80.0)
        self.assertAlmostEqual(payoff_at_maturity(self.reference_inputs, 120.0), 110.0)


if __name__ == "__main__":
    unittest.main()
