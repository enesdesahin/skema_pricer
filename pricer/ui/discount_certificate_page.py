from __future__ import annotations

from html import escape
from textwrap import dedent

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pricer.engines.discount_certificate import (
    DiscountCertificateInputs,
    payoff_at_maturity,
    price_discount_certificate,
)


def _render_section_header(title: str) -> None:
    st.markdown(
        dedent(
            f"""
            <div style="margin-top: 8px; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #e6e6e6; font-size: 13px; font-weight: 700; letter-spacing: 0.08em; color: #6f7278; text-transform: uppercase;">{escape(title)}</div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def _format_number(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def _format_pct(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}%"


def _render_replication_line(inputs: DiscountCertificateInputs) -> None:
    outputs = price_discount_certificate(inputs)
    st.markdown(
        (
            f"**DC Price = PV(Underlying) - Call(K=Cap)** = "
            f"`{outputs.underlying_pv:.4f}` - `{abs(outputs.short_call_value):.4f}` = "
            f"`{outputs.certificate_price:.4f}` per certificate"
        )
    )


def _build_payoff_chart(inputs: DiscountCertificateInputs) -> go.Figure:
    low = inputs.underlying * 0.5
    high = max(inputs.underlying * 1.5, inputs.cap * 1.25)
    points = 80
    spots = [low + (high - low) * i / (points - 1) for i in range(points)]
    certificate_payoff = [payoff_at_maturity(inputs, spot) for spot in spots]
    stock_payoff = [spot / inputs.parity for spot in spots]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=spots, y=stock_payoff, mode="lines", name="Stock Payoff", line=dict(color="#a7b3c5", width=2.5)))
    fig.add_trace(go.Scatter(x=spots, y=certificate_payoff, mode="lines", name="Certificate Payoff", line=dict(color="#3f7edb", width=2.5)))
    fig.add_hline(
        y=inputs.cap / inputs.parity,
        line_dash="dash",
        line_color="#e54842",
        annotation_text=f"Cap ({inputs.cap / inputs.parity:.1f})",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#e54842",
    )
    fig.update_layout(
        title=dict(text="<b>Payoff at Maturity</b>", font=dict(size=14)),
        xaxis=dict(title="Underlying at Expiry", gridcolor="#eef1f4"),
        yaxis=dict(title="", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _build_pnl_chart(inputs: DiscountCertificateInputs) -> go.Figure:
    outputs = price_discount_certificate(inputs)
    low = inputs.underlying * 0.5
    high = max(inputs.underlying * 1.5, inputs.cap * 1.25)
    points = 80
    spots = [low + (high - low) * i / (points - 1) for i in range(points)]
    stock_pnl = [spot / inputs.parity - inputs.underlying / inputs.parity for spot in spots]
    certificate_pnl = [payoff_at_maturity(inputs, spot) - outputs.certificate_price for spot in spots]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=spots, y=stock_pnl, mode="lines", name="Stock P&L", line=dict(color="#a7b3c5", width=2.5)))
    fig.add_trace(go.Scatter(x=spots, y=certificate_pnl, mode="lines", name="Certificate P&L", line=dict(color="#3f7edb", width=2.5)))
    fig.add_hline(y=0, line_color="#dce3ec", line_width=1)
    fig.add_vline(
        x=outputs.breakeven * inputs.parity,
        line_dash="dash",
        line_color="#54a66b",
        annotation_text=f"BE ({outputs.breakeven:.1f})",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#54a66b",
    )
    fig.update_layout(
        title=dict(text="<b>Profit & Loss at Maturity</b>", font=dict(size=14)),
        xaxis=dict(title="Underlying at Expiry", gridcolor="#eef1f4"),
        yaxis=dict(title="", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _build_vol_sensitivity_chart(inputs: DiscountCertificateInputs) -> go.Figure:
    vols = [5.0 + (60.0 - 5.0) * i / 39 for i in range(40)]
    prices = []
    discounts = []
    for vol in vols:
        outputs = price_discount_certificate(DiscountCertificateInputs(**{**inputs.__dict__, "volatility": vol / 100.0}))
        prices.append(outputs.certificate_price)
        discounts.append(outputs.discount_pct)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=vols, y=prices, mode="lines", name="DC Price", line=dict(color="#3f7edb", width=2.5)))
    fig.add_trace(
        go.Scatter(
            x=vols,
            y=discounts,
            mode="lines",
            name="Discount %",
            line=dict(color="#e54842", width=2.2, dash="dot"),
            yaxis="y2",
        )
    )
    fig.update_layout(
        title=dict(text="<b>DC Price & Discount vs Volatility</b>", font=dict(size=14)),
        xaxis=dict(title="Volatility (%)", gridcolor="#eef1f4"),
        yaxis=dict(title="DC Price", gridcolor="#eef1f4"),
        yaxis2=dict(title="Discount %", overlaying="y", side="right"),
        margin=dict(l=0, r=0, t=42, b=0),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _build_cap_sensitivity_chart(inputs: DiscountCertificateInputs) -> go.Figure:
    cap_min = inputs.underlying * 0.7
    cap_max = inputs.underlying * 1.3
    caps = [cap_min + (cap_max - cap_min) * i / 39 for i in range(40)]
    prices = []
    max_returns = []
    for cap in caps:
        outputs = price_discount_certificate(DiscountCertificateInputs(**{**inputs.__dict__, "cap": cap}))
        prices.append(outputs.certificate_price)
        max_returns.append(outputs.max_return_pct)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=caps, y=prices, mode="lines", name="DC Price", line=dict(color="#3f7edb", width=2.5)))
    fig.add_trace(
        go.Scatter(
            x=caps,
            y=max_returns,
            mode="lines",
            name="Max Return %",
            line=dict(color="#54a66b", width=2.2, dash="dot"),
            yaxis="y2",
        )
    )
    fig.add_vline(x=inputs.cap, line_dash="dash", line_color="#aebbd0")
    fig.update_layout(
        title=dict(text="<b>DC Price & Max Return vs Cap Level</b>", font=dict(size=14)),
        xaxis=dict(title="Cap Level", gridcolor="#eef1f4"),
        yaxis=dict(title="DC Price", gridcolor="#eef1f4"),
        yaxis2=dict(title="Max Return %", overlaying="y", side="right"),
        margin=dict(l=0, r=0, t=42, b=0),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _render_discount_certificate_qa() -> None:
    _render_section_header("Trading Q&A - Discount Certificates")
    st.caption(
        "Replication: DC = Long Stock - Call(K=Cap). Client buys the cert: Long S, Short Call. "
        "Trader sells the cert and hedges: Short S, Long Call."
    )

    with st.expander("Question n°1 - As a client, are you long or short volatility ?", expanded=False):
        st.markdown("**Short volatility.**")
        st.markdown(
            "The client is short a call with strike equal to the cap. When volatility rises, that call becomes more expensive. "
            "The client's short call loses value, so the certificate drops in value."
        )
        st.markdown("The client wants volatility to stay low or decrease.")
        st.markdown(
            "The trader is the opposite through the hedge: long volatility via the long call. "
            "If volatility rises, the trader's long call gains value, offsetting the certificate liability."
        )

    with st.expander("Question n°2 - How is a Discount Certificate different from a covered call ?", expanded=False):
        st.markdown("**Economically, it is identical for the client.**")
        st.latex(r"\text{Covered Call} = \text{Long Stock} - \text{Call}(K)")
        st.latex(r"\text{Discount Certificate} = \text{Long Stock} - \text{Call}(K=\text{Cap})")
        st.markdown(
            "The difference is packaging. The certificate is a single security, while the covered call is two separate legs."
        )
        st.markdown(
            "For the trader, selling a Discount Certificate is like buying back a covered call from the client. "
            "The trader ends up long call and short stock after hedging."
        )

    with st.expander("Question n°3 - As a trader, where are you gamma long or gamma short ?", expanded=False):
        st.markdown("**The trader is gamma long from the long call in the hedge.**")
        st.markdown(
            "The client is gamma short because the client is short the cap call. "
            "The trader, having sold the certificate and hedged with a long call, has positive gamma."
        )
        st.markdown("Gamma is largest near the cap strike and near expiry.")
        st.markdown("The trader pays theta for this gamma. This is the classic long-gamma / short-theta profile.")

    with st.expander("Question n°4 - When does holding the stock outperform the Discount Certificate ?", expanded=False):
        st.markdown("**When the stock rallies well above the cap.**")
        st.markdown(
            "The certificate payoff is capped at the cap, so any upside beyond that is lost. "
            "Below the cap, the certificate outperforms because the client bought at a discount."
        )
        st.markdown(
            "For the trader, a rally above the cap is favorable because the long call in the hedge pays off "
            "and the certificate liability is capped. The trader's risk is a drop in the stock due to the short stock hedge."
        )

    with st.expander("Question n°5 - What is the client's delta ? What is the trader's delta ?", expanded=False):
        st.markdown("**Client delta: between 0 and 1. Trader delta: between -1 and 0 before hedging.**")
        st.markdown(
            "Client: long stock (+1) minus short call delta. If the stock is well below the cap, the call is OTM, "
            "so client delta is close to 1. Near or above the cap, delta drops toward 0."
        )
        st.markdown(
            "Trader: short stock (-1) plus long call delta. The trader delta-hedges by buying shares."
        )
        st.markdown(
            "Near the cap at expiry, both client and trader face a delta discontinuity. "
            "This makes hedging expensive and creates pin risk."
        )

    with st.expander("Question n°6 - If vol is high, is it a good time for the client to buy ?", expanded=False):
        st.markdown("**Yes, high volatility is favorable for the client.**")
        st.markdown(
            "High volatility inflates the call premium. Since the client is effectively selling that call, "
            "the discount is larger, entry is cheaper, and max return is higher."
        )
        st.markdown(
            "For the trader, high volatility means the hedge call is expensive to buy, but the trader also receives "
            "a higher certificate price from the client."
        )
        st.markdown(
            "The net result depends on the trader's view of realized volatility versus implied volatility. "
            "If realized volatility is lower than implied, the trade can be profitable."
        )


def render_discount_certificate_page() -> None:
    with st.sidebar:
        st.markdown("### Parameters")

        underlying = st.number_input("Underlying", min_value=0.01, value=100.0, step=1.0, format="%.2f")
        cap = st.number_input("Cap", min_value=0.01, value=110.0, step=1.0, format="%.2f")

        maturity_col, volatility_col = st.columns(2)
        maturity_years = maturity_col.number_input("Maturity (years)", min_value=0.01, value=1.0, step=0.25, format="%.2f")
        volatility_pct = volatility_col.number_input("Volatility (%)", min_value=0.0, value=20.0, step=0.5, format="%.1f")

        rate_col, dividend_col = st.columns(2)
        rate_pct = rate_col.number_input("Risk-free rate (%)", value=5.0, step=0.25, format="%.2f")
        dividend_yield_pct = dividend_col.number_input("Dividend yield (%)", value=2.0, step=0.25, format="%.2f")

        parity = st.number_input("Parity", min_value=0.0001, value=1.0, step=0.1, format="%.4f")

    inputs = DiscountCertificateInputs(
        underlying=underlying,
        cap=cap,
        maturity_years=maturity_years,
        volatility=volatility_pct / 100.0,
        rate=rate_pct / 100.0,
        dividend_yield=dividend_yield_pct / 100.0,
        parity=parity,
    )

    try:
        outputs = price_discount_certificate(inputs)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    _render_section_header("Replication - Long Underlying + Short Call(K=Cap)")
    _render_replication_line(inputs)

    _render_section_header("Key Metrics")
    metrics_df = pd.DataFrame(
        {
            "Metric": ["Certificate price", "Discount", "Max return", "Max payoff", "Breakeven", "Sideways return"],
            "Value": [
                _format_number(outputs.certificate_price, 4),
                _format_pct(outputs.discount_pct, 2),
                _format_pct(outputs.max_return_pct, 2),
                _format_number(outputs.max_payoff, 2),
                _format_number(outputs.breakeven, 2),
                _format_pct(outputs.sideways_return_pct, 2),
            ],
            "Note": [
                "Current certificate value",
                "Discount versus spot/parity",
                "Return if payoff reaches the cap",
                "Maximum payoff at maturity",
                "Certificate cost per unit",
                "Return if spot finishes unchanged",
            ],
        }
    )
    st.dataframe(metrics_df, hide_index=True, use_container_width=True)

    with st.expander("Pricing Decomposition", expanded=True):
        decomposition_df = pd.DataFrame(
            {
                "Component": [
                    "Underlying PV (S x e^{-qT})",
                    "Short Call BS(S, K=Cap)",
                    "= Certificate Price (per unit)",
                    "Spot / Parity (reference)",
                ],
                "Value": [
                    f"{outputs.underlying_pv:.4f}",
                    f"{outputs.short_call_value:.4f}",
                    f"**{outputs.certificate_price:.4f}**",
                    f"{inputs.underlying / inputs.parity:.4f}",
                ],
            }
        )
        st.dataframe(decomposition_df, hide_index=True, use_container_width=True)

    _render_section_header("Payoff at Maturity - Stock vs Discount Certificate")
    payoff_cols = st.columns(2)
    with payoff_cols[0]:
        st.plotly_chart(_build_payoff_chart(inputs), use_container_width=True)
    with payoff_cols[1]:
        st.plotly_chart(_build_pnl_chart(inputs), use_container_width=True)

    _render_section_header("Sensitivity - Impact of Volatility & Cap Level")
    sensitivity_cols = st.columns(2)
    with sensitivity_cols[0]:
        st.plotly_chart(_build_vol_sensitivity_chart(inputs), use_container_width=True)
    with sensitivity_cols[1]:
        st.plotly_chart(_build_cap_sensitivity_chart(inputs), use_container_width=True)

    _render_discount_certificate_qa()
