from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DiscountCertificateInputs:
    underlying: float
    cap: float
    maturity_years: float
    volatility: float
    rate: float
    dividend_yield: float
    parity: float = 1.0

    def validate(self) -> None:
        if self.underlying <= 0:
            raise ValueError("Underlying must be strictly positive.")
        if self.cap <= 0:
            raise ValueError("Cap must be strictly positive.")
        if self.maturity_years <= 0:
            raise ValueError("Maturity must be strictly positive.")
        if self.volatility < 0:
            raise ValueError("Volatility cannot be negative.")
        if self.parity <= 0:
            raise ValueError("Parity must be strictly positive.")


@dataclass(frozen=True)
class DiscountCertificateOutputs:
    underlying_pv: float
    short_call_value: float
    certificate_price: float
    discount_pct: float
    max_return_pct: float
    max_payoff: float
    breakeven: float
    sideways_return_pct: float


def _call_price(inputs: DiscountCertificateInputs) -> float:
    if inputs.volatility == 0:
        discounted_spot = inputs.underlying * math.exp(-inputs.dividend_yield * inputs.maturity_years)
        discounted_strike = inputs.cap * math.exp(-inputs.rate * inputs.maturity_years)
        return max(discounted_spot - discounted_strike, 0.0)

    vol_sqrt_t = inputs.volatility * math.sqrt(inputs.maturity_years)
    d1 = (
        math.log(inputs.underlying / inputs.cap)
        + (inputs.rate - inputs.dividend_yield + 0.5 * inputs.volatility * inputs.volatility) * inputs.maturity_years
    ) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    norm_cdf = lambda x: 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    return (
        inputs.underlying
        * math.exp(-inputs.dividend_yield * inputs.maturity_years)
        * norm_cdf(d1)
        - inputs.cap
        * math.exp(-inputs.rate * inputs.maturity_years)
        * norm_cdf(d2)
    )


def price_discount_certificate(inputs: DiscountCertificateInputs) -> DiscountCertificateOutputs:
    inputs.validate()

    underlying_pv = inputs.underlying * math.exp(-inputs.dividend_yield * inputs.maturity_years) / inputs.parity
    call_value = _call_price(inputs) / inputs.parity
    short_call_value = -call_value
    certificate_price = underlying_pv + short_call_value
    spot_reference = inputs.underlying / inputs.parity
    max_payoff = inputs.cap / inputs.parity

    discount_pct = (1.0 - certificate_price / spot_reference) * 100.0
    max_return_pct = (max_payoff / certificate_price - 1.0) * 100.0
    sideways_return_pct = (inputs.underlying / inputs.parity / certificate_price - 1.0) * 100.0

    return DiscountCertificateOutputs(
        underlying_pv=underlying_pv,
        short_call_value=short_call_value,
        certificate_price=certificate_price,
        discount_pct=discount_pct,
        max_return_pct=max_return_pct,
        max_payoff=max_payoff,
        breakeven=certificate_price,
        sideways_return_pct=sideways_return_pct,
    )


def payoff_at_maturity(inputs: DiscountCertificateInputs, terminal_underlying: float) -> float:
    inputs.validate()
    return min(terminal_underlying, inputs.cap) / inputs.parity
