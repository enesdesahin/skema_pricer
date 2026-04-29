from __future__ import annotations

from dataclasses import dataclass
import math


DOWN_AND_OUT_PUT_FACTOR = 0.23276


@dataclass(frozen=True)
class BonusCertificateInputs:
    underlying: float
    bonus_level: float
    barrier: float
    cap: float | None
    maturity_years: float
    put_volatility: float
    call_volatility: float
    rate: float
    dividend_yield: float
    parity: float = 1.0

    def validate(self) -> None:
        if self.underlying <= 0:
            raise ValueError("Underlying must be strictly positive.")
        if self.bonus_level <= 0:
            raise ValueError("Bonus level must be strictly positive.")
        if self.barrier <= 0:
            raise ValueError("Barrier must be strictly positive.")
        if self.cap is not None and self.cap <= 0:
            raise ValueError("Cap must be strictly positive.")
        if self.cap is not None and self.cap < self.bonus_level:
            raise ValueError("Cap should be greater than or equal to the bonus level.")
        if self.maturity_years <= 0:
            raise ValueError("Maturity must be strictly positive.")
        if self.put_volatility < 0 or self.call_volatility < 0:
            raise ValueError("Volatility cannot be negative.")
        if self.parity <= 0:
            raise ValueError("Parity must be strictly positive.")


@dataclass(frozen=True)
class BonusCertificateOutputs:
    underlying_pv: float
    put_down_and_out_value: float
    short_call_value: float
    certificate_price: float
    barrier_distance_pct: float
    bonus_return_pct: float
    breakeven: float
    max_return_pct: float | None


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _black_scholes_price(
    option_type: str,
    spot: float,
    strike: float,
    maturity_years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
) -> float:
    if volatility == 0:
        discounted_spot = spot * math.exp(-dividend_yield * maturity_years)
        discounted_strike = strike * math.exp(-rate * maturity_years)
        if option_type == "call":
            return max(discounted_spot - discounted_strike, 0.0)
        return max(discounted_strike - discounted_spot, 0.0)

    vol_sqrt_t = volatility * math.sqrt(maturity_years)
    d1 = (
        math.log(spot / strike)
        + (rate - dividend_yield + 0.5 * volatility * volatility) * maturity_years
    ) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    discounted_spot = spot * math.exp(-dividend_yield * maturity_years)
    discounted_strike = strike * math.exp(-rate * maturity_years)

    if option_type == "call":
        return discounted_spot * _norm_cdf(d1) - discounted_strike * _norm_cdf(d2)
    return discounted_strike * _norm_cdf(-d2) - discounted_spot * _norm_cdf(-d1)


def _down_and_out_put_proxy(inputs: BonusCertificateInputs) -> float:
    vanilla_put = _black_scholes_price(
        option_type="put",
        spot=inputs.underlying,
        strike=inputs.bonus_level,
        maturity_years=inputs.maturity_years,
        rate=inputs.rate,
        dividend_yield=inputs.dividend_yield,
        volatility=inputs.put_volatility,
    )
    barrier_ratio = min(max(inputs.barrier / inputs.bonus_level, 0.0), 1.0)
    survival_factor = max(0.0, 1.0 - DOWN_AND_OUT_PUT_FACTOR * barrier_ratio)
    return vanilla_put * survival_factor


def price_bonus_certificate(inputs: BonusCertificateInputs) -> BonusCertificateOutputs:
    inputs.validate()

    underlying_pv = inputs.underlying * math.exp(-inputs.dividend_yield * inputs.maturity_years) / inputs.parity
    put_down_and_out_value = _down_and_out_put_proxy(inputs) / inputs.parity
    call_value = 0.0
    if inputs.cap is not None:
        call_value = _black_scholes_price(
            option_type="call",
            spot=inputs.underlying,
            strike=inputs.cap,
            maturity_years=inputs.maturity_years,
            rate=inputs.rate,
            dividend_yield=inputs.dividend_yield,
            volatility=inputs.call_volatility,
        )
    short_call_value = -call_value / inputs.parity
    certificate_price = underlying_pv + put_down_and_out_value + short_call_value
    bonus_payoff = inputs.bonus_level / inputs.parity
    max_payoff = None if inputs.cap is None else inputs.cap / inputs.parity

    return BonusCertificateOutputs(
        underlying_pv=underlying_pv,
        put_down_and_out_value=put_down_and_out_value,
        short_call_value=short_call_value,
        certificate_price=certificate_price,
        barrier_distance_pct=((inputs.underlying - inputs.barrier) / inputs.underlying) * 100.0,
        bonus_return_pct=(bonus_payoff / certificate_price - 1.0) * 100.0,
        breakeven=certificate_price,
        max_return_pct=None if max_payoff is None else (max_payoff / certificate_price - 1.0) * 100.0,
    )


def payoff_at_maturity(
    inputs: BonusCertificateInputs,
    terminal_underlying: float,
    barrier_breached: bool,
) -> float:
    inputs.validate()
    if barrier_breached:
        payoff = terminal_underlying
    else:
        payoff = max(terminal_underlying, inputs.bonus_level)
    if inputs.cap is not None:
        payoff = min(payoff, inputs.cap)
    return payoff / inputs.parity
