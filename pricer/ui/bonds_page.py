from __future__ import annotations

from html import escape
from textwrap import dedent

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pricer.engines.bonds import BondInputs, CallableBondInputs, price_bond, price_callable_bond


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


def _format_money(value: float, decimals: int = 2) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.{decimals}f}"


def _build_price_vs_yield_chart(callable_inputs: CallableBondInputs | None, inputs: BondInputs) -> go.Figure:
    ytm_min = max(0.0, inputs.ytm * 100.0 - 5.0)
    ytm_max = max(15.0, inputs.ytm * 100.0 + 10.0)
    points = 50
    ytm_range = [ytm_min + (ytm_max - ytm_min) * i / (points - 1) for i in range(points)]
    straight_prices = [
        price_bond(
            BondInputs(
                face=inputs.face,
                coupon_rate=inputs.coupon_rate,
                maturity_years=inputs.maturity_years,
                ytm=ytm / 100.0,
                frequency=inputs.frequency,
                settlement_days=inputs.settlement_days,
                notional=inputs.notional,
                shift_bp=inputs.shift_bp,
            )
        ).dirty_price
        for ytm in ytm_range
    ]
    callable_prices = []
    if callable_inputs is not None:
        for ytm in ytm_range:
            shifted_bond = BondInputs(
                face=inputs.face,
                coupon_rate=inputs.coupon_rate,
                maturity_years=inputs.maturity_years,
                ytm=ytm / 100.0,
                frequency=inputs.frequency,
                settlement_days=inputs.settlement_days,
                notional=inputs.notional,
                shift_bp=inputs.shift_bp,
            )
            callable_prices.append(
                price_callable_bond(
                    CallableBondInputs(
                        bond=shifted_bond,
                        call_price=callable_inputs.call_price,
                        first_call_year=callable_inputs.first_call_year,
                        rate_volatility=callable_inputs.rate_volatility,
                        tree_steps=callable_inputs.tree_steps,
                    )
                ).callable_price
            )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ytm_range,
            y=straight_prices,
            mode="lines",
            name="Straight" if callable_inputs is not None else "Dirty price",
            line=dict(color="#3f7edb", width=2.5),
        )
    )
    if callable_inputs is not None:
        fig.add_trace(
            go.Scatter(
                x=ytm_range,
                y=callable_prices,
                mode="lines",
                name="Callable",
                line=dict(color="#d94c48", width=2.5),
            )
        )
    fig.add_hline(
        y=inputs.face,
        line_dash="dash",
        line_color="#b9c5d6",
        annotation_text="Par",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#8b96a8",
    )
    fig.update_layout(
        title=dict(text="<b>Bond Price vs Yield</b>", font=dict(size=14)),
        xaxis=dict(title="YTM (%)", gridcolor="#eef1f4"),
        yaxis=dict(title="", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        hovermode="x unified",
        showlegend=callable_inputs is not None,
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _render_callable_analysis(callable_inputs: CallableBondInputs) -> None:
    outputs = price_callable_bond(callable_inputs)

    _render_section_header("Callable Bond Analysis")
    callable_df = pd.DataFrame(
        {
            "Metric": ["Callable price", "Option value", "Yield to call", "Yield to worst"],
            "Value": [
                _format_number(outputs.callable_price, 4),
                _format_number(outputs.option_value, 4),
                f"{outputs.yield_to_call * 100.0:.4f}%",
                f"{outputs.yield_to_worst * 100.0:.4f}%",
            ],
            "Note": [
                "Estimated bond price after issuer callability",
                "Value of the embedded issuer call",
                "Yield if called at the first call date",
                "Lower of yield to maturity and yield to call",
            ],
        }
    )
    st.dataframe(callable_df, hide_index=True, use_container_width=True)

    with st.expander("Binomial Rate Tree", expanded=True):
        st.slider(
            "Steps",
            min_value=2,
            max_value=20,
            value=callable_inputs.tree_steps,
            step=1,
            key="callable_tree_steps_display",
            disabled=True,
        )


def _build_cash_flow_chart(inputs: BondInputs) -> go.Figure:
    outputs = price_bond(inputs)
    maturities = [point.maturity_year for point in outputs.cash_flows]
    coupon_pv = [point.coupon_pv for point in outputs.cash_flows]
    principal_pv = [point.principal_pv for point in outputs.cash_flows]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=maturities,
            y=coupon_pv,
            name="Coupon PV",
            marker_color="#3f7edb",
        )
    )
    fig.add_trace(
        go.Bar(
            x=maturities,
            y=principal_pv,
            name="Principal PV",
            marker_color="#d94c48",
        )
    )
    fig.update_layout(
        title=dict(text="<b>Present Value of Cash Flows</b>", font=dict(size=14)),
        xaxis=dict(title="Maturity (y)", gridcolor="#eef1f4"),
        yaxis=dict(title="", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        barmode="stack",
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _render_bonds_interview_qa() -> None:
    _render_section_header("Interview Q&A — Bonds, Swaps & Convexity")
    st.caption("Trading-desk questions on swaps, duration, negative rates, callable bonds, and convexity.")

    with st.expander("Question n°1 - How do you make a currency swap ? Give an example.", expanded=False):
        st.markdown("**You simultaneously buy spot and sell forward, or sell spot and buy forward.**")
        st.markdown("Example: I am in Europe and I buy a USD bond with 6M maturity and $1M notional. I need dollars now.")
        fx_swap_df = pd.DataFrame(
            {
                "Date": ["Today", "Today hedge", "In 6 months"],
                "Action": [
                    "Sell EUR/USD spot",
                    "Sell USD forward 6M",
                    "Receive USD from bond maturity",
                ],
                "Meaning": [
                    "Sell EUR and buy USD to fund the bond",
                    "Buy EUR and sell USD forward",
                    "Use the forward hedge to convert USD back into EUR",
                ],
            }
        )
        st.dataframe(fx_swap_df, hide_index=True, use_container_width=True)
        st.markdown("An FX swap is a spot transaction plus the opposite forward transaction.")

    with st.expander("Question n°2 - How do you make an interest rate swap ?", expanded=False):
        st.markdown("**Replicate it with a fixed-rate bond and a Floating Rate Note.**")
        st.markdown("When you buy a bond, you receive the coupon. When you sell or issue a bond, you pay the coupon.")
        st.markdown(
            "Suppose you pay 6% fixed. The risk is that rates decrease, because you could be paying less. "
            "So you would prefer to receive 6% fixed and pay a lower floating rate."
        )
        swap_df = pd.DataFrame(
            {
                "Leg": ["Buy fixed bond", "Sell / issue FRN", "Net position"],
                "Cash flow": ["Receive 6% fixed", "Pay floating", "Receive fixed, pay floating"],
                "Role": ["Fixed leg", "Floating leg", "Interest rate swap"],
            }
        )
        st.dataframe(swap_df, hide_index=True, use_container_width=True)
        st.markdown(
            "The PV of both legs must be equal. Price matching ensures cash-flow equivalence, "
            "and the swap transforms fixed exposure into floating exposure."
        )

    with st.expander("Question n°3 - If I hedge my coupon with a swap, am I still exposed to bond price risk if the curve moves ?", expanded=False):
        st.markdown("**No. By swapping fixed coupons against floating, you neutralize your duration.**")
        st.markdown("The swap mark-to-market compensates the variation of the bond price.")
        st.latex(r"\text{Fixed Bond} + \text{Pay-Fixed Swap} = \text{Synthetic FRN}")
        st.markdown(
            "You are switching from price exposure to margin exposure. By hedging the coupon, you remove duration. "
            "Without duration, there is no yield risk, and the bond price becomes stable like a bank deposit."
        )

    with st.expander("Question n°4 - I am swap payer on 100M notional. Rates increase by 10 bps. Do I make or lose money ?", expanded=False):
        st.markdown("**You make money.**")
        st.markdown(
            "As a payer, you pay fixed and receive floating. Economically, you are short the fixed bond, "
            "so you benefit when fixed bond prices fall, which happens when rates rise."
        )
        st.latex(r"\text{Approx. P\&L} = \text{Notional} \times \text{DV01} \times \Delta \text{bps}")
        st.markdown("For a 100M swap and a 10 bp move, the gain is roughly 100K, depending on the swap duration.")

    with st.expander("Question n°5 - If I pay the swap, do I increase or decrease my duration ?", expanded=False):
        st.markdown("**You decrease it.**")
        st.markdown(
            "Paying fixed is equivalent to selling a fixed bond and buying an FRN. "
            "The FRN resets at every coupon period, typically quarterly, so its duration is close to zero."
        )
        st.markdown("Net effect: you remove fixed-rate duration from the portfolio.")

    with st.expander("Question n°6 - What is the duration of a 5Y zero-coupon bond ? Why ?", expanded=False):
        st.markdown("**5 years.**")
        st.markdown(
            "A zero-coupon bond has no intermediate cash flows. All the risk is concentrated at maturity, "
            "so duration equals maturity."
        )
        st.markdown("This is why zero-coupon bonds have the highest duration and convexity for a given maturity.")

    with st.expander("Question n°7 - What does it mean buying a bond at -1% interest rate ? Why would you do it ?", expanded=False):
        st.markdown("**It means you buy above par something that will return par at maturity.**")
        st.markdown("If held to maturity, the investor locks in a loss.")
        st.markdown(
            "Why buy it ? Because you may expect rates to go even more negative. "
            "Then the bond price rises further and you can sell it at a profit before maturity."
        )
        st.markdown("This happened extensively in Europe and Japan during the negative-rate era.")

    with st.expander("Question n°8 - Can a zero-coupon bond trade at a premium ? Why ?", expanded=False):
        st.markdown("**Yes. If yields are negative, the zero-coupon bond price rises above par.**")
        st.latex(r"\text{Price} = \frac{\text{Face}}{(1+y)^T}")
        st.markdown("If y is negative, the denominator is below 1, so price is above face value.")
        st.markdown("This happened with German Bunds and Swiss government bonds during the negative-rate era.")

    with st.expander("Question n°9 - Describe simply what convexity is in bond trading.", expanded=False):
        st.markdown("**With convexity, you earn more when you make money, and you lose less when you lose money.**")
        st.markdown(
            "Convexity is the curvature of the price-yield relationship. A high-convexity bond benefits more "
            "from a rate decrease than it suffers from an equal rate increase."
        )
        st.markdown("It is the bond equivalent of being long gamma in options.")

    with st.expander("Question n°10 - What is the cheapest: a callable bond or a straight bond ? Why ?", expanded=False):
        st.markdown("**The callable bond is cheaper.**")
        st.markdown(
            "A callable bond has negative convexity at low yields. The issuer can call it back and refinance at lower rates, "
            "which prevents the bondholder from receiving the full price appreciation."
        )
        st.latex(r"\text{Callable Bond} = \text{Straight Bond} - \text{Call Option}")
        st.markdown("The issuer owns the call option. The bondholder is short convexity and must be compensated with a lower price.")

    with st.expander("Question n°11 - For a given maturity, which bond has the strongest convexity: a ZCB or a 5% coupon bond ?", expanded=False):
        st.markdown("**The zero-coupon bond.**")
        st.markdown(
            "A coupon bond spreads PV across many dates, while a ZCB has 100% of PV at maturity. "
            "The more value is pushed into the future, the stronger the sensitivity to rate changes."
        )
        convexity_df = pd.DataFrame(
            {
                "Bond": ["5% coupon bond", "Zero-coupon bond"],
                "PV distribution": ["Spread across coupons and principal", "100% concentrated at maturity"],
                "Convexity": ["Lower", "Higher"],
            }
        )
        st.dataframe(convexity_df, hide_index=True, use_container_width=True)
        st.markdown("Therefore, the ZCB has higher convexity.")

    with st.expander("Question n°12 - If interest rates increase, does convexity increase or decrease ? Why ?", expanded=False):
        st.markdown("**It decreases.**")
        st.markdown(
            "When rates rise, the PV of each cash flow decreases, especially the longest-dated cash flows. "
            "Since convexity is driven by distant cash flows, the overall convexity shrinks."
        )

    with st.expander("Question n°13 - Two bonds, same maturity: 5% coupon and 10% coupon. Rates go from 2% to 8%. Which convexity decreases first ?", expanded=False):
        st.markdown("**The 5% coupon bond.**")
        st.markdown(
            "It has higher duration because more of its value is concentrated farther in the future. "
            "When rates rise sharply, those longer-duration cash flows lose more PV, so convexity drops faster."
        )
        st.markdown("The 10% coupon bond has more PV in near-term coupons, so it is less sensitive.")

    with st.expander("Question n°14 - Which portfolio has the biggest convexity: A: two 10Y-duration bonds, or B: one 5Y and one 15Y ?", expanded=False):
        st.markdown("**Portfolio B has more convexity.**")
        st.markdown(
            "Both portfolios have the same average duration of 10Y. But portfolio B has cash flows that are more spread out over time."
        )
        barbell_df = pd.DataFrame(
            {
                "Portfolio": ["A: bullet", "B: barbell"],
                "Composition": ["Two 10Y-duration bonds", "One 5Y-duration bond + one 15Y-duration bond"],
                "Average duration": ["10Y", "10Y"],
                "Convexity": ["Lower", "Higher"],
            }
        )
        st.dataframe(barbell_df, hide_index=True, use_container_width=True)
        st.markdown(
            "Convexity depends on dispersion of cash flows around duration. More spread means more convexity. "
            "This is the principle behind barbell versus bullet strategies: the barbell has higher convexity for the same duration."
        )


def render_bonds_page() -> None:
    with st.sidebar:
        st.markdown("### Parameters")

        face = st.number_input("Face value", min_value=0.01, value=1000.0, step=100.0, format="%.0f")
        coupon_pct = st.number_input("Coupon (%)", min_value=0.0, value=5.0, step=0.25, format="%.2f")

        maturity_col, ytm_col = st.columns(2)
        maturity_years = maturity_col.number_input("Maturity (years)", min_value=0.01, value=10.0, step=0.5, format="%.1f")
        ytm_pct = ytm_col.number_input("Yield to maturity (%)", value=5.0, step=0.25, format="%.2f")

        settlement_col, frequency_col = st.columns(2)
        settlement_days = settlement_col.number_input("Settlement days", min_value=0, value=0, step=1, format="%d")
        frequency = frequency_col.selectbox("Frequency", options=[1, 2, 4, 12], index=1)

        notional = st.number_input("Notional", min_value=1.0, value=1_000_000.0, step=10_000.0, format="%.0f")
        shift_bp = st.number_input("Shift (bp)", value=1.0, step=0.1, format="%.1f")

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        is_callable = st.toggle("Callable", value=False)
        call_price = 1000.0
        first_call_year = 5.0
        rate_volatility_pct = 20.0
        if is_callable:
            call_price = st.number_input("Call price", min_value=0.01, value=1000.0, step=10.0, format="%.0f")
            first_call_year = st.number_input("First call year", min_value=0.01, value=5.0, step=0.5, format="%.1f")
            rate_volatility_pct = st.number_input("Interest rate volatility (%)", min_value=0.0, value=20.0, step=0.5, format="%.1f")

    inputs = BondInputs(
        face=face,
        coupon_rate=coupon_pct / 100.0,
        maturity_years=maturity_years,
        ytm=ytm_pct / 100.0,
        frequency=frequency,
        settlement_days=settlement_days,
        notional=notional,
        shift_bp=shift_bp,
    )

    try:
        outputs = price_bond(inputs)
        callable_inputs = None
        if is_callable:
            callable_inputs = CallableBondInputs(
                bond=inputs,
                call_price=call_price,
                first_call_year=first_call_year,
                rate_volatility=rate_volatility_pct / 100.0,
                tree_steps=6,
            )
            price_callable_bond(callable_inputs)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    _render_section_header("Bond Pricing")
    pricing_df = pd.DataFrame(
        {
            "Metric": ["Dirty price", "Clean price", "Accrued interest"],
            "Value": [
                _format_number(outputs.dirty_price, 2),
                _format_number(outputs.clean_price, 2),
                _format_number(outputs.accrued_interest, 4),
            ],
            "Note": ["Full price including accrued interest", "Quoted bond price", "Coupon accrued since last payment"],
        }
    )
    st.dataframe(pricing_df, hide_index=True, use_container_width=True)

    _render_section_header("Duration & Convexity")
    duration_df = pd.DataFrame(
        {
            "Metric": ["Macaulay duration", "Modified duration", "Convexity"],
            "Value": [f"{outputs.macaulay_duration:.4f} y", f"{outputs.modified_duration:.4f} y", _format_number(outputs.convexity, 4)],
            "Note": ["PV-weighted cash-flow time", "Yield sensitivity duration", "Curvature of price-yield relation"],
        }
    )
    st.dataframe(duration_df, hide_index=True, use_container_width=True)

    _render_section_header("Risk Sensitivity")
    risk_df = pd.DataFrame(
        {
            "Metric": ["DV01 (per bond)", "PV01 (notional)", f"PnL (+{shift_bp:g} bp)"],
            "Value": [
                _format_number(outputs.dv01_per_bond, 4),
                _format_money(outputs.pv01_notional, 2),
                _format_money(outputs.pnl_for_shift, 2),
            ],
            "Note": ["Price value of 1 bp per bond", "Scaled to notional", "Estimated P&L for the selected yield shift"],
        }
    )
    st.dataframe(risk_df, hide_index=True, use_container_width=True)

    if callable_inputs is not None:
        _render_callable_analysis(callable_inputs)

    _render_section_header("Charts")
    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.plotly_chart(_build_price_vs_yield_chart(callable_inputs, inputs), use_container_width=True)
    with chart_cols[1]:
        st.plotly_chart(_build_cash_flow_chart(inputs), use_container_width=True)

    with st.expander("Cash-flow table", expanded=False):
        cash_flow_df = pd.DataFrame(
            {
                "Maturity (y)": [point.maturity_year for point in outputs.cash_flows],
                "Coupon PV": [point.coupon_pv for point in outputs.cash_flows],
                "Principal PV": [point.principal_pv for point in outputs.cash_flows],
                "Total PV": [point.coupon_pv + point.principal_pv for point in outputs.cash_flows],
            }
        )
        st.dataframe(
            cash_flow_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Maturity (y)": st.column_config.NumberColumn("Maturity (y)", format="%.2f"),
                "Coupon PV": st.column_config.NumberColumn("Coupon PV", format="%.2f"),
                "Principal PV": st.column_config.NumberColumn("Principal PV", format="%.2f"),
                "Total PV": st.column_config.NumberColumn("Total PV", format="%.2f"),
            },
        )

    _render_bonds_interview_qa()
