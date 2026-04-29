from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Literal


DAY_COUNT_BASIS = 365.25
MIN_TIME_TO_MATURITY = 1e-10


@dataclass(frozen=True)
class OptionInputs:
    spot: float
    strike: float
    valuation_date: date
    maturity_date: date
    rate: float
    dividend_yield: float
    repo_rate: float
    volatility: float
    option_type: Literal["call", "put"]
    position: Literal["long", "short"] = "long"
    lots: float = 1.0
    multiplier: float = 100.0
    tick: float = 0.01
    day_count_basis: float = DAY_COUNT_BASIS

    @property
    def quantity(self) -> float:
        return self.lots * self.multiplier

    @property
    def position_sign(self) -> int:
        return 1 if self.position == "long" else -1

    @property
    def carry_yield(self) -> float:
        return self.dividend_yield + self.repo_rate

    def validate(self) -> None:
        if self.spot <= 0:
            raise ValueError("Spot must be strictly positive.")
        if self.strike <= 0:
            raise ValueError("Strike must be strictly positive.")
        if self.volatility < 0:
            raise ValueError("Volatility cannot be negative.")
        if self.lots <= 0:
            raise ValueError("Lots must be strictly positive.")
        if self.multiplier <= 0:
            raise ValueError("Multiplier must be strictly positive.")
        if self.tick <= 0:
            raise ValueError("Tick must be strictly positive.")
        if self.day_count_basis <= 0:
            raise ValueError("Day-count basis must be strictly positive.")
        if self.option_type not in {"call", "put"}:
            raise ValueError("Option type must be 'call' or 'put'.")
        if self.position not in {"long", "short"}:
            raise ValueError("Position must be 'long' or 'short'.")


@dataclass(frozen=True)
class OptionOutputs:
    time_to_maturity_years: float
    forward: float
    unit_price: float
    unit_delta: float
    unit_gamma: float
    unit_vega: float
    unit_rho: float
    unit_vanna: float
    signed_position_value: float
    signed_cash_delta: float
    signed_delta_hedge_shares: float
    signed_delta_t_plus_1d_shares: float
    signed_cash_gamma_per_1pct: float
    signed_theta_per_day: float
    signed_cash_vega_per_1pct: float
    signed_cash_charm_per_day: float
    signed_cash_vanna_per_1pct: float
    signed_cash_rho_per_1pct: float


@dataclass(frozen=True)
class GammaPnlOutputs:
    spot_move_pct: float
    iv_pct: float
    new_cash_delta: float
    gamma_pnl: float
    daily_move_pct: float


@dataclass(frozen=True)
class TradingShortcutsOutputs:
    break_even_spot: float
    break_even_pct: float
    break_even_realized_vol_pct: float
    break_even_lower_spot: float
    break_even_upper_spot: float
    break_even_ticks: float
    gamma_theta_ratio: float
    theta_earn_move_pct: float


@dataclass(frozen=True)
class ThetaBillOutputs:
    gamma_notional: float
    vol_pct: float
    theta_per_day: float
    daily_move_pct: float


@dataclass(frozen=True)
class AmericanOptionAnalysis:
    tree_steps: int
    european_tree_price: float
    american_price: float
    early_exercise_premium: float
    premium_pct: float
    american_delta: float


def year_fraction(start_date: date, end_date: date, basis: float = DAY_COUNT_BASIS) -> float:
    return (end_date - start_date).days / basis


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _intrinsic_value(option_type: str, spot: float, strike: float) -> float:
    if option_type == "call":
        return max(spot - strike, 0.0)
    return max(strike - spot, 0.0)


def _unit_delta_at_expiry(option_type: str, spot: float, strike: float) -> float:
    if option_type == "call":
        if spot > strike:
            return 1.0
        if spot < strike:
            return 0.0
        return 0.5
    if spot < strike:
        return -1.0
    if spot > strike:
        return 0.0
    return -0.5


def _d1_d2(spot: float, strike: float, time_to_maturity: float, rate: float, carry_yield: float, volatility: float) -> tuple[float, float]:
    vol_sqrt_t = volatility * math.sqrt(time_to_maturity)
    d1 = (
        math.log(spot / strike)
        + (rate - carry_yield + 0.5 * volatility * volatility) * time_to_maturity
    ) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return d1, d2


