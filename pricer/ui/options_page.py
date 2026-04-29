from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from html import escape
from textwrap import dedent

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pricer.engines.options import (
    OptionInputs,
    analyze_american_option,
    calculate_gamma_pnl,
    calculate_trading_shortcuts,
    price_option,
    quick_calc_gamma_theta_bill,
)

POSITION_LABELS = {
    "Long": "long",
    "Short": "short",
}

OPTION_TYPE_LABELS = {
    "Call": "call",
    "Put": "put",
}


def _render_section_header(title: str) -> None:
    header_html = dedent(
        f"""
        <div style="margin-top: 8px; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #e6e6e6; font-size: 13px; font-weight: 700; letter-spacing: 0.08em; color: #6f7278; text-transform: uppercase;">{escape(title)}</div>
        """
    ).strip()
    st.markdown(header_html, unsafe_allow_html=True)


def _format_number(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def _format_signed_shares(value: float) -> str:
    return f"{value:,.2f}"


def _format_percent(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}%"


def _render_pill(text: str, background: str = "#e6f4ea", color: str = "#1e8e3e") -> None:
    st.markdown(
        dedent(
            f"""
            <span style="
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                background: {background};
                color: {color};
                font-size: 12px;
                font-weight: 600;
            ">{escape(text)}</span>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def _render_payoff_charts(inputs: OptionInputs, outputs) -> None:
    _render_section_header("Payoff at Maturity")

    spot_min = max(0.01, inputs.strike * 0.5)
    spot_max = inputs.strike * 1.5
    points = 80
    spots = [spot_min + (spot_max - spot_min) * i / (points - 1) for i in range(points)]

    unit_payoffs = []
    position_pnls = []
    stock_pnls = []
    for terminal_spot in spots:
        if inputs.option_type == "call":
            unit_payoff = max(terminal_spot - inputs.strike, 0.0)
        else:
            unit_payoff = max(inputs.strike - terminal_spot, 0.0)
        position_payoff = inputs.position_sign * unit_payoff * inputs.quantity
        unit_payoffs.append(unit_payoff)
        position_pnls.append(position_payoff - outputs.signed_position_value)
        stock_pnls.append((terminal_spot - inputs.spot) * inputs.quantity)

    payoff_cols = st.columns(2)

    with payoff_cols[0]:
        fig_payoff = go.Figure()
        fig_payoff.add_trace(
            go.Scatter(
                x=spots,
                y=unit_payoffs,
                mode="lines",
                name=f"{inputs.option_type.title()} payoff",
                line=dict(color="#3f7edb", width=2.5),
            )
        )
        fig_payoff.add_vline(
            x=inputs.strike,
            line_dash="dash",
            line_color="#aebbd0",
            annotation_text=f"Strike ({inputs.strike:g})",
            annotation_position="top right",
            annotation_font_size=11,
            annotation_font_color="#8b96a8",
        )
        fig_payoff.add_vline(
            x=inputs.spot,
            line_dash="dot",
            line_color="#54a66b",
            annotation_text=f"Spot ({inputs.spot:g})",
            annotation_position="top right",
            annotation_font_size=11,
            annotation_font_color="#54a66b",
        )
        fig_payoff.update_layout(
            title=dict(text="<b>Unit Payoff</b>", font=dict(size=14)),
            xaxis=dict(title="Underlying at Expiry", gridcolor="#eef1f4"),
            yaxis=dict(title="Payoff", gridcolor="#eef1f4"),
            margin=dict(l=0, r=0, t=42, b=0),
            hovermode="x unified",
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        st.plotly_chart(fig_payoff, use_container_width=True)

    with payoff_cols[1]:
        fig_pnl = go.Figure()
        fig_pnl.add_trace(
            go.Scatter(
                x=spots,
                y=stock_pnls,
                mode="lines",
                name="Stock P&L",
                line=dict(color="#a7b3c5", width=2, dash="dash"),
            )
        )
        fig_pnl.add_trace(
            go.Scatter(
                x=spots,
                y=position_pnls,
                mode="lines",
                name="Option P&L",
                line=dict(color="#3f7edb", width=2.5),
            )
        )
        fig_pnl.add_hline(y=0, line_color="#dce3ec", line_width=1)
        fig_pnl.add_vline(
            x=inputs.strike,
            line_dash="dash",
            line_color="#aebbd0",
            annotation_text="K",
            annotation_position="bottom",
            annotation_font_size=11,
            annotation_font_color="#8b96a8",
        )
        fig_pnl.update_layout(
            title=dict(text="<b>Position P&L</b>", font=dict(size=14)),
            xaxis=dict(title="Underlying at Expiry", gridcolor="#eef1f4"),
            yaxis=dict(title="P&L", gridcolor="#eef1f4"),
            margin=dict(l=0, r=0, t=42, b=0),
            legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
            hovermode="x unified",
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        st.plotly_chart(fig_pnl, use_container_width=True)


def _render_charts(inputs: OptionInputs) -> None:
    _render_section_header("Market Sensitivities")

    y_metrics = {
        "Price": "signed_position_value",
        "Cash Delta": "signed_cash_delta",
        "Cash Gamma": "signed_cash_gamma_per_1pct",
        "Cash Theta": "signed_theta_per_day",
        "Cash Vega": "signed_cash_vega_per_1pct",
        "Cash Charm": "signed_cash_charm_per_day",
        "Cash Vanna": "signed_cash_vanna_per_1pct",
        "Cash Rho": "signed_cash_rho_per_1pct",
    }

    col1, col2 = st.columns(2)

    with col1:
        st.write("vs Spot")
        left_y_metric = st.selectbox("Price", options=list(y_metrics.keys()), index=0, key="left_y_metric", label_visibility="collapsed")
        
        spot_min = max(0.01, inputs.strike * 0.7)
        spot_max = inputs.strike * 1.3
        num_points = 50
        spot_range = [spot_min + (spot_max - spot_min) * i / (num_points - 1) for i in range(num_points)]
        
        call_y = []
        put_y = []
        for s in spot_range:
            c_in = replace(inputs, spot=s, option_type="call")
            p_in = replace(inputs, spot=s, option_type="put")
            call_y.append(getattr(price_option(c_in), y_metrics[left_y_metric]))
            put_y.append(getattr(price_option(p_in), y_metrics[left_y_metric]))

        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=spot_range, y=call_y, mode='lines', name='Call', line=dict(color='#4285F4')))
        fig1.add_trace(go.Scatter(x=spot_range, y=put_y, mode='lines', name='Put', line=dict(color='#EA4335')))
        
        fig1.add_vline(x=inputs.strike, line_dash="dash", line_color="#b6c2d1", annotation_text="ATM", annotation_position="top right", annotation_font_size=10, annotation_font_color="#b6c2d1")
        
        fig1.update_layout(
            title=dict(text=f"<b>{left_y_metric} vs Spot</b>", font=dict(size=14)),
            xaxis=dict(title="Spot", gridcolor='#f0f2f6'),
            yaxis=dict(gridcolor='#f0f2f6'),
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            hovermode="x unified",
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        col2_a, col2_b = st.columns([1, 1])
        with col2_a:
            st.write("Chart")
            right_y_metric = st.selectbox("Price", options=list(y_metrics.keys()), index=0, key="right_y_metric_2", label_visibility="collapsed")
        with col2_b:
            st.write("vs")
            right_x_metric = st.selectbox("Vol", options=["Vol", "Maturity"], index=0, key="right_x_metric", label_visibility="collapsed")

        call_y_2 = []
        put_y_2 = []
        x_range_2 = []
        x_title_2 = ""
        
        if right_x_metric == "Vol":
            vol_min = 5.0
            vol_max = 60.0
            x_range_2 = [vol_min + (vol_max - vol_min) * i / (num_points - 1) for i in range(num_points)]
            for v in x_range_2:
                c_in = replace(inputs, volatility=v / 100.0, option_type="call")
                p_in = replace(inputs, volatility=v / 100.0, option_type="put")
                call_y_2.append(getattr(price_option(c_in), y_metrics[right_y_metric]))
                put_y_2.append(getattr(price_option(p_in), y_metrics[right_y_metric]))
            x_title_2 = "Vol (%)"
        else:
            days_range = [int(1 + (365 * 2 - 1) * i / (num_points - 1)) for i in range(num_points)]
            x_range_2 = [inputs.valuation_date + timedelta(days=d) for d in days_range]
            for d in x_range_2:
                c_in = replace(inputs, maturity_date=d, option_type="call")
                p_in = replace(inputs, maturity_date=d, option_type="put")
                call_y_2.append(getattr(price_option(c_in), y_metrics[right_y_metric]))
                put_y_2.append(getattr(price_option(p_in), y_metrics[right_y_metric]))
            x_title_2 = "Maturity Date"

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=x_range_2, y=call_y_2, mode='lines', name='Call', line=dict(color='#4285F4')))
        fig2.add_trace(go.Scatter(x=x_range_2, y=put_y_2, mode='lines', name='Put', line=dict(color='#EA4335')))
        
        fig2.update_layout(
            title=dict(text=f"<b>{right_y_metric} vs {right_x_metric}</b>", font=dict(size=14)),
            xaxis=dict(title=x_title_2, gridcolor='#f0f2f6'),
            yaxis=dict(gridcolor='#f0f2f6'),
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            hovermode="x unified",
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        st.plotly_chart(fig2, use_container_width=True)

def _render_unit_greeks_sensitivity(inputs: OptionInputs) -> None:
    st.caption("Shape analysis for the unit Greeks. These charts are useful when explaining how moneyness, time, and volatility change the hedge.")

    vols = [0.10, 0.20, 0.40]
    vol_colors = ['#4285F4', '#a166df', '#EA4335']

    k = inputs.strike
    strikes_spot = [k * 0.9, k * 1.0, k * 1.1]
    str_colors = ['#EA4335', '#4285F4', '#34A853']
    if inputs.option_type == "call":
        str_labels = [f"OTM (S={strikes_spot[0]:g})", f"ATM (S={strikes_spot[1]:g})", f"ITM (S={strikes_spot[2]:g})"]
    else:
        str_labels = [f"ITM (S={strikes_spot[0]:g})", f"ATM (S={strikes_spot[1]:g})", f"OTM (S={strikes_spot[2]:g})"]

    num_points = 50
    spot_min = k * 0.7
    spot_max = k * 1.3
    spot_range = [spot_min + (spot_max - spot_min) * i / (num_points - 1) for i in range(num_points)]

    ttm_range = [0.01 + (1.0 - 0.01) * i / (num_points - 1) for i in range(num_points)]
    val_date = inputs.valuation_date
    date_range = [val_date + timedelta(days=int(t * 365.25)) for t in ttm_range]

    metrics = [
        ("Delta", "unit_delta"),
        ("Gamma", "unit_gamma"),
        ("Vega", "unit_vega")
    ]

    for i, (metric_name, metric_attr) in enumerate(metrics):
        col1, col2 = st.columns(2)

        with col1:
            fig1 = go.Figure()
            for vol, color in zip(vols, vol_colors):
                y_vals = []
                for s in spot_range:
                    mod_in = replace(inputs, spot=s, volatility=vol)
                    y_vals.append(getattr(price_option(mod_in), metric_attr))
                fig1.add_trace(go.Scatter(x=spot_range, y=y_vals, mode='lines', name=f"σ = {int(vol*100)}%", line=dict(color=color)))
            
            fig1.add_vline(x=k, line_dash="dash", line_color="#b6c2d1", annotation_text="ATM", annotation_position="top right", annotation_font_size=10, annotation_font_color="#b6c2d1")
            
            fig1.update_layout(
                title=dict(text=f"<b>{metric_name} vs Spot — by Volatility</b>", font=dict(size=14)),
                xaxis=dict(title="Spot" if i == 2 else "", gridcolor='#f0f2f6'),
                yaxis=dict(gridcolor='#f0f2f6'),
                margin=dict(l=0, r=0, t=40, b=20 if i == 2 else 0),
                legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
                hovermode="x unified",
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = go.Figure()
            for s, label, color in zip(strikes_spot, str_labels, str_colors):
                y_vals = []
                for d in date_range:
                    mod_in = replace(inputs, spot=s, maturity_date=d)
                    y_vals.append(getattr(price_option(mod_in), metric_attr))
                fig2.add_trace(go.Scatter(x=ttm_range, y=y_vals, mode='lines', name=label, line=dict(color=color)))
            
            fig2.update_layout(
                title=dict(text=f"<b>{metric_name} vs Time — by Moneyness</b>", font=dict(size=14)),
                xaxis=dict(title="Time to Maturity (y)" if i == 2 else "", gridcolor='#f0f2f6'),
                yaxis=dict(gridcolor='#f0f2f6'),
                margin=dict(l=0, r=0, t=40, b=20 if i == 2 else 0),
                legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
                hovermode="x unified",
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            st.plotly_chart(fig2, use_container_width=True)


def _render_forwards_options_interview_qa() -> None:
    _render_section_header("Interview Q&A — Forwards & Options")

    with st.expander("Question n°1 - Is the forward the market's prediction of the future spot price ?", expanded=False):
        st.markdown("**No.** A forward is a replication price, not a forecast.")
        st.markdown("If you want to own the stock in 6 months, you can either:")
        st.markdown("1. Buy it in 6 months, at an unknown future price.")
        st.markdown("2. Buy it today, finance the purchase, and carry the stock until maturity.")
        st.markdown("That replication gives the no-arbitrage forward price:")
        st.latex(r"F = S e^{(r-q)T}")
        st.markdown(
            "The forward therefore reflects financing costs minus the benefit of dividends. "
            "It is an arbitrage-enforced price, not a view on where spot will trade."
        )

    with st.expander("Question n°2 - Why can a 6-month forward trade below spot ?", expanded=False):
        st.markdown("A forward can trade at a discount to spot when carry is negative.")
        st.latex(r"F = S e^{(r-q-\mathrm{repo})T}")
        st.markdown(
            "If the dividend yield and repo benefit together are larger than the financing cost, "
            "then the exponent becomes negative and the forward falls below spot."
        )
        st.latex(r"\text{If } q + \mathrm{repo} > r,\ \text{then } F < S")

    with st.expander("Question n°3 - What happens to call prices if expected dividends are cut while spot is unchanged ?", expanded=False):
        st.markdown("**Call prices increase.**")
        st.markdown(
            "A lower dividend yield increases the forward price because there is less dividend drag in the carry. "
            "Calls benefit from a higher forward, while puts become cheaper."
        )

    with st.expander("Question n°4 - Spot = 100, r = 5%, no dividends. The 1Y forward trades at 110. How do you arbitrage ?", expanded=False):
        st.markdown("This is a **cash-and-carry arbitrage**.")
        st.markdown("The fair 1-year forward is:")
        st.latex(r"F^* = 100 \times (1 + 5\%) = 105")
        st.markdown("If the market forward is 110, it is overpriced. The arbitrage is:")
        st.markdown("1. Borrow 100 today at 5%.")
        st.markdown("2. Buy the stock at 100.")
        st.markdown("3. Sell the 1-year forward at 110.")
        st.markdown("At maturity, deliver the stock into the forward, receive 110, repay 105, and lock in a risk-free profit of 5.")

    with st.expander("Question n°5 - A forward holder observes an expected dividend payment. Spot drops by the dividend amount. Does the forward price change ?", expanded=False):
        st.markdown("**No, not if the dividend was fully expected.**")
        st.markdown(
            "When the stock goes ex-dividend, spot drops by the dividend amount. "
            "But the dividend drag in the carry also disappears. Those two effects offset each other."
        )
        st.markdown("So there is no new P&L from the dividend event itself if it was already priced in.")

    with st.expander("Question n°6 - What if the dividend is larger than expected ?", expanded=False):
        st.markdown("Then the forward price drops by the **unexpected** dividend component.")
        st.markdown("Example: the market priced a dividend of 5, but the company pays 6.")
        st.markdown("The extra 1 was not embedded in the original carry assumption, so the forward must adjust lower by about 1.")
        st.latex(r"\Delta F \approx -(D_{\mathrm{realized}} - D_{\mathrm{expected}})")

    with st.expander("Question n°7 - Which is cheaper: a 3M ATM straddle or a 1Y ATM call ?", expanded=False):
        st.markdown("Using standard ATM approximations, they are about the same in this example.")
        st.latex(r"\text{ATM straddle} \approx 0.8 \, S \sigma \sqrt{T}")
        st.latex(r"\text{ATM call} \approx 0.4 \, S \sigma \sqrt{T}")
        st.markdown(r"With $S=100$, $\sigma=20\%$:")
        st.latex(r"0.8 \times 100 \times 0.20 \times \sqrt{0.25} = 8")
        st.latex(r"0.4 \times 100 \times 0.20 \times \sqrt{1} = 8")
        st.markdown("So the 3M ATM straddle and the 1Y ATM call both cost about 8 in this rule-of-thumb setup.")

    with st.expander("Question n°8 - Which is more expensive: 1 call with strike 100, or 2 calls with strike 200 ?", expanded=False):
        st.markdown("**1 call with strike 100 is more expensive.**")
        st.markdown("A simple scenario table makes the intuition clear:")
        comparison_df = pd.DataFrame(
            {
                "Scenario": ["S_T = 100", "S_T = 200", "S_T = 300", "Average"],
                "1 × Call(K=100)": ["0", "100", "200", "100"],
                "1 × Call(K=200)": ["0", "0", "100", "33"],
                "2 × Call(K=200)": ["0", "0", "200", "66"],
            }
        )
        st.dataframe(comparison_df, hide_index=True, use_container_width=True)
        st.markdown(
            "The lower-strike call benefits from being in the money over a wider range of outcomes. "
            "That convexity makes 1 × Call(100) more valuable than 2 × Call(200)."
        )

    with st.expander("Question n°9 - If you are gamma long and delta hedged, which path makes more money: +3%, +3%, +3% or 0%, 0%, +9% ?", expanded=False):
        st.markdown("**The 0%, 0%, +9% path makes more money.**")
        st.markdown("Gamma P&L scales with the square of the move size:")
        st.latex(r"\mathrm{PnL}_{\Gamma} \propto \sum_t (\Delta S_t)^2")
        st.latex(r"3^2 + 3^2 + 3^2 = 27")
        st.latex(r"0^2 + 0^2 + 9^2 = 81")
        st.markdown(
            "Both paths add up to the same total move, but one large move produces much more gamma P&L than several small ones."
        )

    with st.expander("Question n°10 - In a worst-of product on Apple (200) and Nokia (5), Apple drops 20 and Nokia drops 1. Which is the worst-off component ?", expanded=False):
        st.markdown("**Nokia is the worst-off component.**")
        st.markdown("Worst-of payoffs depend on **relative performance**, not absolute currency moves.")
        st.latex(r"\frac{20}{200} = 10\% \quad \text{for Apple}")
        st.latex(r"\frac{1}{5} = 20\% \quad \text{for Nokia}")
        st.markdown("Nokia has the larger percentage loss, so it is the worst-off underlying.")


def _inject_streamlit_table_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stDataFrame"],
        div[data-testid="stDataFrame"] > div,
        div[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {
            border-radius: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_options_page() -> None:
    _inject_streamlit_table_css()

    with st.sidebar:
        st.markdown("### Parameters")

        valuation_date = date.today()
        default_maturity = date(valuation_date.year + 1, valuation_date.month, valuation_date.day)

        spot = st.number_input("Spot", min_value=0.01, value=100.0, step=1.0, format="%.2f")
        strike = st.number_input("Strike", min_value=0.01, value=100.0, step=1.0, format="%.2f")
        maturity_date = st.date_input("Maturity", value=default_maturity, min_value=valuation_date)

        st.caption(f"T = {(maturity_date - valuation_date).days / 365.25:.4f} y")

        rate_col, dividend_col = st.columns(2)
        rate_pct = rate_col.number_input("Risk-free rate (%)", value=5.0, step=0.25, format="%.2f")
        dividend_yield_pct = dividend_col.number_input("Dividend yield (%)", value=2.0, step=0.25, format="%.2f")

        repo_col, volatility_col = st.columns(2)
        repo_rate_pct = repo_col.number_input("Repo rate (%)", value=0.0, step=0.25, format="%.2f")
        volatility_pct = volatility_col.number_input("Volatility (%)", min_value=0.0, value=20.0, step=0.5, format="%.2f")

        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

        position_col, type_col = st.columns(2)
        position_label = position_col.selectbox("Position", options=list(POSITION_LABELS), index=0)
        option_type_label = type_col.selectbox("Type", options=list(OPTION_TYPE_LABELS), index=0)

        lots_col, multiplier_col = st.columns(2)
        lots = lots_col.number_input("Lots", min_value=0.01, value=1.0, step=1.0, format="%.2f")
        multiplier = multiplier_col.number_input("Multiplier", min_value=1.0, value=100.0, step=1.0, format="%.0f")

        tick_col, _ = st.columns(2)
        tick = tick_col.number_input("Tick", min_value=0.0001, value=0.01, step=0.0001, format="%.4f")

    inputs = OptionInputs(
        spot=spot,
        strike=strike,
        valuation_date=valuation_date,
        maturity_date=maturity_date,
        rate=rate_pct / 100.0,
        dividend_yield=dividend_yield_pct / 100.0,
        repo_rate=repo_rate_pct / 100.0,
        volatility=volatility_pct / 100.0,
        option_type=OPTION_TYPE_LABELS[option_type_label],
        position=POSITION_LABELS[position_label],
        lots=lots,
        multiplier=multiplier,
        tick=tick,
    )

    try:
        outputs = price_option(inputs)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    pricing_df = pd.DataFrame(
        {
            "Metric": ["Price", "Forward", "Cash delta", "Delta hedge", "Δ T+1D"],
            "Description": [
                "Theoretical price",
                "Forward price implied by carry",
                "Directional exposure in cash terms",
                "Underlying shares needed to hedge",
                "One-day change in hedge shares",
            ],
            "Value": [
                _format_number(outputs.unit_price, 4),
                _format_number(outputs.forward, 4),
                _format_number(outputs.signed_cash_delta, 2),
                _format_signed_shares(outputs.signed_delta_hedge_shares),
                _format_signed_shares(outputs.signed_delta_t_plus_1d_shares),
            ],
        }
    )
    cash_greeks_df = pd.DataFrame(
        {
            "Metric": [
                "Gamma (1%)",
                "Theta (day)",
                "Vega (1%)",
                "Charm (day)",
                "Vanna (1%)",
                "Rho (1%)",
            ],
            "Description": [
                "Cash delta for a 1% move",
                "One-day cash decay",
                "Cash P&L for a 1 vol-point move",
                "One-day change in cash delta",
                "Delta sensitivity to volatility",
                "Cash P&L for a 1% rate move",
            ],
            "Value": [
                _format_number(outputs.signed_cash_gamma_per_1pct, 2),
                _format_number(outputs.signed_theta_per_day, 2),
                _format_number(outputs.signed_cash_vega_per_1pct, 2),
                _format_number(outputs.signed_cash_charm_per_day, 2),
                _format_number(outputs.signed_cash_vanna_per_1pct, 2),
                _format_number(outputs.signed_cash_rho_per_1pct, 2),
            ],
        }
    )

    unit_theta_per_day = 0.0
    unit_vega_per_1pct = 0.0
    unit_rho_per_1pct = 0.0
    if inputs.quantity > 0:
        unit_theta_per_day = outputs.signed_theta_per_day / (inputs.quantity * inputs.position_sign)
        unit_vega_per_1pct = outputs.signed_cash_vega_per_1pct / (inputs.quantity * inputs.position_sign)
        unit_rho_per_1pct = outputs.signed_cash_rho_per_1pct / (inputs.quantity * inputs.position_sign)

    unit_greeks_df = pd.DataFrame(
        {
            "Greek": ["Delta", "Gamma", "Vega /1%", "Theta /day", "Rho /1%"],
            "Value": [
                f"{outputs.unit_delta:.3f}",
                f"{outputs.unit_gamma:.3f}",
                f"{unit_vega_per_1pct:.3f}",
                f"{unit_theta_per_day:.3f}",
                f"{unit_rho_per_1pct:.3f}",
            ],
        }
    )

    _render_section_header("Price & Hedge")
    st.caption("Signed values reflect the selected long/short position, lots, and multiplier.")
    st.dataframe(
        pricing_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Value": st.column_config.TextColumn("Value", width="small"),
        },
    )

    _render_section_header("Cash & Unit greeks")
    greeks_tabs = st.tabs(["Cash greeks", "Unit greeks"])
    with greeks_tabs[0]:
        st.caption("Scaled to the full position.")
        st.dataframe(
            cash_greeks_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Metric": st.column_config.TextColumn("Metric", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Value": st.column_config.TextColumn("Value", width="small"),
            },
        )
    with greeks_tabs[1]:
        st.caption("Per option before lot and multiplier scaling.")
        st.dataframe(
            unit_greeks_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Greek": st.column_config.TextColumn("Greek", width="medium"),
                "Value": st.column_config.TextColumn("Value", width="medium"),
            },
        )

    shortcuts = calculate_trading_shortcuts(inputs, outputs)

    _render_section_header("Trading Tools")
    analytics_tabs = st.tabs(
        [
            "Gamma P&L",
            "Trading shortcuts",
            "Gamma to Theta",
            "American exercise",
        ]
    )

    with analytics_tabs[0]:
        gamma_input_cols = st.columns(2)
        with gamma_input_cols[0]:
            spot_move_pct = st.number_input(
                "Spot move %",
                value=1.0,
                step=0.25,
                format="%.2f",
                key="options_gamma_spot_move_pct",
            )
        with gamma_input_cols[1]:
            gamma_iv_pct = st.number_input(
                "IV %",
                min_value=0.0,
                value=20.0,
                step=0.5,
                format="%.1f",
                key="options_gamma_iv_pct",
            )

        gamma_pnl = calculate_gamma_pnl(outputs, spot_move_pct=spot_move_pct, iv_pct=gamma_iv_pct)

        gamma_result_df = pd.DataFrame(
            {
                "Metric": ["New Δ cash", "Gamma P&L", "Daily move"],
                "Value": [
                    _format_number(gamma_pnl.new_cash_delta, 0),
                    _format_number(gamma_pnl.gamma_pnl, 2),
                    _format_percent(gamma_pnl.daily_move_pct, 2),
                ],
                "Note": [
                    "Delta after the spot scenario",
                    "1/2 × cash gamma for 1% × move²",
                    "One-day implied move from IV",
                ],
            }
        )
        st.dataframe(gamma_result_df, hide_index=True, use_container_width=True)

    with analytics_tabs[1]:
        shortcuts_df = pd.DataFrame(
            {
                "Metric": ["Spot", "Premium", "BE spot", "BE move", "BE vol", "BE range", "Gamma / Theta", "Theta earn move"],
                "Value": [
                    _format_number(inputs.spot, 2),
                    _format_number(outputs.unit_price, 4),
                    _format_number(shortcuts.break_even_spot, 2),
                    f"{shortcuts.break_even_pct:+.2f}%",
                    _format_percent(shortcuts.break_even_realized_vol_pct, 2),
                    f"[{shortcuts.break_even_lower_spot:.2f}, {shortcuts.break_even_upper_spot:.2f}]",
                    _format_number(shortcuts.gamma_theta_ratio, 2),
                    _format_percent(shortcuts.theta_earn_move_pct, 2),
                ],
                "Note": [
                    "Current underlying level",
                    "Current option premium per unit",
                    "Spot needed to recover premium",
                    "Move from current spot",
                    "Realized volatility break-even",
                    f"{shortcuts.break_even_ticks:.0f} ticks wide",
                    "Gamma carry versus theta cost",
                    "Move needed to earn one day of theta",
                ],
            }
        )
        st.dataframe(shortcuts_df, hide_index=True, use_container_width=True)

    with analytics_tabs[2]:
        quick_input_cols = st.columns(2)
        with quick_input_cols[0]:
            gamma_notional = st.number_input(
                "Gamma $ notional",
                min_value=0.0,
                value=20_000_000.0,
                step=100_000.0,
                format="%.0f",
                key="options_gamma_notional",
            )
        with quick_input_cols[1]:
            quick_vol_pct = st.number_input(
                "Vol %",
                min_value=0.0,
                value=22.0,
                step=0.5,
                format="%.1f",
                key="options_quick_vol_pct",
            )

        theta_bill = quick_calc_gamma_theta_bill(gamma_notional=gamma_notional, vol_pct=quick_vol_pct)

        theta_df = pd.DataFrame(
            {
                "Metric": ["Θ / day", "Daily move"],
                "Value": [f"${theta_bill.theta_per_day:,.0f}", _format_percent(theta_bill.daily_move_pct, 2)],
                "Note": ["CG × σ² / 50,400", "One-sigma daily move"],
            }
        )
        st.dataframe(theta_df, hide_index=True, use_container_width=True)

    with analytics_tabs[3]:
        tree_steps = st.slider(
            "Tree steps",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            key="options_tree_steps",
        )

        american_analysis = analyze_american_option(inputs, tree_steps=tree_steps)

        table_df = pd.DataFrame(
            {
                "Metric": [
                    "European price (tree)",
                    "American price (CRR)",
                    "Early exercise premium",
                    "Premium",
                    "American delta",
                ],
                "Value": [
                    f"{american_analysis.european_tree_price:.4f}",
                    f"{american_analysis.american_price:.4f}",
                    f"{american_analysis.early_exercise_premium:.4f}",
                    f"{american_analysis.premium_pct:.2f}%",
                    f"{american_analysis.american_delta:.6f}",
                ],
            }
        )
        st.dataframe(table_df, hide_index=True, use_container_width=True)

    _render_payoff_charts(inputs, outputs)
    _render_charts(inputs)

    with st.expander("Unit greek shape analysis", expanded=False):
        _render_unit_greeks_sensitivity(inputs)

    _render_forwards_options_interview_qa()
