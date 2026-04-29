from __future__ import annotations

import unittest

from pricer.engines.turbo import (
    TurboInputs,
    build_spot_scenarios,
    calculate_turbo_drift,
    price_turbo,
)


class TurboEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference_inputs = TurboInputs(
            turbo_type="long",
            underlying=100.0,
            strike=80.0,
            barrier=82.0,
            parity=10.0,
            financing_rate=0.02,
            lots=100.0,
        )

    def test_reference_case_matches_teacher_pricer_style_values(self) -> None:
        outputs = price_turbo(self.reference_inputs)

        self.assertAlmostEqual(outputs.turbo_price, 2.0000, places=4)
        self.assertAlmostEqual(outputs.leverage, 5.0, places=1)
        self.assertAlmostEqual(outputs.distance_to_barrier_pct, 18.00, places=2)
        self.assertAlmostEqual(outputs.daily_funding_cost, 0.0044, places=4)
        self.assertAlmostEqual(outputs.initial_delta_cash, 200.00, places=2)
        self.assertAlmostEqual(outputs.leveraged_delta_cash, 1000.00, places=2)
        self.assertAlmostEqual(outputs.equivalent_underlying, 10.0, places=1)

    def test_financing_drift_matches_reference_values(self) -> None:
        drift = calculate_turbo_drift(self.reference_inputs, holding_days=30)

        self.assertAlmostEqual(drift.strike_today, 80.00, places=2)
        self.assertAlmostEqual(drift.strike_after, 80.1333, places=4)
        self.assertAlmostEqual(drift.strike_drift, 0.1333, places=4)
        self.assertAlmostEqual(drift.turbo_price_drifted, 1.9867, places=4)
        self.assertAlmostEqual(drift.value_erosion, -0.0133, places=4)

    def test_scenarios_flag_knockout_below_long_barrier(self) -> None:
        scenarios = build_spot_scenarios(self.reference_inputs, points=5)

        self.assertTrue(scenarios[0].knocked_out)
        self.assertIsNone(scenarios[0].turbo_price)
        self.assertLess(scenarios[0].pnl_per_unit, 0.0)
        self.assertFalse(scenarios[-1].knocked_out)
        self.assertGreater(scenarios[-1].turbo_price, price_turbo(self.reference_inputs).turbo_price)


if __name__ == "__main__":
    unittest.main()
