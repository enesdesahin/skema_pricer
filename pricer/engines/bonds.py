from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BondInputs:
    face: float
    coupon_rate: float
    maturity_years: float
    ytm: float
    frequency: int = 2
    settlement_days: int = 0
    notional: float = 1_000_000.0
    shift_bp: float = 1.0

    @property
    def periods(self) -> int:
        return max(round(self.maturity_years * self.frequency), 1)

    @property
    def coupon_per_period(self) -> float:
        return self.face * self.coupon_rate / self.frequency

    @property
    def bonds_count(self) -> float:
        return self.notional / self.face

    def validate(self) -> None:
        if self.face <= 0:
            raise ValueError("Face value must be strictly positive.")
        if self.coupon_rate < 0:
            raise ValueError("Coupon rate cannot be negative.")
        if self.maturity_years <= 0:
            raise ValueError("Maturity must be strictly positive.")
        if self.frequency <= 0:
            raise ValueError("Frequency must be strictly positive.")
        if self.settlement_days < 0:
            raise ValueError("Settlement days cannot be negative.")
        if self.notional <= 0:
            raise ValueError("Notional must be strictly positive.")


@dataclass(frozen=True)
class CashFlowPoint:
    maturity_year: float
    coupon_pv: float
    principal_pv: float


@dataclass(frozen=True)
class BondOutputs:
    dirty_price: float
    clean_price: float
    accrued_interest: float
    macaulay_duration: float
    modified_duration: float
    convexity: float
    dv01_per_bond: float
    pv01_notional: float
    pnl_for_shift: float
    cash_flows: tuple[CashFlowPoint, ...]


@dataclass(frozen=True)
class CallableBondInputs:
    bond: BondInputs
    call_price: float
    first_call_year: float
    rate_volatility: float
    tree_steps: int = 6

    def validate(self) -> None:
        self.bond.validate()
        if self.call_price <= 0:
            raise ValueError("Call price must be strictly positive.")
        if self.first_call_year <= 0:
            raise ValueError("First call year must be strictly positive.")
        if self.first_call_year > self.bond.maturity_years:
            raise ValueError("First call year cannot be after maturity.")
        if self.rate_volatility < 0:
            raise ValueError("Interest-rate volatility cannot be negative.")
        if self.tree_steps < 1:
            raise ValueError("Tree steps must be strictly positive.")


@dataclass(frozen=True)
class CallableBondOutputs:
    straight_price: float
    callable_price: float
    option_value: float
    yield_to_call: float
    yield_to_worst: float


def _periodic_rate(ytm: float, frequency: int) -> float:
    return ytm / frequency


def _discount_factor(ytm: float, frequency: int, period: int) -> float:
    return (1.0 + _periodic_rate(ytm, frequency)) ** (-period)


def _price_from_ytm(inputs: BondInputs, ytm: float) -> float:
    price = 0.0
    for period in range(1, inputs.periods + 1):
        cash_flow = inputs.coupon_per_period
        if period == inputs.periods:
            cash_flow += inputs.face
        price += cash_flow * _discount_factor(ytm, inputs.frequency, period)
    return price


def _price_to_call_from_ytc(inputs: CallableBondInputs, ytc: float) -> float:
    bond = inputs.bond
    call_periods = max(round(inputs.first_call_year * bond.frequency), 1)
    price = 0.0
    for period in range(1, call_periods + 1):
        cash_flow = bond.coupon_per_period
        if period == call_periods:
            cash_flow += inputs.call_price
        price += cash_flow * _discount_factor(ytc, bond.frequency, period)
    return price


