# FinRisk Code Walkthrough

This guide explains how the source files work together. Start here before reading
individual lines of code.

## Request flow

1. A browser opens a Flask URL such as `/predict` or `/batch`.
2. `dashboard/app.py` receives the request and validates form values or uploaded files.
3. It calls a helper in `dashboard/pipeline.py`.
4. The pipeline loads the saved model/data artifacts, prepares features, predicts a tier,
   applies the loan policy and FOIR affordability rule, then returns normal Python data.
5. Flask passes that data to a Jinja HTML template under `dashboard/templates/`.
6. The browser renders the template with the shared styles from `style.css`.
7. Eligible-loan pages load `payoff.js`, which performs an optional client-side repayment simulation.

## Python files

### `dashboard/app.py`

This is the web controller. Every `@app.route(...)` function maps a URL to a page.
It does not contain ML mathematics: it gets input, calls the pipeline, and chooses a
template. The `inr` and `inr_compact` filters format values in Indian currency style.

### `dashboard/pipeline.py`

This is the core business and ML layer.

- `LazyRegistry` delays loading a large `.joblib` model until a request needs it.
- `credit_health_score` creates the custom 0-100 payment-health measure.
- `affordable_loan`, `compute_emi`, and `repayment_schedule` implement lending maths.
- `_prepare_features` converts 11 human-readable form inputs into the 68 feature columns
  expected by the trained model. Less-important unavailable values use dataset medians.
- `score_applicant` is the primary function: it returns tier, decision, amount, EMI,
  explanation, FOIR zone, and schedule for one applicant.
- `score_batch` does the same for many rows at once using vectorized pandas/NumPy work.

### `api/index.py`

This is only the Vercel adapter. It exposes the Flask object named `app` from
`dashboard/app.py` after putting the project folder on Python's import path.

### `notebooks/model_training_code.py`

This readable Python export mirrors the training notebook. It loads the engineered
dataset, makes train/validation/test splits, trains the risk classifier and loan
regressor, evaluates them, saves reports/charts, and serializes selected models.

## Browser files

### Templates

All HTML files use Jinja. Curly-brace expressions such as `{{ result.loan_amount }}`
print values supplied by Flask; `{% for ... %}` and `{% if ... %}` are server-side
loops and conditions. They run before the browser receives the final HTML.

- `base.html`: shared page shell, navigation, stylesheet link, and content block.
- `index.html`: portfolio overview.
- `predict.html`: manual application form and live decision output.
- `batch.html`: upload, summary, and results-table page.
- `batch_applicant.html`: expanded result for an uploaded row.
- `customers.html` and `customer_detail.html`: saved customer browsing.
- `insights.html`: approval-rate and risk-exposure views.
- `model.html`: saved evaluation metrics and training figures.

### `dashboard/static/payoff.js`

This file runs only when the page contains `id="payoff"`. It reads loan values from
HTML `data-*` attributes, calculates monthly interest/principal for a user-selected
yearly payment, and redraws the payoff summary and stacked repayment bars.

### `dashboard/static/style.css`

This is presentation only. It defines the header, cards, responsive grids, colours,
tables, forms, tier badges, affordability-zone tags, and the payoff-simulator bars.
It does not change a decision or call the model.

## Notebook order

Run the four notebooks in order: data understanding, EDA/features, training/evaluation,
then loan recommendation/repayment. Each later notebook relies on the CSV/model files
created by the earlier one.
