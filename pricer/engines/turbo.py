from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TRADING_DAY_BASIS = 360.0


@dataclass(frozen=True)
class TurboInputs:
    turbo_type: Literal["long", "short"]
    underlying: float
    strike: float
    barrier: float
    parity: float
    financing_rate: float
    lots: float
    day_count_basis: float = TRADING_DAY_BASIS

    @property
    def sign(self) -> int:
        return 1 if self.turbo_type == "long" else -1

    @property
    def equivalent_underlying(self) -> float:
        return self.lots / self.parity

    def validate(self) -> None:
        if self.turbo_type not in {"long", "short"}:
            raise ValueError("Turbo type must be 'long' or 'short'.")
        if self.underlying <= 0:
            raise ValueError("Underlying must be strictly positive.")
        if self.strike <= 0:
            raise ValueError("Strike / financing level must be strictly positive.")
        if self.barrier <= 0:
            raise ValueError("Barrier must be strictly positive.")
        if self.parity <= 0:
            raise ValueError("Parity must be strictly positive.")
        if self.lots <= 0:
            raise ValueError("Lots must be strictly positive.")
        if self.day_count_basis <= 0:
            raise ValueError("Day-count basis must be strictly positive.")
        if self.turbo_type == "long" and self.barrier <= self.strike:
            raise ValueError("For a long turbo, barrier should be above the strike / financing level.")
        if self.turbo_type == "short" and self.barrier >= self.strike:
            raise ValueError("For a short turbo, barrier should be below the strike / financing level.")


@dataclass(frozen=True)
class TurboOutputs:
    turbo_price: float
    leverage: float
    distance_to_barrier_pct: float
    daily_funding_cost: float
    initial_delta_cash: float
    leveraged_delta_cash: float
    equivalent_underlying: float


@dataclass(frozen=True)
class TurboDriftOutputs:
    holding_days: int
    strike_today: float
    strike_after: float
    strike_drift: float
    turbo_price_drifted: float
    value_erosion: float


@dataclass(frozen=True)
class TurboScenario:
    spot: float
    turbo_price: float | None
    leverage: float | None
    distance_to_barrier_pct: float
    pnl_per_unit: float
    knocked_out: bool


def _raw_price(turbo_type: str, spot: float, strike: float, parity: float) -> float:
    if turbo_type == "long":
        return (spot - strike) / parity
    return (strike - spot) / parity


def is_knocked_out(inputs: TurboInputs, spot: float | None = None) -> bool:
    observed_spot = inputs.underlying if spot is None else spot
    if inputs.turbo_type == "long":
        return observed_spot <= inputs.barrier
    return observed_spot >= inputs.barrier


def turbo_price_at_spot(inputs: TurboInputs, spot: float, strike: float | None = None) -> float:
    financing_level = inputs.strike if strike is None else strike
    if is_knocked_out(inputs, spot):
        return 0.0
    return max(_raw_price(inputs.turbo_type, spot, financing_level, inputs.parity), 0.0)


def distance_to_barrier_pct(inputs: TurboInputs, spot: float | None = None) -> float:
    observed_spot = inputs.underlying if spot is None else spot
    if inputs.turbo_type == "long":
        return ((observed_spot - inputs.barrier) / observed_spot) * 100.0
    return ((inputs.barrier - observed_spot) / observed_spot) * 100.0


def strike_after_days(inputs: TurboInputs, holding_days: int) -> float:
    drift = inputs.strike * inputs.financing_rate * holding_days / inputs.day_count_basis
    if inputs.turbo_type == "long":
        return inputs.strike + drift
    return inputs.strike - drift


def price_turbo(inputs: TurboInputs) -> TurboOutputs:
    inputs.validate()

    turbo_price = turbo_price_at_spot(inputs, inputs.underlying)
    leverage = 0.0 if turbo_price == 0 else inputs.underlying / (turbo_price * inputs.parity)
    daily_funding_cost = inputs.strike * inputs.financing_rate / inputs.day_count_basis
    leveraged_delta_cash = inputs.underlying * inputs.equivalent_underlying
    initial_delta_cash = turbo_price * inputs.lots

    return TurboOutputs(
        turbo_price=turbo_price,
        leverage=leverage,
        distance_to_barrier_pct=distance_to_barrier_pct(inputs),
        daily_funding_cost=daily_funding_cost,
        initial_delta_cash=initial_delta_cash,
        leveraged_delta_cash=leveraged_delta_cash,
        equivalent_underlying=inputs.equivalent_underlying,
    )


def calculate_turbo_drift(inputs: TurboInputs, holding_days: int) -> TurboDriftOutputs:
    if holding_days < 0:
        raise ValueError("Holding days cannot be negative.")

    outputs = price_turbo(inputs)
    strike_after = strike_after_days(inputs, holding_days)
    drifted_price = turbo_price_at_spot(inputs, inputs.underlying, strike=strike_after)
    value_erosion = drifted_price - outputs.turbo_price

    return TurboDriftOutputs(
        holding_days=holding_days,
        strike_today=inputs.strike,
        strike_after=strike_after,
        strike_drift=strike_after - inputs.strike,
        turbo_price_drifted=drifted_price,
        value_erosion=value_erosion,
    )


def build_spot_scenarios(inputs: TurboInputs, points: int = 25) -> tuple[TurboScenario, ...]:
    if points < 2:
        raise ValueError("At least two scenario points are required.")

    current_price = price_turbo(inputs).turbo_price
    if inputs.turbo_type == "long":
        low = inputs.barrier * 0.98
        high = max(inputs.underlying * 1.2, inputs.barrier * 1.1)
    else:
        low = min(inputs.underlying * 0.8, inputs.barrier * 0.9)
        high = inputs.barrier * 1.02

    scenarios = []
    for index in range(points):
        spot = low + (high - low) * index / (points - 1)
        knocked_out = is_knocked_out(inputs, spot)
        scenario_price = None if knocked_out else turbo_price_at_spot(inputs, spot)
        scenario_leverage = None
        if scenario_price and scenario_price > 0:
            scenario_leverage = spot / (scenario_price * inputs.parity)
        pnl_per_unit = (0.0 if scenario_price is None else scenario_price) - current_price
        scenarios.append(
            TurboScenario(
                spot=spot,
                turbo_price=scenario_price,
                leverage=scenario_leverage,
                distance_to_barrier_pct=distance_to_barrier_pct(inputs, spot),
                pnl_per_unit=pnl_per_unit,
                knocked_out=knocked_out,
            )
        )

    return tuple(scenarios)
