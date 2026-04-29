# Pricer

This project is a Streamlit-based derivatives pricer built for an applied derivatives course.

The goal is to create a clean local version of the deployed SKEMA-style pricer and progressively implement the main product pages used in class:
- Options
- Bonds
- Turbo Certificates
- Discount Certificates
- Bonus Certificates
- Interview / training questions

## What We Are Trying To Build

We are building an educational pricing app with two objectives:

1. Provide correct pricing and risk calculations for common structured products and vanilla derivatives.
2. Present those calculations in a simple interface that is useful for coursework, intuition building, and interview preparation.

The app is not just meant to output a price. It should also explain the product through:
- Greeks and hedge metrics
- payoff views
- sensitivity charts
- trading shortcuts
- interview-style finance questions

## Current Status

The core implementation phase is complete. The app now includes:

- **uv-managed environment**: Fast, reproducible setup with `uv`.
- **Streamlit interface**: Responsive dashboard with sidebar navigation.
- **Robust Engines**: Mathematically correct pricing for:
    - **European Options**: Black-Scholes with carry-aware forward pricing (r, q, repo).
    - **Bonds**: YTM, duration, convexity, and sensitivity analytics.
    - **Turbo Certificates**: Barrier-aware pricing and leverage metrics.
    - **Discount & Bonus Certificates**: Yield-to-maturity and barrier probability views.
- **Comprehensive Greeks**: Delta, Gamma, Vega, Rho, Vanna, and Theta.
- **Unit Testing**: 100% engine coverage for all pricing logic.

## Project Approach

The project is being built in small passes.

### Pass 1
- Build the pricing engine
- Build the first usable `Options` page
- Add tests

### Pass 2
- Add options analytics:
  - Gamma PnL calculator
  - trading shortcuts
  - price vs spot chart
  - price vs volatility chart

### Pass 3
- Refine layout and output formatting
- Extend parity with the deployed app
- Add the remaining product pages one by one

## Code Structure

The project follows a strict separation between pricing logic and UI:

- **`app.py`**: Entrypoint and page routing.
- **`pricer/engines/`**: Pure Python modules for financial calculations. These are independent of Streamlit and fully testable.
- **`pricer/ui/`**: Layout and visualization code for each product page.
- **`tests/`**: Unit tests verifying engine correctness against reference benchmarks.

## Run The App

```bash
uv sync
uv run streamlit run app.py
```

## Run Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Near-Term Roadmap

Next steps for the project:
- **Enhanced Analytics**: Add Gamma PnL calculators and sensitivity heatmaps.
- **Interactive Charts**: Implement Plotly-based payoff and risk charts for all products.
- **Interview Training**: Expand the interview section with more randomized scenarios and trading riddles.
- **Performance**: Optimize engine calculations for real-time sensitivity sliders.

## Philosophy

This project is being built as a course tool, not as a black-box pricer.

That means the implementation should stay:
- financially correct
- easy to read
- modular
- testable
- useful for learning how the products behave, not only for producing a number