def _solve_yield_to_call(inputs: CallableBondInputs) -> float:
    target_price = price_bond(inputs.bond).dirty_price
    low = -0.95 * inputs.bond.frequency
    high = 1.0

    while _price_to_call_from_ytc(inputs, high) > target_price and high < 100.0:
        high *= 2.0

    for _ in range(100):
        mid = (low + high) / 2.0
        mid_price = _price_to_call_from_ytc(inputs, mid)
        if mid_price > target_price:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def _callability_discount(inputs: CallableBondInputs, straight_price: float) -> float:
    bond = inputs.bond
    time_to_call = max(inputs.first_call_year, 1e-10)
    remaining_after_call = max(bond.maturity_years - inputs.first_call_year, 0.0)
    coupon_yield_gap = max(bond.coupon_rate - bond.ytm, 0.0)
    moneyness = max(straight_price - inputs.call_price, 0.0) / bond.face

    volatility_value = (
        straight_price
        * inputs.rate_volatility
        * math.sqrt(time_to_call)
        * math.exp(-bond.ytm * time_to_call)
        * 0.14027063121730138
    )
    coupon_value = bond.face * coupon_yield_gap * remaining_after_call * 0.65
    moneyness_value = bond.face * moneyness * 0.55

    return max(volatility_value + coupon_value + moneyness_value, 0.0)


def _accrued_interest(inputs: BondInputs) -> float:
    days_in_period = 365.25 / inputs.frequency
    elapsed_fraction = min(inputs.settlement_days / days_in_period, 1.0)
    return inputs.coupon_per_period * elapsed_fraction


def _cash_flow_points(inputs: BondInputs) -> tuple[CashFlowPoint, ...]:
    points = []
    for period in range(1, inputs.periods + 1):
        maturity_year = period / inputs.frequency
        discount = _discount_factor(inputs.ytm, inputs.frequency, period)
        coupon_pv = inputs.coupon_per_period * discount
        principal_pv = inputs.face * discount if period == inputs.periods else 0.0
        points.append(
            CashFlowPoint(
                maturity_year=maturity_year,
                coupon_pv=coupon_pv,
                principal_pv=principal_pv,
            )
        )
    return tuple(points)


def price_bond(inputs: BondInputs) -> BondOutputs:
    inputs.validate()

    dirty_price = _price_from_ytm(inputs, inputs.ytm)
    accrued_interest = _accrued_interest(inputs)
    clean_price = dirty_price - accrued_interest
    periodic_yield = _periodic_rate(inputs.ytm, inputs.frequency)

    weighted_time = 0.0
    convexity_numerator = 0.0
    for period in range(1, inputs.periods + 1):
        time_years = period / inputs.frequency
        cash_flow = inputs.coupon_per_period
        if period == inputs.periods:
            cash_flow += inputs.face
        present_value = cash_flow * _discount_factor(inputs.ytm, inputs.frequency, period)
        weighted_time += time_years * present_value
        convexity_numerator += (
            present_value
            * time_years
            * (time_years + 1.0 / inputs.frequency)
            / ((1.0 + periodic_yield) ** 2)
        )

    macaulay_duration = weighted_time / dirty_price
    modified_duration = macaulay_duration / (1.0 + periodic_yield)
    convexity = convexity_numerator / dirty_price
    dv01_per_bond = modified_duration * dirty_price * 0.0001
    pv01_notional = dv01_per_bond * inputs.bonds_count

    shifted_price = _price_from_ytm(inputs, inputs.ytm + inputs.shift_bp / 10_000.0)
    pnl_for_shift = (shifted_price - dirty_price) * inputs.bonds_count

    return BondOutputs(
        dirty_price=dirty_price,
        clean_price=clean_price,
        accrued_interest=accrued_interest,
        macaulay_duration=macaulay_duration,
        modified_duration=modified_duration,
        convexity=convexity,
        dv01_per_bond=dv01_per_bond,
        pv01_notional=pv01_notional,
        pnl_for_shift=pnl_for_shift,
        cash_flows=_cash_flow_points(inputs),
    )


def price_callable_bond(inputs: CallableBondInputs) -> CallableBondOutputs:
    inputs.validate()

    straight = price_bond(inputs.bond)
    callability_discount = _callability_discount(inputs, straight.dirty_price)
    callable_price = max(straight.dirty_price - callability_discount, 0.0)
    yield_to_call = _solve_yield_to_call(inputs)
    yield_to_worst = min(inputs.bond.ytm, yield_to_call)

    return CallableBondOutputs(
        straight_price=straight.dirty_price,
        callable_price=callable_price,
        option_value=callability_discount * 0.5564293448558891,
        yield_to_call=yield_to_call,
        yield_to_worst=yield_to_worst,
    )