def _unit_price(inputs: OptionInputs, time_to_maturity: float) -> float:
    if time_to_maturity <= 0 or inputs.volatility == 0:
        forward_discounted = inputs.spot * math.exp(-inputs.carry_yield * time_to_maturity)
        strike_discounted = inputs.strike * math.exp(-inputs.rate * time_to_maturity)
        if inputs.option_type == "call":
            return max(forward_discounted - strike_discounted, 0.0)
        return max(strike_discounted - forward_discounted, 0.0)

    d1, d2 = _d1_d2(
        inputs.spot,
        inputs.strike,
        time_to_maturity,
        inputs.rate,
        inputs.carry_yield,
        inputs.volatility,
    )
    discounted_spot = inputs.spot * math.exp(-inputs.carry_yield * time_to_maturity)
    discounted_strike = inputs.strike * math.exp(-inputs.rate * time_to_maturity)

    if inputs.option_type == "call":
        return discounted_spot * _norm_cdf(d1) - discounted_strike * _norm_cdf(d2)
    return discounted_strike * _norm_cdf(-d2) - discounted_spot * _norm_cdf(-d1)


def _unit_delta(inputs: OptionInputs, time_to_maturity: float) -> float:
    if time_to_maturity <= 0 or inputs.volatility == 0:
        return _unit_delta_at_expiry(inputs.option_type, inputs.spot, inputs.strike)

    d1, _ = _d1_d2(
        inputs.spot,
        inputs.strike,
        time_to_maturity,
        inputs.rate,
        inputs.carry_yield,
        inputs.volatility,
    )
    discount = math.exp(-inputs.carry_yield * time_to_maturity)

    if inputs.option_type == "call":
        return discount * _norm_cdf(d1)
    return discount * (_norm_cdf(d1) - 1.0)


def _unit_gamma(inputs: OptionInputs, time_to_maturity: float) -> float:
    if time_to_maturity <= 0 or inputs.volatility == 0:
        return 0.0

    d1, _ = _d1_d2(
        inputs.spot,
        inputs.strike,
        time_to_maturity,
        inputs.rate,
        inputs.carry_yield,
        inputs.volatility,
    )
    return (
        math.exp(-inputs.carry_yield * time_to_maturity)
        * _norm_pdf(d1)
        / (inputs.spot * inputs.volatility * math.sqrt(time_to_maturity))
    )


def _unit_vega(inputs: OptionInputs, time_to_maturity: float) -> float:
    if time_to_maturity <= 0 or inputs.volatility == 0:
        return 0.0

    d1, _ = _d1_d2(
        inputs.spot,
        inputs.strike,
        time_to_maturity,
        inputs.rate,
        inputs.carry_yield,
        inputs.volatility,
    )
    return (
        inputs.spot
        * math.exp(-inputs.carry_yield * time_to_maturity)
        * _norm_pdf(d1)
        * math.sqrt(time_to_maturity)
    )


def _unit_rho(inputs: OptionInputs, time_to_maturity: float) -> float:
    if time_to_maturity <= 0:
        return 0.0
    if inputs.volatility == 0:
        if inputs.option_type == "call":
            return time_to_maturity * inputs.strike * math.exp(-inputs.rate * time_to_maturity)
        return -time_to_maturity * inputs.strike * math.exp(-inputs.rate * time_to_maturity)

    _, d2 = _d1_d2(
        inputs.spot,
        inputs.strike,
        time_to_maturity,
        inputs.rate,
        inputs.carry_yield,
        inputs.volatility,
    )
    factor = inputs.strike * time_to_maturity * math.exp(-inputs.rate * time_to_maturity)
    if inputs.option_type == "call":
        return factor * _norm_cdf(d2)
    return -factor * _norm_cdf(-d2)


def _unit_vanna(inputs: OptionInputs, time_to_maturity: float) -> float:
    if time_to_maturity <= 0 or inputs.volatility == 0:
        return 0.0

    d1, d2 = _d1_d2(
        inputs.spot,
        inputs.strike,
        time_to_maturity,
        inputs.rate,
        inputs.carry_yield,
        inputs.volatility,
    )
    return -math.exp(-inputs.carry_yield * time_to_maturity) * _norm_pdf(d1) * d2 / inputs.volatility


def _finite_difference_next_day(
    metric_fn,
    inputs: OptionInputs,
    time_to_maturity: float,
) -> float:
    next_time = max(time_to_maturity - 1.0 / inputs.day_count_basis, 0.0)
    return metric_fn(inputs, next_time)


def _safe_daily_move_from_vol(vol_pct: float) -> float:
    return vol_pct / math.sqrt(252.0)


