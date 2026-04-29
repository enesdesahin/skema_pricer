from __future__ import annotations

from html import escape
from textwrap import dedent

import pandas as pd
import streamlit as st


def _render_section_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div style="font-size: 13px; color: #6f7278; margin-top: 4px; letter-spacing: 0;">{escape(subtitle)}</div>'
    st.markdown(
        dedent(
            f"""
            <div style="margin-top: 8px; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid #e6e6e6;">
                <div style="font-size: 13px; font-weight: 700; letter-spacing: 0.08em; color: #6f7278; text-transform: uppercase;">{escape(title)}</div>
                {subtitle_html}
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def _answer(title: str):
    return st.expander(title, expanded=False)


def _render_greeks_qa() -> None:
    _render_section_header(
        "Greeks - Reading Your Book",
        "Quick-fire questions on Delta, Gamma, Vega, and P&L from a trading book perspective.",
    )

    with _answer("Q1. Delta = 0, Gamma = 1 M EUR. Spot increases by 5%. What is my Delta ?"):
        st.markdown("**Delta = 5 M EUR.**")
        st.markdown("Gamma tells you how much your delta changes per 1% move in spot.")
        st.markdown(
            "- Gamma = 1 M EUR, so for every 1% up, delta increases by 1 M.\n"
            "- Spot moves up 5%, so Delta change = 1 M x 5 = 5 M EUR.\n"
            "- Starting delta was 0, so new delta = 5 M EUR."
        )
        st.markdown("Long gamma means you accumulate delta in the direction of the move.")

    with _answer("Q2. Delta = -1 M EUR, Gamma = 1 M EUR. Spot goes up by 1%. What is my Delta ?"):
        st.markdown("**Delta = -2 M EUR.**")
        st.latex(r"\text{New Delta} = \text{Old Delta} - \Gamma \times \%\text{move}")
        st.markdown("New Delta = -1 M - 1 M x 1 = -2 M EUR.")
        st.markdown("Starting at -1 M delta, a 1% up move pushes delta further negative by another 1 M.")

    with _answer("Q3. Delta = 1 M EUR, Gamma = -1 M EUR. What is my Delta if spot goes down 1% ? Up 1% ?"):
        st.markdown("**Down 1%: Delta = 2 M EUR. Up 1%: Delta = 0.**")
        st.markdown("You are short gamma. Short gamma means your delta moves against you.")
        st.markdown(
            "- Spot down 1%: new delta = 1 M + 1 M = 2 M EUR. You get longer as the market falls.\n"
            "- Spot up 1%: new delta = 1 M - 1 M = 0 EUR. You get flatter as the market rises."
        )
        st.markdown("This is the curse of short gamma: you accumulate delta in the losing direction.")

    with _answer("Q4. I see 100 K EUR vega. IV drops by 1 point. Do I make or lose money ? How much ?"):
        st.markdown("**You lose 100 K EUR.**")
        st.markdown("Vega is the sensitivity of your position to a 1 vol-point change in implied volatility.")
        st.markdown(
            "Vega = +100 K means you are long volatility. IV drops 1 point, so P&L = 100 K x (-1) = -100 K EUR."
        )
        st.markdown("Long vega means long options. You want implied volatility to expand.")

    with _answer("Q5. Gamma = 1 M, Delta flat. Spot goes up by 5%. What is my P&L ?"):
        st.markdown("**P&L = +125 K EUR.**")
        st.latex(r"\text{P\&L} = \frac{1}{2} \times \Gamma \times \text{move}^2")
        st.markdown(
            "Gamma = 1 M EUR per 1% move. Move = 5%. "
            "P&L = 1/2 x 1 M x 25% = 125 K EUR."
        )
        st.markdown("The P&L is the area under the delta curve. Long gamma plus a big move means profit, regardless of direction.")

    with _answer("Q6. I buy 1 000 calls, ATM, multiplier 10. How many shares do I buy or sell to be hedged ?"):
        st.markdown("**Sell 5 000 shares.**")
        st.markdown("ATM call delta is approximately 0.5.")
        st.markdown("1 000 calls x multiplier 10 = exposure on 10 000 shares.")
        st.markdown("Delta exposure = 10 000 x 0.5 = 5 000 shares long. To be delta-neutral, sell 5 000 shares.")

    with _answer("Q7. I have a deep ITM call. The dividend is about to be paid out. What should I do ?"):
        st.markdown("**Exercise your calls to own the stock before the ex-date.**")
        st.markdown(
            "If you hold a deep ITM call and do not exercise, the stock drops by the dividend amount on the ex-date "
            "and you receive nothing."
        )
        st.markdown("A deep ITM call has minimal time value, so exercising sacrifices almost nothing and lets you collect the dividend.")

    with _answer("Q8. Expiry day. I am short 1 000 calls, strike 100, spot = 100. What is delta cash at 99.9 ? At 100.1 ?"):
        st.markdown("**Spot = 99.9: Delta cash = 0. Spot = 100.1: Delta cash = -10 000 000.**")
        st.markdown(
            "- At 99.9, calls expire OTM, so delta = 0.\n"
            "- At 100.1, calls expire ITM, so delta = -1 because you are short calls."
        )
        st.markdown("This is pin risk at expiry. A tiny move around the strike can swing your delta from 0 to a very large short exposure.")

    with _answer("Q9. I buy stock at 100. It goes up 10% day 1, then down 10% day 2. Did I make money ?"):
        st.markdown("**You lost 1 EUR. Ending spot = 99.**")
        st.markdown("Day 1: 100 x 1.10 = 110. Day 2: 110 x 0.90 = 99.")
        st.markdown(
            "Percentage moves are not symmetric. A +10% followed by -10% does not bring you back to the start. "
            "This is volatility drag."
        )

    with _answer("Q10. I have an ITM call. IV goes to 0. What is my Delta ?"):
        st.markdown("**Delta = 1.**")
        st.markdown("If volatility is zero, there is no uncertainty. An ITM call finishes ITM with certainty and behaves like a forward.")

    with _answer("Q11. I have an OTM call. IV goes to 0. What is my Delta ?"):
        st.markdown("**Delta = 0.**")
        st.markdown("With zero volatility, an OTM call has zero probability of reaching the strike. It expires worthless with certainty.")

    with _answer("Q12. I am long K1 calls, short K2 calls, with K1 < K2. What is my skew position ?"):
        st.markdown("**You are long skew.**")
        st.markdown(
            "You want IV at K1 to increase and IV at K2 to decrease. "
            "Long K1 means long vega at K1. Short K2 means short vega at K2."
        )
        st.markdown("A steeper skew helps both legs.")

    with _answer("Q13. Why am I rho positive when I buy a call ?"):
        st.markdown("There are two equivalent views.")
        st.markdown(
            "1. **Forward argument:** a call is long the forward. If rates rise, the forward rises, so call value rises.\n"
            "2. **Cash argument:** when you delta-hedge a long call, you sell stock and hold cash. Higher rates help that cash."
        )
        st.markdown("Both views say the same thing: long call benefits from higher rates.")

    with _answer("Q14. If volatility goes to infinity, what happens to Gamma ?"):
        st.markdown("**Gamma goes to 0.**")
        st.markdown(
            "If volatility is infinite, all option deltas converge toward 0.5 regardless of strike. "
            "If delta does not change when spot moves, gamma is 0."
        )

    with _answer("Q15. If volatility is 0, what is Gamma for an ATM option ? And for OTM or ITM ?"):
        st.markdown("**ATM: Gamma goes to infinity. OTM/ITM: Gamma = 0.**")
        st.markdown(
            "With zero vol, delta is a step function: 0 below strike and 1 above strike. "
            "At the strike, delta jumps over an infinitely small range, so gamma is infinite."
        )
        st.markdown("For OTM, delta is stuck at 0. For ITM, delta is stuck at 1. In both cases gamma is 0.")


def _render_project_setup_qa() -> None:
    _render_section_header(
        "IT & Project Setup - Why It Matters on a Trading Desk",
        "Practical questions about Python tooling, version control, and project architecture.",
    )

    with _answer("Q1. What is a virtual environment (venv) ? Why do we use one ?"):
        st.markdown("**A venv is an isolated Python installation specific to your project.**")
        st.markdown(
            "Example: an old risk report uses pandas 2.1, while a new pricer needs pandas 2.2. "
            "Without a venv, upgrading pandas for the pricer can break the risk report."
        )
        st.markdown("With a venv, each project has its own packages. Upgrading one project does not touch the other.")

    with _answer("Q2. What is requirements.txt ? Why is it important ?"):
        st.markdown("It lists every package your project needs, with versions.")
        st.markdown(
            "When someone clones the project, `pip install -r requirements.txt` installs everything in one command. "
            "Without it, they discover missing packages one by one and waste time."
        )

    with _answer("Q3. What is .gitignore ? Why do we need it ?"):
        st.markdown("It tells Git which files to never track, such as `venv/`, `*.pyc`, and `.env`.")
        st.markdown(
            "Example: if `.env` contains a market data API key and you push it to GitHub, a bot may scrape it within minutes. "
            "`.gitignore` keeps secrets, generated files, and local junk out of the repo."
        )

    with _answer("Q4. Why do we never push the venv/ folder to Git ?"):
        st.markdown("Three reasons:")
        st.markdown(
            "- **Size:** the project code may be tiny, while the venv can be hundreds of MB.\n"
            "- **OS-specific:** a venv from Windows will not work on a Linux server.\n"
            "- **Redundant:** dependency files already describe how to recreate it."
        )
        st.markdown("You send the code and dependency definition, not the entire local environment.")

    with _answer("Q5. Why do we separate engines (computation) from UI (Streamlit) ?"):
        st.markdown("So different people can work on different parts without breaking each other.")
        st.markdown(
            "A quant can improve formulas in `engines/` without knowing Streamlit. "
            "A developer can redesign charts in `ui/` without touching the math."
        )
        st.markdown("Same desk logic: structurer designs payoff, quant builds model, IT builds booking or UI.")

    with _answer("Q6. What is Git ? Why not just share code on a drive or by email ?"):
        st.markdown("Git tracks every change, who made it, when, and why. You can revert to any previous version.")
        st.markdown(
            "With a shared drive, whoever saves last can overwrite someone else's work. "
            "With email, nobody knows whether `pricer_final_FINAL_v2.py` is current."
        )
        st.markdown("With Git, people work on branches and merge changes cleanly.")

    with _answer("Q7. What is a commit ? What is a push ?"):
        st.markdown("A commit is a saved snapshot with a message. A push uploads that snapshot so others can see it.")
        st.markdown(
            "Commit is writing in your notebook. Push is publishing it. "
            "If you commit but do not push and your laptop disappears, the desk never gets your fix."
        )

    with _answer("Q8. Why do we use @st.cache_data instead of recomputing everything each time ?"):
        st.markdown("Streamlit reruns the script on every user interaction.")
        st.markdown(
            "Without caching, moving a volatility slider may recompute every chart from scratch. "
            "With caching, unchanged expensive results can be reused."
        )
        st.markdown("It is like keeping your pricing sheet open instead of rebuilding it for every client call.")

    with _answer("Q9. Why structure the project in folders instead of one big file ?"):
        st.markdown("One large file is painful to navigate and creates merge conflicts.")
        st.markdown(
            "Folders such as `engines/`, `ui/`, `data/`, and `tests/` split the project by responsibility. "
            "Each area has a clear owner and purpose."
        )

    with _answer("Q10. What are tests ? Why do we have tests/test_engines.py ?"):
        st.markdown("Tests are automated checks that verify your code still works after a change.")
        st.markdown(
            "They check things like put-call parity, American price versus European price, and par bond pricing. "
            "If someone breaks delta or duration, tests catch it before a trader uses the wrong number."
        )
        st.markdown("Tests are pre-trade checks for code.")


def _render_uv_qa() -> None:
    _render_section_header(
        "uv vs pip - Modern Python Tooling",
        "Why uv replaces pip + venv, and what pyproject.toml and lockfiles are.",
    )

    with _answer("Q1. What happens if you install packages without a virtual environment ?"):
        st.markdown("You pollute the global Python and risk breaking other projects.")
        st.markdown(
            "Example: installing a new pandas version globally can crash an older desk pricer that relies on removed APIs. "
            "With a venv, your project packages are isolated."
        )

    with _answer("Q2. Why is uv better than pip + venv for managing environments ?"):
        st.markdown("uv removes the human error of forgetting to activate the venv.")
        st.code("uv add pandas\nuv run streamlit run app.py", language="bash")
        st.markdown("`uv run` uses the project's isolated environment automatically.")

    with _answer("Q3. What is pyproject.toml ? Why is it better than requirements.txt ?"):
        st.markdown("It is the identity card of the project: name, version, dependencies, and configuration.")
        st.markdown(
            "Analogy: it is like the term sheet of a structured product. "
            "It describes the product, its components, and its constraints in one place."
        )

    with _answer("Q4. What is a lockfile (uv.lock) ? Why does it matter ?"):
        st.markdown("`pyproject.toml` gives the dependency intent. `uv.lock` gives the exact reproducible result.")
        st.markdown(
            "Analogy: `pyproject.toml` is a buy order, such as buy Apple between 180 and 200. "
            "`uv.lock` is the fill confirmation: executed at the exact price and time."
        )
        st.markdown("With a lockfile, everyone installs the same package versions months or years later.")

    with _answer("Q5. What is wrong with pip freeze ?"):
        st.markdown("`pip freeze` dumps everything installed, including packages you never asked for.")
        st.markdown(
            "Analogy: it is a photo of the whole trading book. You see every position, but no longer know which were initial trades "
            "and which were hedges."
        )
        st.markdown("uv separates intent from resolution: `pyproject.toml` is what you want; `uv.lock` is the full resolved book.")

    with _answer("Q6. uv is 10-100x faster than pip. Why does speed matter ?"):
        st.markdown("During development, you switch branches, rebuild environments, and recover from broken states.")
        st.markdown("If every rebuild takes 45 seconds, you lose time all day. If `uv sync` takes 2 seconds, iteration stays smooth.")
        st.markdown("Analogy: pip is a slow wire transfer; uv is an instant transfer.")

    with _answer("Q7. What are the classic intern mistakes with pip, and how does uv prevent them ?"):
        mistakes_df = pd.DataFrame(
            {
                "Mistake": [
                    "Forget to activate venv",
                    "pip install pandas without version",
                    "pip freeze > requirements.txt with too many packages",
                    "Two colleagues with different versions",
                    "Delete the venv and forget what to reinstall",
                ],
                "Consequence": [
                    "Installs into global Python and can break other projects",
                    "Installs latest version, which may be incompatible",
                    "Dependency file becomes polluted and hard to maintain",
                    "Creates the classic 'works on my machine' problem",
                    "Project cannot be recreated reliably",
                ],
                "How uv prevents it": [
                    "`uv run` manages the environment automatically",
                    "`uv add pandas` records a dependency constraint",
                    "`pyproject.toml` lists only direct dependencies",
                    "`uv.lock` guarantees the same resolved versions",
                    "`uv sync` recreates everything from the lockfile",
                ],
            }
        )
        st.dataframe(mistakes_df, hide_index=True, use_container_width=True)


def render_interview_page() -> None:
    with st.sidebar:
        st.markdown("### Interview")
        st.caption("Training questions grouped by topic.")

    st.header("Interview")
    tabs = st.tabs(["Greeks", "IT & Project Setup", "uv vs pip"])

    with tabs[0]:
        _render_greeks_qa()
    with tabs[1]:
        _render_project_setup_qa()
    with tabs[2]:
        _render_uv_qa()
