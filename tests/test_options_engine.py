from __future__ import annotations

from datetime import date
import math
import unittest

from pricer.engines.options import (
    OptionInputs,
    analyze_american_option,
    calculate_gamma_pnl,
    calculate_trading_shortcuts,
    price_option,
    quick_calc_gamma_theta_bill,
)


class OptionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference_kwargs = dict(
            spot=100.0,
            strike=100.0,
            valuation_date=date(2026, 4, 13),
            maturity_date=date(2027, 4, 13),
            rate=0.05,
            dividend_yield=0.02,
            repo_rate=0.0,
            volatility=0.20,
            option_type="call",
            position="long",
            lots=1.0,
            multiplier=100.0,
            tick=0.01,
        )

    def test_reference_case_matches_deployed_defaults(self) -> None:
        outputs = price_option(OptionInputs(**self.reference_kwargs))

        self.assertAlmostEqual(outputs.time_to_maturity_years, 365 / 365.25, places=6)
        self.assertAlmostEqual(outputs.unit_price, 9.2235, places=4)
        self.assertAlmostEqual(outputs.forward, 103.0433, places=4)
        self.assertAlmostEqual(outputs.signed_cash_delta, 5868.27, places=2)
        self.assertAlmostEqual(outputs.signed_delta_hedge_shares, 58.68, places=2)
        self.assertAlmostEqual(outputs.signed_delta_t_plus_1d_shares, -0.0098, places=4)
        self.assertAlmostEqual(outputs.signed_cash_gamma_per_1pct, 189.58, places=2)
        self.assertAlmostEqual(outputs.signed_theta_per_day, -1.39, places=2)
        self.assertAlmostEqual(outputs.signed_cash_vega_per_1pct, 37.89, places=2)
        self.assertAlmostEqual(outputs.signed_cash_charm_per_day, -0.98, places=2)
        self.assertAlmostEqual(outputs.signed_cash_vanna_per_1pct, -9.47, places=2)
        self.assertAlmostEqual(outputs.signed_cash_rho_per_1pct, 49.43, places=2)

    def test_put_call_parity_holds(self) -> None:
        call_inputs = dict(self.reference_kwargs)
        put_inputs = dict(self.reference_kwargs)
        put_inputs["option_type"] = "put"

        call = price_option(OptionInputs(**call_inputs))
        put = price_option(OptionInputs(**put_inputs))

        lhs = call.unit_price - put.unit_price
        rhs = (
            self.reference_kwargs["spot"]
            * math.exp(
                -(
                    self.reference_kwargs["dividend_yield"]
                    + self.reference_kwargs["repo_rate"]
                )
                * call.time_to_maturity_years
            )
            - self.reference_kwargs["strike"]
            * math.exp(-self.reference_kwargs["rate"] * call.time_to_maturity_years)
        )
        self.assertAlmostEqual(lhs, rhs, places=8)

    def test_short_position_flips_signed_exposures(self) -> None:
        long_inputs = dict(self.reference_kwargs)
        short_inputs = dict(self.reference_kwargs)
        short_inputs["position"] = "short"

        long_outputs = price_option(OptionInputs(**long_inputs))
        short_outputs = price_option(OptionInputs(**short_inputs))

        self.assertAlmostEqual(short_outputs.unit_price, long_outputs.unit_price, places=10)
        self.assertAlmostEqual(short_outputs.signed_cash_delta, -long_outputs.signed_cash_delta, places=10)
        self.assertAlmostEqual(short_outputs.signed_cash_gamma_per_1pct, -long_outputs.signed_cash_gamma_per_1pct, places=10)
        self.assertAlmostEqual(short_outputs.signed_theta_per_day, -long_outputs.signed_theta_per_day, places=10)

    def test_expired_option_returns_intrinsic_value(self) -> None:
        expired_inputs = dict(self.reference_kwargs)
        expired_inputs["valuation_date"] = date(2027, 4, 13)
        expired_inputs["maturity_date"] = date(2027, 4, 13)

        outputs = price_option(
            OptionInputs(**expired_inputs)
        )

        self.assertEqual(outputs.unit_price, 0.0)
        self.assertEqual(outputs.forward, 100.0)
        self.assertEqual(outputs.signed_cash_gamma_per_1pct, 0.0)
        self.assertEqual(outputs.signed_cash_vega_per_1pct, 0.0)

    def test_gamma_pnl_calculator_matches_reference_values(self) -> None:
        outputs = price_option(OptionInputs(**self.reference_kwargs))
        gamma_pnl = calculate_gamma_pnl(outputs, spot_move_pct=1.0, iv_pct=20.0)

        self.assertAlmostEqual(gamma_pnl.new_cash_delta, 189.58, places=2)
        self.assertAlmostEqual(gamma_pnl.gamma_pnl, 0.95, places=2)
        self.assertAlmostEqual(gamma_pnl.daily_move_pct, 1.26, places=2)

    def test_trading_shortcuts_match_reference_values(self) -> None:
        inputs = OptionInputs(**self.reference_kwargs)
        outputs = price_option(inputs)
        shortcuts = calculate_trading_shortcuts(inputs, outputs)

        self.assertAlmostEqual(shortcuts.break_even_spot, 109.22, places=2)
        self.assertAlmostEqual(shortcuts.break_even_pct, 9.22, places=2)
        self.assertAlmostEqual(shortcuts.break_even_realized_vol_pct, 19.26, places=2)
        self.assertAlmostEqual(shortcuts.gamma_theta_ratio, 135.93, places=2)
        self.assertAlmostEqual(shortcuts.theta_earn_move_pct, 1.21, places=2)
        self.assertAlmostEqual(shortcuts.break_even_lower_spot, 98.79, places=2)
        self.assertAlmostEqual(shortcuts.break_even_upper_spot, 101.21, places=2)
        self.assertAlmostEqual(shortcuts.break_even_ticks, 121.30, places=2)

    def test_quick_calc_gamma_theta_bill_matches_reference_values(self) -> None:
        bill = quick_calc_gamma_theta_bill(gamma_notional=20_000_000.0, vol_pct=22.0)

        self.assertAlmostEqual(bill.theta_per_day, 192063.49, places=2)
        self.assertAlmostEqual(bill.daily_move_pct, 1.39, places=2)

    def test_american_tree_matches_reference_values(self) -> None:
        inputs = OptionInputs(**self.reference_kwargs)
        analysis = analyze_american_option(inputs, tree_steps=100)

        self.assertAlmostEqual(analysis.european_tree_price, 9.2041, places=4)
        self.assertAlmostEqual(analysis.american_price, 9.2041, places=4)
        self.assertAlmostEqual(analysis.early_exercise_premium, 0.0, places=4)
        self.assertAlmostEqual(analysis.premium_pct, 0.0, places=2)
        self.assertAlmostEqual(analysis.american_delta, 0.5867, places=4)


if __name__ == "__main__":
    unittest.main()