def _crr_tree_values(
    inputs: OptionInputs,
    tree_steps: int,
    allow_early_exercise: bool,
) -> tuple[float, float]:
    time_to_maturity = max(
        year_fraction(inputs.valuation_date, inputs.maturity_date, inputs.day_count_basis),
        0.0,
    )
    if time_to_maturity <= 0:
        intrinsic = _intrinsic_value(inputs.option_type, inputs.spot, inputs.strike)
        delta = _unit_delta_at_expiry(inputs.option_type, inputs.spot, inputs.strike)
        return intrinsic, delta

    steps = max(int(tree_steps), 1)
    dt = time_to_maturity / steps
    if dt <= 0 or inputs.volatility <= 0:
        price = _unit_price(inputs, time_to_maturity)
        delta = _unit_delta(inputs, time_to_maturity)
        return price, delta

    up = math.exp(inputs.volatility * math.sqrt(dt))
    down = 1.0 / up
    growth = math.exp((inputs.rate - inputs.carry_yield) * dt)
    probability = (growth - down) / (up - down)
    probability = min(max(probability, 0.0), 1.0)
    discount = math.exp(-inputs.rate * dt)

    option_values = []
    for up_moves in range(steps + 1):
        spot_at_node = inputs.spot * (up ** up_moves) * (down ** (steps - up_moves))
        option_values.append(_intrinsic_value(inputs.option_type, spot_at_node, inputs.strike))

    step_one_values: list[float] | None = None
    for step in range(steps - 1, -1, -1):
        new_values = []
        for up_moves in range(step + 1):
            continuation = discount * (
                probability * option_values[up_moves + 1]
                + (1.0 - probability) * option_values[up_moves]
            )
            if allow_early_exercise:
                spot_at_node = inputs.spot * (up ** up_moves) * (down ** (step - up_moves))
                exercise = _intrinsic_value(inputs.option_type, spot_at_node, inputs.strike)
                new_values.append(max(continuation, exercise))
            else:
                new_values.append(continuation)
        option_values = new_values
        if step == 1:
            step_one_values = option_values.copy()

    if step_one_values is None:
        delta = _unit_delta(inputs, time_to_maturity)
    else:
        spot_up = inputs.spot * up
        spot_down = inputs.spot * down
        delta = (step_one_values[1] - step_one_values[0]) / (spot_up - spot_down)

    return option_values[0], delta


def calculate_gamma_pnl(
    outputs: OptionOutputs,
    spot_move_pct: float,
    iv_pct: float,
) -> GammaPnlOutputs:
    new_cash_delta = outputs.signed_cash_gamma_per_1pct * spot_move_pct
    gamma_pnl = 0.5 * outputs.signed_cash_gamma_per_1pct * (spot_move_pct ** 2) / 100.0
    daily_move_pct = _safe_daily_move_from_vol(iv_pct)
    return GammaPnlOutputs(
        spot_move_pct=spot_move_pct,
        iv_pct=iv_pct,
        new_cash_delta=new_cash_delta,
        gamma_pnl=gamma_pnl,
        daily_move_pct=daily_move_pct,
    )


def calculate_trading_shortcuts(
    inputs: OptionInputs,
    outputs: OptionOutputs,
) -> TradingShortcutsOutputs:
    if inputs.option_type == "call":
        break_even_spot = inputs.strike + outputs.unit_price
    else:
        break_even_spot = inputs.strike - outputs.unit_price
    break_even_pct = ((break_even_spot / inputs.spot) - 1.0) * 100.0

    gamma_abs = abs(outputs.signed_cash_gamma_per_1pct)
    theta_abs = abs(outputs.signed_theta_per_day)
    if gamma_abs > 0 and theta_abs > 0:
        theta_earn_move_pct = math.sqrt(200.0 * theta_abs / gamma_abs)
        gamma_theta_ratio = gamma_abs / theta_abs
    else:
        theta_earn_move_pct = 0.0
        gamma_theta_ratio = 0.0

    break_even_realized_vol_pct = theta_earn_move_pct * math.sqrt(252.0)
    break_even_lower_spot = inputs.spot * (1.0 - theta_earn_move_pct / 100.0)
    break_even_upper_spot = inputs.spot * (1.0 + theta_earn_move_pct / 100.0)
    break_even_ticks = 0.0 if inputs.tick <= 0 else (inputs.spot * theta_earn_move_pct / 100.0) / inputs.tick

    return TradingShortcutsOutputs(
        break_even_spot=break_even_spot,
        break_even_pct=break_even_pct,
        break_even_realized_vol_pct=break_even_realized_vol_pct,
        break_even_lower_spot=break_even_lower_spot,
        break_even_upper_spot=break_even_upper_spot,
        break_even_ticks=break_even_ticks,
        gamma_theta_ratio=gamma_theta_ratio,
        theta_earn_move_pct=theta_earn_move_pct,
    )


