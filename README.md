# AI-Powered Credit Risk Assessment & Smart Loan Recommendation System

Predicts whether a bank customer is eligible for a loan from their banking +
CIBIL bureau history, recommends a loan amount/tenure/repayment method, and
projects a year-by-year repayment schedule (principal paid, interest paid,
outstanding balance) — all driven by trained ML models, not hardcoded rules.

## Structure

- `data/raw`: Source data — `Internal_Bank_Dataset.xlsx` (bank trade-line
  history), `External_Cibil_Dataset.xlsx` (bureau/CIBIL features + target
  `Approved_Flag`), `Unseen_Dataset.xlsx` (100-row holdout with a reduced,
  partially-missing feature set).
- `data/processed`: `merged_dataset.csv` -> `featured_dataset.csv` -> final
  fact tables (`fact_LoanApplication.csv`, `fact_RepaymentSchedule.csv`) and
  the consolidated `Bank_Loan_Prediction_Results.xlsx`.
- `notebooks`: run in order.
- `models`: saved classifiers/regressor + label encoders (joblib).
- `reports`: EDA summary, model performance, feature importance, eligible
  customers list.
- `figures`: EDA and model evaluation charts.
- `dashboard`: Flask web app (`app.py`, `pipeline.py`, `templates/`, `static/`)
  that serves the results in a browser, including a live prediction form.

## Notebooks (run in this order)

1. `01_Data_Understanding.ipynb` — load, inspect, merge the internal + bureau
   datasets on `PROSPECTID`.
2. `02_EDA_and_Feature_Engineering.ipynb` — handle missing-value sentinels,
   EDA, correlation-based column pruning, engineered features
   (`Income_TL_Ratio`, `Credit_Health_Score`, plus reporting-only bins),
   categorical encoding.
3. `03_Model_Training_Evaluation.ipynb` — stratified train/val/test split;
   compares Logistic Regression, Decision Tree, Random Forest and Gradient
   Boosting for risk-tier classification, and Linear Regression vs. Random
   Forest for loan-amount prediction; saves the best of each plus a
   reduced-feature classifier for the `Unseen_Dataset` schema.
4. `04_Loan_Recommendation_and_Repayment.ipynb` — turns the models into
   eligibility decisions, recommended loan amount/rate/tenure/EMI, a
   plain-language approval/rejection reason, the year-by-year repayment
   schedule, unseen-batch scoring, and the final Excel workbook. Loan sizing is
   bounded by the **"ideal zone" affordability rule** — the EMI is kept within
   **30% of net monthly income for every income level**, so basic needs and
   monthly savings stay unaffected; applicants whose income can't support a
   minimum viable loan are declined, exactly as real lenders operate. Zone labels
   (Ideal ≤30% · Moderate · Caution · High) classify any EMI-to-income ratio.

## Getting Started

```
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace notebooks/01_Data_Understanding.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_EDA_and_Feature_Engineering.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/03_Model_Training_Evaluation.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/04_Loan_Recommendation_and_Repayment.ipynb
```

## Web Dashboard (Flask)

After the notebooks have produced the models and processed data, launch the browser app:

```
python dashboard/app.py
```

Then open <http://localhost:5000>. Pages:

- **Overview** — portfolio stats, risk-tier distribution, loan-amount spread, loan policy, EDA charts.
- **Live Prediction** — enter an applicant's profile and the trained model predicts
  their risk tier + confidence and (if eligible) recommends a loan amount and EMI.
  You can **switch which model** makes the decision (any of the 4 classifiers / 2
  regressors) and a comparison table shows how *every* classifier would decide the same
  applicant. An interactive **debt-payoff simulator** lets you drag the yearly payment
  and instantly see how many years the debt takes to clear (paying less = more years and
  more total interest) with the balance remaining each year.
- **Batch Scoring** — upload a CSV/Excel of many applicants (a blank template is
  downloadable in-app, and `data/sample_applicants.csv` is a ready-made example),
  score them all at once, and download the results. Missing columns fall back to the
  dataset median.
- **Insights** — approval-rate decision curve by credit score (shows the ~650 cutoff),
  approval rates by income segment and age group, and risk exposure + projected
  interest income per tier.
- **Customers** — searchable, sortable table of every approved customer with
  per-customer loan detail and full repayment breakdown.
- **Model** — algorithm comparison, feature importance, and evaluation charts.
