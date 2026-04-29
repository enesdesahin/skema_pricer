from __future__ import annotations

from html import escape
from textwrap import dedent

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pricer.engines.turbo import (
    TurboInputs,
    build_spot_scenarios,
    calculate_turbo_drift,
    price_turbo,
    strike_after_days,
    turbo_price_at_spot,
)


TURBO_TYPE_OPTIONS = {"Long": "long", "Short": "short"}
DEFINE_BY_OPTIONS = ["Strike and barrier", "Target leverage"]


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


def _derive_levels_from_target_leverage(
    underlying: float,
    turbo_type: str,
    target_leverage: float,
    barrier_gap_pct: float,
) -> tuple[float, float]:
    if turbo_type == "long":
        strike = underlying - (underlying / target_leverage)
        barrier = strike * (1.0 + barrier_gap_pct / 100.0)
    else:
        strike = underlying + (underlying / target_leverage)
        barrier = strike * (1.0 - barrier_gap_pct / 100.0)
    return strike, barrier


def _build_drift_charts(inputs: TurboInputs, holding_days: int) -> tuple[go.Figure, go.Figure]:
    days = list(range(0, holding_days + 1))
    strikes = [strike_after_days(inputs, day) for day in days]
    prices = [turbo_price_at_spot(inputs, inputs.underlying, strike=strike) for strike in strikes]

    strike_fig = go.Figure()
    strike_fig.add_trace(
        go.Scatter(x=days, y=strikes, mode="lines", name="Strike", line=dict(color="#e54842", width=2.5))
    )
    strike_fig.add_hline(
        y=inputs.barrier,
        line_dash="dash",
        line_color="#aebbd0",
        annotation_text="Barrier",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#8b96a8",
    )
    strike_fig.update_layout(
        title=dict(text="<b>Strike Drift Over Time</b>", font=dict(size=14)),
        xaxis=dict(title="Days", gridcolor="#eef1f4"),
        yaxis=dict(title="", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    erosion_fig = go.Figure()
    erosion_fig.add_trace(
        go.Scatter(x=days, y=prices, mode="lines", name="Turbo price", line=dict(color="#3f7edb", width=2.5))
    )
    erosion_fig.update_layout(
        title=dict(text="<b>Turbo Price Erosion (Spot unchanged)</b>", font=dict(size=14)),
        xaxis=dict(title="Days", gridcolor="#eef1f4"),
        yaxis=dict(title="", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return strike_fig, erosion_fig


def _build_payoff_chart(inputs: TurboInputs) -> go.Figure:
    low = min(inputs.underlying, inputs.strike, inputs.barrier) * 0.7
    high = max(inputs.underlying, inputs.strike, inputs.barrier) * 1.2
    points = 80
    spots = [low + (high - low) * i / (points - 1) for i in range(points)]
    prices = [turbo_price_at_spot(inputs, spot) for spot in spots]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=spots,
            y=prices,
            mode="lines",
            name="Payoff",
            line=dict(color="#3f7edb", width=2.5),
        )
    )
    fig.add_vline(
        x=inputs.strike,
        line_dash="dash",
        line_color="#aebbd0",
        annotation_text=f"Strike ({inputs.strike:.1f})",
        annotation_position="bottom right",
        annotation_font_size=11,
        annotation_font_color="#697386",
    )
    fig.add_vline(
        x=inputs.barrier,
        line_dash="dash",
        line_color="#e54842",
        annotation_text=f"Barrier ({inputs.barrier:.1f})",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#e54842",
    )
    fig.add_vline(
        x=inputs.underlying,
        line_dash="dash",
        line_color="#54a66b",
        annotation_text=f"Spot ({inputs.underlying:.1f})",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#54a66b",
    )
    fig.update_layout(
        title=dict(text=f"<b>Turbo {inputs.turbo_type.title()} Payoff</b>", font=dict(size=14)),
        xaxis=dict(title="Underlying Spot", gridcolor="#eef1f4"),
        yaxis=dict(title="", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _scenario_dataframe(inputs: TurboInputs) -> pd.DataFrame:
    scenarios = build_spot_scenarios(inputs, points=25)
    return pd.DataFrame(
        {
            "Spot": [scenario.spot for scenario in scenarios],
            "Turbo Price": ["KO" if scenario.knocked_out else f"{scenario.turbo_price:.4f}" for scenario in scenarios],
            "Leverage": ["—" if scenario.leverage is None else f"{scenario.leverage:.1f}x" for scenario in scenarios],
            "Dist. Barrier": [f"{max(scenario.distance_to_barrier_pct, 0.0):.1f}%" for scenario in scenarios],
            "P&L / unit": [scenario.pnl_per_unit for scenario in scenarios],
        }
    )


def _render_turbo_interview_qa() -> None:
    _render_section_header("Trading Q&A - Turbo Certificates")
    st.caption("Turbo Long = Long Stock - PV(Strike). Knock-out at barrier. Delta is approximately 1 with leveraged exposure.")

    with st.expander("Question n°1 - I sold 1 000 Turbo Long with ratio 0.1. How many stocks do I need to buy to be hedged ?", expanded=False):
        st.markdown("**Buy 100 stocks.**")
        st.markdown("A Turbo Long has delta approximately 1 per unit, but the ratio converts turbo units into shares.")
        st.latex(r"1\,000 \times 0.1 = 100")
        st.markdown("You sold the Turbos, so you are short delta. To hedge, you buy 100 stocks.")

    with st.expander("Question n°2 - Same underlying, leverage 5 vs leverage 10. Which Turbo is cheaper ?", expanded=False):
        st.markdown("**The leverage 10 Turbo is cheaper.**")
        st.markdown(
            "Higher leverage means the barrier is closer to spot and the probability of knock-out is higher. "
            "The client takes more risk, so the Turbo costs less."
        )
        st.latex(r"\text{Turbo Price} \approx (S - K) \times \text{Ratio}")
        st.markdown("Higher leverage means the strike is closer to spot, so S - K is smaller.")

    with st.expander("Question n°3 - Barrier distance 1% vs 10%. Which Turbo is more expensive ?", expanded=False):
        st.markdown("**The 10% barrier-distance Turbo is more expensive.**")
        st.markdown(
            "A 10% barrier distance means the barrier is further from spot. The Turbo is more protected, "
            "more in-the-money, and less likely to knock out."
        )
        st.markdown("A 1% barrier distance means the barrier is very close to spot, so KO probability is high and the Turbo is cheap.")

    with st.expander("Question n°4 - For a Turbo Long, do we increase or decrease the strike and barrier every day ? Why ?", expanded=False):
        st.markdown("**Increase them every day.**")
        st.markdown(
            "The issuer hedges by holding stock. To finance this stock position, the issuer borrows cash. "
            "That financing cost is passed on to the client."
        )
        st.latex(r"\Delta K = K \times r \times \frac{1}{365}")
        st.markdown(
            "The barrier moves up with the strike. This daily funding adjustment makes the client pay for the carry "
            "of the hedge through a slowly rising strike."
        )

    with st.expander("Question n°5 - If a Turbo Long gets knocked out, what is the residual value ?", expanded=False):
        st.markdown("**Residual value = (S - K) x Ratio x FX.**")
        st.latex(r"\text{Residual Value} = (S - K) \times \text{Ratio} \times \text{FX}")
        st.markdown(
            "When the barrier is breached, the Turbo is terminated. For a Turbo Long, the barrier is usually above the strike, "
            "so there can still be intrinsic value left."
        )
        st.markdown(
            "S is the spot at knock-out, approximately the barrier level. K is the strike, ratio is the conversion ratio, "
            "and FX is the currency adjustment if needed."
        )
        st.markdown("Residual value can be zero if the stock gaps through both the barrier and the strike.")

    with st.expander("Question n°6 - A Turbo Long with 10 000 lots gets knocked out. What must the trader do ?", expanded=False):
        st.markdown("**Sell all the stocks held against this Turbo.**")
        st.markdown(
            "The issuer was hedged by holding the underlying shares. When the Turbo knocks out, the product is dead, "
            "so there is no more delta exposure to hedge."
        )
        st.latex(r"\text{Shares to sell} = 10\,000 \times \text{Ratio}")
        st.markdown(
            "This must be done quickly, but the stock is already falling because it hit the barrier. "
            "Selling into that move can add further pressure."
        )


def render_turbo_page() -> None:
    with st.sidebar:
        st.markdown("### Parameters")

        turbo_type_label = st.selectbox("Type", options=list(TURBO_TYPE_OPTIONS), index=0)
        turbo_type = TURBO_TYPE_OPTIONS[turbo_type_label]
        underlying = st.number_input("Underlying", min_value=0.01, value=100.0, step=1.0, format="%.2f")

        define_by = st.selectbox("Define by", options=DEFINE_BY_OPTIONS, index=0)

        if define_by == "Strike and barrier":
            strike = st.number_input("Strike / Financing", min_value=0.01, value=80.0, step=1.0, format="%.2f")
            default_barrier = 82.0 if turbo_type == "long" else 118.0
            barrier = st.number_input("Knock-out barrier", min_value=0.01, value=default_barrier, step=1.0, format="%.2f")
            target_leverage = None
            barrier_gap_pct = None
        else:
            target_leverage = st.number_input("Target leverage", min_value=0.01, value=5.0, step=0.1, format="%.1f")
            barrier_gap_label = "Barrier gap above K (%)" if turbo_type == "long" else "Barrier gap below K (%)"
            barrier_gap_pct = st.number_input(barrier_gap_label, min_value=0.0, value=2.0, step=0.1, format="%.1f")
            strike, barrier = _derive_levels_from_target_leverage(
                underlying=underlying,
                turbo_type=turbo_type,
                target_leverage=target_leverage,
                barrier_gap_pct=barrier_gap_pct,
            )
            st.caption(f"-> K = {strike:,.2f} | B = {barrier:,.2f}")

        parity_col, financing_col = st.columns(2)
        parity = parity_col.number_input("Parity", min_value=0.0001, value=10.0, step=0.1, format="%.4f")
        financing_pct = financing_col.number_input("Financing (%)", value=2.0, step=0.25, format="%.2f")

        st.caption("Position")
        lots = st.number_input("Lots (# turbos)", min_value=0.01, value=100.0, step=1.0, format="%.0f")

    inputs = TurboInputs(
        turbo_type=turbo_type,
        underlying=underlying,
        strike=strike,
        barrier=barrier,
        parity=parity,
        financing_rate=financing_pct / 100.0,
        lots=lots,
    )

    try:
        outputs = price_turbo(inputs)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    _render_section_header("Turbo Open-End Pricing")
    pricing_df = pd.DataFrame(
        {
            "Metric": ["Turbo price", "Leverage", "Distance to barrier", "Daily funding cost"],
            "Value": [
                _format_number(outputs.turbo_price, 4),
                f"{outputs.leverage:.1f}x",
                _format_pct(outputs.distance_to_barrier_pct, 2),
                _format_number(outputs.daily_funding_cost, 4),
            ],
            "Note": ["Current certificate price", "Underlying exposure / invested cash", "Distance before knock-out", "Daily strike drift cost"],
        }
    )
    st.dataframe(pricing_df, hide_index=True, use_container_width=True)

    _render_section_header("Position Exposure")
    exposure_df = pd.DataFrame(
        {
            "Metric": ["Initial Δ cash (investment)", "Leveraged Δ cash (exposure)", "Equivalent underlying"],
            "Value": [
                _format_number(outputs.initial_delta_cash, 2),
                _format_number(outputs.leveraged_delta_cash, 2),
                f"{outputs.equivalent_underlying:.1f} units",
            ],
            "Note": ["Cash invested in the turbo", "Underlying exposure created", "Equivalent number of underlying units"],
        }
    )
    st.dataframe(exposure_df, hide_index=True, use_container_width=True)

    _render_section_header("Financing Cost Simulation - Strike Drift Over Time")
    holding_days = st.slider("Holding period (days)", min_value=0, max_value=365, value=30, step=1)
    drift = calculate_turbo_drift(inputs, holding_days)

    drift_df = pd.DataFrame(
        {
            "Metric": ["K today", f"K after {holding_days}D", "Turbo price (drifted)", "Value erosion"],
            "Value": [
                _format_number(drift.strike_today, 2),
                _format_number(drift.strike_after, 4),
                _format_number(drift.turbo_price_drifted, 4),
                _format_number(abs(drift.value_erosion), 4),
            ],
            "Change": ["", f"{drift.strike_drift:+.4f}", "", f"{drift.value_erosion:+.4f}"],
        }
    )
    st.dataframe(drift_df, hide_index=True, use_container_width=True)

    drift_fig, erosion_fig = _build_drift_charts(inputs, holding_days)
    drift_chart_cols = st.columns(2)
    with drift_chart_cols[0]:
        st.plotly_chart(drift_fig, use_container_width=True)
    with drift_chart_cols[1]:
        st.plotly_chart(erosion_fig, use_container_width=True)

    _render_section_header("Payoff at Current Time")
    st.plotly_chart(_build_payoff_chart(inputs), use_container_width=True)

    with st.expander("Turbo Sensitivity Table - Spot Scenarios", expanded=True):
        scenario_df = _scenario_dataframe(inputs)
        st.dataframe(
            scenario_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Spot": st.column_config.NumberColumn("Spot", format="%.2f"),
                "Turbo Price": st.column_config.TextColumn("Turbo Price"),
                "Leverage": st.column_config.TextColumn("Leverage"),
                "Dist. Barrier": st.column_config.TextColumn("Dist. Barrier"),
                "P&L / unit": st.column_config.NumberColumn("P&L / unit", format="%.4f"),
            },
        )

    _render_turbo_interview_qa()