def quick_calc_gamma_theta_bill(
    gamma_notional: float,
    vol_pct: float,
) -> ThetaBillOutputs:
    theta_per_day = gamma_notional * (vol_pct ** 2) / 50_400.0
    daily_move_pct = _safe_daily_move_from_vol(vol_pct)
    return ThetaBillOutputs(
        gamma_notional=gamma_notional,
        vol_pct=vol_pct,
        theta_per_day=theta_per_day,
        daily_move_pct=daily_move_pct,
    )


def analyze_american_option(
    inputs: OptionInputs,
    tree_steps: int,
) -> AmericanOptionAnalysis:
    european_tree_price, _ = _crr_tree_values(inputs, tree_steps, allow_early_exercise=False)
    american_price, american_delta = _crr_tree_values(inputs, tree_steps, allow_early_exercise=True)
    early_exercise_premium = american_price - european_tree_price
    premium_pct = 0.0 if european_tree_price == 0 else (early_exercise_premium / european_tree_price) * 100.0
    return AmericanOptionAnalysis(
        tree_steps=tree_steps,
        european_tree_price=european_tree_price,
        american_price=american_price,
        early_exercise_premium=early_exercise_premium,
        premium_pct=premium_pct,
        american_delta=american_delta,
    )


def price_option(inputs: OptionInputs) -> OptionOutputs:
    inputs.validate()

    time_to_maturity = max(
        year_fraction(inputs.valuation_date, inputs.maturity_date, inputs.day_count_basis),
        0.0,
    )
    effective_time = max(time_to_maturity, MIN_TIME_TO_MATURITY)

    forward = inputs.spot * math.exp((inputs.rate - inputs.carry_yield) * time_to_maturity)
    unit_price = _unit_price(inputs, time_to_maturity)
    unit_delta = _unit_delta(inputs, time_to_maturity)
    unit_gamma = _unit_gamma(inputs, effective_time if time_to_maturity > 0 else 0.0)
    unit_vega = _unit_vega(inputs, effective_time if time_to_maturity > 0 else 0.0)
    unit_rho = _unit_rho(inputs, time_to_maturity)
    unit_vanna = _unit_vanna(inputs, effective_time if time_to_maturity > 0 else 0.0)

    quantity = inputs.quantity
    sign = inputs.position_sign

    signed_delta_shares = sign * unit_delta * quantity
    next_day_delta_shares = sign * _finite_difference_next_day(_unit_delta, inputs, time_to_maturity) * quantity
    signed_delta_t_plus_1d_shares = next_day_delta_shares - signed_delta_shares

    signed_position_value = sign * unit_price * quantity
    signed_cash_delta = signed_delta_shares * inputs.spot
    signed_cash_gamma_per_1pct = sign * unit_gamma * quantity * inputs.spot * inputs.spot * 0.01
    next_day_position_value = sign * _finite_difference_next_day(_unit_price, inputs, time_to_maturity) * quantity
    signed_theta_per_day = next_day_position_value - signed_position_value
    signed_cash_vega_per_1pct = sign * unit_vega * quantity * 0.01
    signed_cash_charm_per_day = signed_delta_t_plus_1d_shares * inputs.spot
    signed_cash_vanna_per_1pct = sign * unit_vanna * quantity * inputs.spot * 0.01
    signed_cash_rho_per_1pct = sign * unit_rho * quantity * 0.01

    return OptionOutputs(
        time_to_maturity_years=time_to_maturity,
        forward=forward,
        unit_price=unit_price,
        unit_delta=unit_delta,
        unit_gamma=unit_gamma,
        unit_vega=unit_vega,
        unit_rho=unit_rho,
        unit_vanna=unit_vanna,
        signed_position_value=signed_position_value,
        signed_cash_delta=signed_cash_delta,
        signed_delta_hedge_shares=signed_delta_shares,
        signed_delta_t_plus_1d_shares=signed_delta_t_plus_1d_shares,
        signed_cash_gamma_per_1pct=signed_cash_gamma_per_1pct,
        signed_theta_per_day=signed_theta_per_day,
        signed_cash_vega_per_1pct=signed_cash_vega_per_1pct,
        signed_cash_charm_per_day=signed_cash_charm_per_day,
        signed_cash_vanna_per_1pct=signed_cash_vanna_per_1pct,
        signed_cash_rho_per_1pct=signed_cash_rho_per_1pct,
    )
