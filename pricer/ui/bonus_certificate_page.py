from __future__ import annotations

from html import escape
from textwrap import dedent

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pricer.engines.bonus_certificate import (
    BonusCertificateInputs,
    payoff_at_maturity,
    price_bonus_certificate,
)


LEVEL_INPUT_OPTIONS = ["Absolute", "% of spot"]


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


def _format_pct(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "Uncapped"
    return f"{value:.{decimals}f}%"


def _build_sensitivity_chart(inputs: BonusCertificateInputs, x_axis: str) -> go.Figure:
    x_values = []
    bc_prices = []
    put_values = []
    if x_axis == "vol":
        x_values = [5.0 + (60.0 - 5.0) * i / 39 for i in range(40)]
        for vol in x_values:
            outputs = price_bonus_certificate(
                BonusCertificateInputs(**{**inputs.__dict__, "put_volatility": vol / 100.0})
            )
            bc_prices.append(outputs.certificate_price)
            put_values.append(outputs.put_down_and_out_value)
        x_title = "Volatility (%)"
        title = "BC Price & Put D&O vs Volatility"
    else:
        x_values = [0.1 + (3.0 - 0.1) * i / 39 for i in range(40)]
        for maturity in x_values:
            outputs = price_bonus_certificate(
                BonusCertificateInputs(**{**inputs.__dict__, "maturity_years": maturity})
            )
            bc_prices.append(outputs.certificate_price)
            put_values.append(outputs.put_down_and_out_value)
        x_title = "Time (y)"
        title = "BC Price & Put D&O vs Time to Maturity"

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_values, y=bc_prices, mode="lines", name="BC Price", line=dict(color="#3f7edb", width=2.5)))
    fig.add_trace(go.Scatter(x=x_values, y=put_values, mode="lines", name="Put D&O", line=dict(color="#e54842", width=2.2, dash="dot")))
    if x_axis == "vol":
        fig.add_vline(x=inputs.put_volatility * 100.0, line_dash="dash", line_color="#aebbd0")
    else:
        fig.add_vline(x=inputs.maturity_years, line_dash="dash", line_color="#aebbd0")
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14)),
        xaxis=dict(title=x_title, gridcolor="#eef1f4"),
        yaxis=dict(title="Price", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _render_how_it_works() -> None:
    with st.expander("How It Works - Bonus vs Cap", expanded=True):
        st.markdown("**Example: S = 100, Barrier = 70, Bonus = 120, Cap = 140. If the barrier is never breached:**")
        example_df = pd.DataFrame(
            {
                "S_T at Maturity": [60, 80, 110, 130, 150],
                "Payoff": [60, 120, 120, 130, 140],
                "Why": [
                    "Barrier was hit -> no protection, you hold the stock",
                    "S_T < Bonus -> the bonus floor kicks in",
                    "Still below Bonus -> payoff = Bonus = 120",
                    "Bonus < S_T < Cap -> you follow the stock upside",
                    "S_T > Cap -> capped at 140",
                ],
            }
        )
        st.dataframe(example_df, hide_index=True, use_container_width=True)
        st.markdown("**Bonus = floor.** As long as the barrier is intact, you receive at least the Bonus level, even if the stock ends below it.")
        st.markdown("**Cap = ceiling.** Even if the stock rallies to 200, your payoff is limited to the Cap.")
        st.markdown("**Between Bonus and Cap:** you participate 1:1 in the upside.")
        st.markdown(
            "The Cap exists because you are short a Call(K=Cap) in the replication. "
            "This partially funds the Down-and-Out Put that gives the Bonus protection."
        )


def _build_payoff_chart(inputs: BonusCertificateInputs) -> go.Figure:
    high = max(inputs.underlying * 1.8, (inputs.cap or inputs.bonus_level) * 1.25)
    spots = [high * i / 80 for i in range(81)]
    bc_payoff = [payoff_at_maturity(inputs, spot, barrier_breached=spot <= inputs.barrier) for spot in spots]
    stock_payoff = [spot / inputs.parity for spot in spots]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=spots, y=stock_payoff, mode="lines", name="Stock", line=dict(color="#b5bdc9", width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=spots, y=bc_payoff, mode="lines", name="BC (barrier breached)", line=dict(color="#e54842", width=2.5)))
    fig.add_vline(x=inputs.barrier, line_dash="dash", line_color="#aebbd0", annotation_text="B", annotation_position="bottom")
    fig.add_vline(x=inputs.underlying, line_dash="dot", line_color="#aebbd0", annotation_text="S0", annotation_position="bottom")
    if inputs.cap is not None:
        fig.add_hline(y=inputs.cap / inputs.parity, line_dash="dot", line_color="#aebbd0", annotation_text="N+BA", annotation_position="top right")
    fig.update_layout(
        title=dict(text="<b>Payoff at Maturity</b>", font=dict(size=14)),
        xaxis=dict(title="S_T", gridcolor="#eef1f4"),
        yaxis=dict(title="X_T", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _build_pnl_chart(inputs: BonusCertificateInputs) -> go.Figure:
    outputs = price_bonus_certificate(inputs)
    high = max(inputs.underlying * 1.8, (inputs.cap or inputs.bonus_level) * 1.25)
    spots = [high * i / 80 for i in range(81)]
    bc_pnl = [payoff_at_maturity(inputs, spot, barrier_breached=spot <= inputs.barrier) - outputs.certificate_price for spot in spots]
    stock_pnl = [spot / inputs.parity - inputs.underlying / inputs.parity for spot in spots]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=spots, y=stock_pnl, mode="lines", name="Stock", line=dict(color="#b5bdc9", width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=spots, y=bc_pnl, mode="lines", name="BC (barrier breached)", line=dict(color="#e54842", width=2.5)))
    fig.add_hline(y=0, line_color="#dce3ec", line_width=1)
    fig.add_vline(x=inputs.barrier, line_dash="dash", line_color="#aebbd0", annotation_text="B", annotation_position="bottom")
    fig.add_vline(x=inputs.underlying, line_dash="dot", line_color="#aebbd0", annotation_text="S0", annotation_position="bottom")
    fig.add_vline(x=outputs.breakeven * inputs.parity, line_dash="dash", line_color="#54a66b", annotation_text="BE", annotation_position="top")
    fig.update_layout(
        title=dict(text="<b>Profit & Loss</b>", font=dict(size=14)),
        xaxis=dict(title="S_T", gridcolor="#eef1f4"),
        yaxis=dict(title="P&L", gridcolor="#eef1f4"),
        margin=dict(l=0, r=0, t=42, b=0),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _render_bonus_certificate_qa() -> None:
    _render_section_header("Trading Q&A - Bonus Certificates")
    st.caption(
        "Replication: BC = Long S + Long Put D&O(K=Bonus, B=Barrier) - Call(K=Cap). "
        "Client buys the cert: Long S, Long Put D&O, Short Call. Trader sells the cert and hedges: Short S, Short Put D&O, Long Call."
    )

    with st.expander("Question n°1 - Which is more expensive: a Bonus Certificate or a Capped Bonus Certificate ?", expanded=False):
        st.markdown("**The uncapped Bonus Certificate is more expensive.**")
        st.markdown(
            "Client view: the capped version includes a short call at the cap. The client sells upside, "
            "and that call premium reduces the certificate price. Lower cap means cheaper cert and more limited upside."
        )
        st.markdown(
            "Trader view: in the capped version, the trader is long the call. This call premium offsets part of the cost "
            "of the Put D&O exposure. Without the cap, there is no call income, so the trader charges a higher price."
        )
        st.markdown("The cap finances the bonus protection. No cap means the client pays for the full Put D&O.")

    with st.expander("Question n°2 - As a trader seller, where are you gamma long or gamma short ?", expanded=False):
        st.markdown("**Trader hedge: Short S, Short Put D&O, Long Call(K=Cap).**")
        st.markdown(
            "- Near the cap: gamma long from the long call. Spot moves around the cap generate mark-to-market gains, paid for with theta.\n"
            "- Far from the barrier, near the bonus level: gamma short from the short Put D&O, which behaves like a vanilla put.\n"
            "- Near the barrier: gamma can flip violently. The short Put D&O benefits as the put collapses, but delta is unstable."
        )
        st.markdown(
            "The barrier zone is the most dangerous area: gamma changes sign, delta is unstable, and a breach creates a discrete jump."
        )

    with st.expander("Question n°3 - Client vs trader: who is long vega, who is short vega ?", expanded=False):
        st.markdown("**It depends on spot location, and client and trader are always opposite.**")
        vega_df = pd.DataFrame(
            {
                "Zone": ["Far from barrier", "Near barrier", "Near cap"],
                "Client": ["Long vega", "Short vega", "Short vega"],
                "Trader": ["Short vega", "Long vega", "Long vega"],
                "Reason": [
                    "Put D&O behaves closer to a vanilla put",
                    "Higher vol increases knock-out probability, hurting the client's put",
                    "Client is short the cap call; trader is long it",
                ],
            }
        )
        st.dataframe(vega_df, hide_index=True, use_container_width=True)
        st.markdown("This vega sign flip near the barrier is a hallmark of barrier options.")

    with st.expander("Question n°4 - If volatility increases, does the certificate get cheaper or more expensive ?", expanded=False):
        st.markdown("**It depends on barrier distance.**")
        st.markdown(
            "- Barrier far, for example 30% OTM: Put D&O behaves closer to a vanilla put. Higher vol increases the put value, so the cert gets more expensive.\n"
            "- Barrier close, for example 5% OTM: higher vol makes knock-out more likely. The put can lose value, so the cert gets cheaper."
        )
        st.markdown(
            "The volatility sensitivity can be non-monotonic: price may rise with vol first, then reverse when knock-out probability dominates."
        )
        st.markdown("For the trader, this means the vol exposure can flip as spot moves closer to the barrier.")

    with st.expander("Question n°5 - What happens to the trader's hedge as spot approaches the barrier ?", expanded=False):
        st.markdown("**The trader faces a hedging nightmare.**")
        st.markdown(
            "The trader is short the Put D&O. As spot approaches the barrier, the put collapses toward zero, "
            "which benefits the short position. But the delta swings violently."
        )
        st.markdown(
            "- The put delta moves toward zero.\n"
            "- The trader must rapidly unwind the stock hedge.\n"
            "- Gamma becomes extreme and unstable.\n"
            "- At breach, the put dies instantly and the position value jumps."
        )
        st.markdown("Barrier options are exotic because the Greeks near the barrier are brutal to manage.")

    with st.expander("Question n°6 - When does the Bonus Cert outperform the stock ? Client perspective.", expanded=False):
        st.markdown("**In sideways or moderately bearish markets, as long as the barrier remains intact.**")
        scenarios_df = pd.DataFrame(
            {
                "Scenario": [
                    "S_T < Barrier (breach)",
                    "Barrier < S_T < Bonus",
                    "Bonus < S_T < Cap",
                    "S_T > Cap",
                ],
                "Stock P&L": ["S_T - S0 (loss)", "S_T - S0 (loss)", "S_T - S0", "S_T - S0 (big gain)"],
                "Cert P&L": ["S_T - Cost", "Bonus - Cost", "S_T - Cost", "Cap - Cost"],
                "Winner": ["Tie", "Cert", "Similar", "Stock"],
            }
        )
        st.dataframe(scenarios_df, hide_index=True, use_container_width=True)
        st.markdown("The sweet spot is a moderate drop that stays above the barrier. The worst case is a crash through the barrier.")

    with st.expander("Question n°7 - Continuous vs discrete barrier: who benefits ?", expanded=False):
        st.markdown("**Continuous monitoring makes the cert cheaper and benefits the trader or issuer.**")
        st.markdown(
            "- Continuous: more chances to knock out, so the Put D&O is worth less and the cert price is lower.\n"
            "- Discrete: the put can survive intraday breaches, so it is worth more and more expensive to structure."
        )
        st.markdown(
            "Continuous barriers are easier to price with closed forms but harder to hedge because the barrier can be hit at any time. "
            "Discrete barriers often need Monte Carlo or lattice methods but hedging is more predictable."
        )

    with st.expander("Question n°8 - Compare delta-hedging a Long PDI vs a Short PDO as spot falls to the barrier. What is similar ?", expanded=False):
        st.markdown("**Both positions accumulate shares on the way down and must sell at the barrier. That creates identical pin risk.**")
        hedge_df = pd.DataFrame(
            {
                "Spot": ["100 (start)", "85 (-15%)", "75 (-25%)", "70 (breach)"],
                "Long PDI": [
                    "Buy ~5 shares, knock-in unlikely",
                    "Buy ~15 more, delta deepens",
                    "Buy ~40 more, barrier proximity amplifies",
                    "Activates into vanilla put ITM -> sell ~100+ excess shares",
                ],
                "Short PDO": [
                    "Sell ~45 shares, behaves like short ATM put",
                    "Buy back ~15, knock-out more likely",
                    "Buy back ~25 more, nearly zero delta",
                    "Knocks out -> sell entire accumulated hedge",
                ],
            }
        )
        st.dataframe(hedge_df, hide_index=True, use_container_width=True)
        st.markdown("Key similarity: both sell at the same level, at the same moment, potentially in a thin market.")

    with st.expander("Question n°9 - Is a trader short a Put Down-and-Out gamma short throughout the life of the trade ?", expanded=False):
        st.markdown("**No. That is a critical misconception.**")
        st.markdown(
            "A Short PDO starts gamma short because it behaves like a short vanilla put far from the barrier. "
            "But as spot approaches the barrier, gamma can flip to long."
        )
        st.markdown(
            "Near the barrier, every tick down increases knock-out probability. The put loses value rapidly as it approaches death, "
            "so the trader short the put benefits from this convexity."
        )
        st.markdown("Gamma sign on a barrier option is dynamic and path-dependent.")

    with st.expander("Question n°10 - Spot breaches the barrier at 70. What happens to the hedge for Long PDI and Short PDO ?", expanded=False):
        st.markdown("**Long PDI: activates into a vanilla ITM put. Short PDO: knocks out and becomes dead.**")
        breach_df = pd.DataFrame(
            {
                "Position": ["Long PDI", "Short PDO"],
                "At breach": [
                    "PDI activates into vanilla ITM put",
                    "PDO knocks out and obligation disappears",
                ],
                "Hedge action": [
                    "Sell excess shares because barrier delta snaps back to vanilla put delta",
                    "Sell the full hedge because delta collapses to zero",
                ],
                "After breach": [
                    "Still manage a live vanilla put",
                    "Position is dead: delta, gamma, vega = 0",
                ],
            }
        )
        st.dataframe(breach_df, hide_index=True, use_container_width=True)

    with st.expander("Question n°11 - Near the barrier, how do gamma and vega behave differently for Long PDI vs Short PDO ?", expanded=False):
        st.markdown("**Both flip, but in different ways.**")
        greeks_df = pd.DataFrame(
            {
                "Greek": ["Gamma", "Vega", "After breach"],
                "Long PDI": [
                    "Strong long: knock-in probability is amplified",
                    "Strong long: higher vol increases knock-in probability",
                    "Gamma short and vega short as a vanilla put",
                ],
                "Short PDO": [
                    "Flips to long: short position benefits as the put dies",
                    "Flips to long: higher vol increases knock-out probability",
                    "Gamma = 0 and vega = 0 because position is dead",
                ],
            }
        )
        st.dataframe(greeks_df, hide_index=True, use_container_width=True)
        st.markdown("This is why standard intuition like short option = short gamma breaks down near barriers.")

    with st.expander("Question n°12 - Why is barrier pin risk so dangerous for both Long PDI and Short PDO traders ?", expanded=False):
        st.markdown("**Both traders are forced sellers at the same price, at the same moment, in a potentially illiquid market.**")
        st.markdown(
            "- Long PDI trader: may hold too many shares and must sell excess after activation.\n"
            "- Short PDO trader: must sell the entire hedge after knock-out.\n"
            "- Many dealers may have the same barrier level, creating concentrated flow."
        )
        st.markdown(
            "The feedback loop is dangerous: barrier breach -> forced selling -> price drops further -> more barriers trigger -> more forced selling."
        )
        st.markdown("Round-number barriers such as 70, 80, or 90 can create market-structure risk.")


def render_bonus_certificate_page() -> None:
    with st.sidebar:
        st.markdown("### Parameters")

        underlying = st.number_input("Underlying", min_value=0.01, value=100.0, step=1.0, format="%.2f")

        st.caption("Levels (absolute or % of Spot)")
        input_as = st.selectbox("Input as", options=LEVEL_INPUT_OPTIONS, index=0)

        bonus_level_raw = st.number_input("Bonus level", min_value=0.01, value=120.0, step=1.0, format="%.2f")
        barrier_raw = st.number_input("Barrier", min_value=0.01, value=70.0, step=1.0, format="%.2f")

        has_cap = st.toggle("Cap", value=True)
        if has_cap:
            cap_raw = st.number_input("Cap level", min_value=0.01, value=140.0, step=1.0, format="%.2f")
        else:
            cap_raw = None

        if input_as == "% of spot":
            bonus_level = underlying * bonus_level_raw / 100.0
            barrier = underlying * barrier_raw / 100.0
            cap_level = None if cap_raw is None else underlying * cap_raw / 100.0
        else:
            bonus_level = bonus_level_raw
            barrier = barrier_raw
            cap_level = cap_raw

        maturity_years = st.number_input("Maturity (years)", min_value=0.01, value=1.0, step=0.25, format="%.2f")

        st.caption("Volatility (skew)")
        put_vol_col, call_vol_col = st.columns(2)
        put_vol_pct = put_vol_col.number_input("Put volatility (%)", min_value=0.0, value=22.0, step=0.5, format="%.1f")
        call_vol_pct = call_vol_col.number_input("Call volatility (%)", min_value=0.0, value=18.0, step=0.5, format="%.1f")

        rate_col, dividend_col = st.columns(2)
        rate_pct = rate_col.number_input("Risk-free rate (%)", value=5.0, step=0.25, format="%.2f")
        dividend_yield_pct = dividend_col.number_input("Dividend yield (%)", value=2.0, step=0.25, format="%.2f")

        parity = st.number_input("Parity", min_value=0.0001, value=1.0, step=0.1, format="%.4f")

    inputs = BonusCertificateInputs(
        underlying=underlying,
        bonus_level=bonus_level,
        barrier=barrier,
        cap=cap_level,
        maturity_years=maturity_years,
        put_volatility=put_vol_pct / 100.0,
        call_volatility=call_vol_pct / 100.0,
        rate=rate_pct / 100.0,
        dividend_yield=dividend_yield_pct / 100.0,
        parity=parity,
    )

    try:
        outputs = price_bonus_certificate(inputs)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    cap_label = "Call(K=Cap)" if inputs.cap is not None else "No cap call"
    _render_section_header("Replication - Long Underlying + Long Put Down-and-Out(K=Bonus, B=Barrier) - Call(K=Cap)")
    st.markdown(
        f"**BC = PV(S) + Put_DO - {cap_label}** = "
        f"`{outputs.underlying_pv:.4f}` + `{outputs.put_down_and_out_value:.4f}` - `{abs(outputs.short_call_value):.4f}` "
        f"= `{outputs.certificate_price:.4f}`"
    )

    _render_section_header("Key Metrics")
    metrics_df = pd.DataFrame(
        {
            "Metric": ["Certificate price", "Barrier distance", "Bonus return", "Breakeven", "Put D&O value", "Max return (cap)"],
            "Value": [
                _format_number(outputs.certificate_price, 4),
                _format_pct(outputs.barrier_distance_pct, 2),
                _format_pct(outputs.bonus_return_pct, 2),
                _format_number(outputs.breakeven, 2),
                _format_number(outputs.put_down_and_out_value, 4),
                _format_pct(outputs.max_return_pct, 2),
            ],
            "Note": [
                "Current certificate value",
                "Distance from spot to barrier",
                "Return if bonus payoff is achieved",
                "Certificate cost per unit",
                "Value of the barrier put component",
                "Return if payoff reaches the cap",
            ],
        }
    )
    st.dataframe(metrics_df, hide_index=True, use_container_width=True)

    with st.expander("Pricing Decomposition", expanded=True):
        decomposition_df = pd.DataFrame(
            {
                "Component": [
                    "Underlying PV (S x e^{-qT})",
                    "+ Put Down-and-Out (K=Bonus, B=Barrier)",
                    "- Call (K=Cap)",
                    '= "Certificate Price"',
                ],
                "Value": [
                    f"{outputs.underlying_pv:.4f}",
                    f"+{outputs.put_down_and_out_value:.4f}",
                    f"{outputs.short_call_value:.4f}",
                    f"**{outputs.certificate_price:.4f}**",
                ],
            }
        )
        st.dataframe(decomposition_df, hide_index=True, use_container_width=True)

    _render_how_it_works()

    _render_section_header("Payoff at Maturity")
    payoff_cols = st.columns(2)
    with payoff_cols[0]:
        st.plotly_chart(_build_payoff_chart(inputs), use_container_width=True)
    with payoff_cols[1]:
        st.plotly_chart(_build_pnl_chart(inputs), use_container_width=True)

    _render_section_header("Sensitivity - Volatility & Time to Maturity")
    sensitivity_cols = st.columns(2)
    with sensitivity_cols[0]:
        st.plotly_chart(_build_sensitivity_chart(inputs, "vol"), use_container_width=True)
    with sensitivity_cols[1]:
        st.plotly_chart(_build_sensitivity_chart(inputs, "time"), use_container_width=True)

    _render_bonus_certificate_qa()
