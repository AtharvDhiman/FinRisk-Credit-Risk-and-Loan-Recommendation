"""
Shared scoring pipeline for the Flask dashboard.

Loads the trained models and processed data once at import time, and exposes
helpers to look up existing customers and to score brand-new applicants live
with the same feature engineering and business rules used in the notebooks.
"""
import os
import numpy as np
import pandas as pd
import joblib

# ---------------------------------------------------------------------------
# Paths (this file lives in <project>/dashboard/)
# ---------------------------------------------------------------------------
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DASHBOARD_DIR)
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
FIGURES_DIR = os.path.join(PROJECT_ROOT, "figures")


def _p(*parts):
    return os.path.join(*parts)


# ---------------------------------------------------------------------------
# Load models + reference data once
# ---------------------------------------------------------------------------
CLASSIFIER = joblib.load(_p(MODELS_DIR, "risk_tier_classifier.joblib"))
REGRESSOR = joblib.load(_p(MODELS_DIR, "loan_amount_regressor.joblib"))
FEATURE_COLS = joblib.load(_p(MODELS_DIR, "feature_columns.joblib"))
ENCODERS = joblib.load(_p(MODELS_DIR, "label_encoders.joblib"))

# Every selectable model (name -> estimator), so the dashboard can let the user
# switch models and compare. Loaded from the clf_*/reg_* files notebook 03 saves.
_CLF_NAMES = ["Gradient Boosting", "Decision Tree", "Random Forest", "Logistic Regression"]
_REG_NAMES = ["Random Forest Regressor", "Linear Regression"]


def _load_registry(names, prefix):
    reg = {}
    for name in names:
        path = _p(MODELS_DIR, f"{prefix}_{name.lower().replace(' ', '_')}.joblib")
        if os.path.exists(path):
            reg[name] = joblib.load(path)
    return reg


CLASSIFIERS = _load_registry(_CLF_NAMES, "clf")
REGRESSORS = _load_registry(_REG_NAMES, "reg")

# Defaults = the best models (first row of the comparison reports)
DEFAULT_CLF_NAME = pd.read_csv(_p(REPORTS_DIR, "classifier_comparison.csv")).iloc[0]["Model"]
DEFAULT_REG_NAME = pd.read_csv(_p(REPORTS_DIR, "regressor_comparison.csv")).iloc[0]["Model"]

FEATURED = pd.read_csv(_p(DATA_DIR, "featured_dataset.csv"))

TIER_RULES = pd.read_csv(_p(REPORTS_DIR, "dim_risk_tier.csv")).set_index("RiskTierID")

# Median value for every model feature -- used to fill in fields a live
# applicant form does not ask about, so the model always receives a complete row.
FEATURE_MEDIANS = FEATURED[FEATURE_COLS].median(numeric_only=True).to_dict()

# Income winsorization bounds (same 1st/99th pct used in notebook 02)
INCOME_LOW, INCOME_HIGH = FEATURED["NETMONTHLYINCOME"].quantile([0.01, 0.99])

TIER_META = {
    "P1": {"label": "Best Risk",     "eligible": True},
    "P2": {"label": "Good Risk",     "eligible": True},
    "P3": {"label": "Moderate Risk", "eligible": True},
    "P4": {"label": "High Risk",     "eligible": False},
}


# ---------------------------------------------------------------------------
# Credit_Health_Score normalization stats (recreated from the training data so
# a single new applicant is scored on the same scale as notebook 02)
# ---------------------------------------------------------------------------
def _minmax_bounds(series):
    return float(series.min()), float(series.max())


_pay_ratio_full = 1 - (FEATURED["Tot_Missed_Pmnt"] / FEATURED["Total_TL"].replace(0, 1))
CHS_BOUNDS = {
    "Credit_Score": _minmax_bounds(FEATURED["Credit_Score"]),
    "Age_Oldest_TL": _minmax_bounds(FEATURED["Age_Oldest_TL"]),
    "pay_ratio": _minmax_bounds(_pay_ratio_full),
    "Tot_Missed_Pmnt": _minmax_bounds(FEATURED["Tot_Missed_Pmnt"]),
    "num_times_delinquent": _minmax_bounds(FEATURED["num_times_delinquent"]),
    "num_times_30p_dpd": _minmax_bounds(FEATURED["num_times_30p_dpd"]),
}


def _mm(value, key):
    lo, hi = CHS_BOUNDS[key]
    return (value - lo) / (hi - lo + 1e-9)


def credit_health_score(credit_score, age_oldest_tl, tot_missed, total_tl,
                        num_delinquent, num_30p_dpd):
    pay_ratio = 1 - (tot_missed / (total_tl if total_tl else 1))
    positive = (
        0.5 * _mm(credit_score, "Credit_Score")
        + 0.3 * _mm(age_oldest_tl, "Age_Oldest_TL")
        + 0.2 * _mm(pay_ratio, "pay_ratio")
    )
    negative = (
        0.4 * _mm(tot_missed, "Tot_Missed_Pmnt")
        + 0.35 * _mm(num_delinquent, "num_times_delinquent")
        + 0.25 * _mm(num_30p_dpd, "num_times_30p_dpd")
    )
    return round(max(positive - 0.5 * negative, 0.0) * 100, 2)


# ---------------------------------------------------------------------------
# Business calculations
# ---------------------------------------------------------------------------
def risk_adjustment(chs):
    return float(np.clip(0.6 + 0.4 * (chs / 100.0), 0.6, 1.0))


MIN_VIABLE_LOAN = 50000  # below this the income is too low for the product

# The "Ideal Zone": keep the EMI under 30% of net monthly income for EVERYONE
# (low or high earner). Below 30%, basic needs (food, rent, utilities, education)
# and monthly savings/investments stay unaffected -- so this is the sizing basis.
IDEAL_FOIR = 0.30


def max_foir(net_monthly_income=None):
    """EMI ceiling as a share of net monthly income -- a flat 30% ideal/safe zone for
    all income levels (income arg kept for call compatibility)."""
    return IDEAL_FOIR


def foir_zone(emi_pct):
    """Classify an EMI-to-income ratio into an affordability zone (30% is the ideal
    ceiling, so it counts as Ideal)."""
    if emi_pct <= 30:
        return ("Ideal", "ideal")
    if emi_pct <= 40:
        return ("Moderate", "moderate")
    if emi_pct <= 50:
        return ("Caution", "caution")
    return ("High risk", "high")


def affordable_loan(net_monthly_income, annual_rate_pct, tenure_years):
    """Largest loan whose EMI stays within the FOIR limit for this actual income."""
    if net_monthly_income <= 0:
        return 0.0
    max_emi = max_foir(net_monthly_income) * net_monthly_income
    r = (annual_rate_pct / 100.0) / 12.0
    n = tenure_years * 12
    if r == 0:
        return max_emi * n
    annuity_factor = ((1 + r) ** n - 1) / (r * (1 + r) ** n)
    return max_emi * annuity_factor


def compute_emi(principal, annual_rate_pct, tenure_years):
    if tenure_years <= 0 or principal <= 0:
        return 0.0
    r = (annual_rate_pct / 100.0) / 12.0
    n = tenure_years * 12
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def repayment_schedule(principal, annual_rate_pct, tenure_years):
    """Year-by-year amortization for a single loan."""
    emi = compute_emi(principal, annual_rate_pct, tenure_years)
    r = (annual_rate_pct / 100.0) / 12.0
    balance = principal
    rows = []
    for year in range(1, int(tenure_years) + 1):
        principal_paid = interest_paid = 0.0
        for _ in range(12):
            interest = balance * r
            principal_component = min(emi - interest, balance)
            balance = max(balance - principal_component, 0.0)
            principal_paid += principal_component
            interest_paid += interest
        rows.append({
            "year": year,
            "emi": round(emi),
            "principal_paid": round(principal_paid),
            "interest_paid": round(interest_paid),
            "total_paid": round(principal_paid + interest_paid),
            "outstanding": round(balance),
        })
    return rows


def build_reason(tier, credit_score, income, tot_missed, num_delinquent,
                 age_oldest_tl, enq_l3m):
    reasons = []
    if tier in ("P1", "P2", "P3"):
        if tot_missed == 0:
            reasons.append("No missed payments")
        if num_delinquent == 0:
            reasons.append("No delinquency history")
        if income >= 30000:
            reasons.append(f"Stable income Rs.{income:,.0f}/mo")
        if age_oldest_tl >= 60:
            reasons.append(f"Mature credit ({age_oldest_tl:.0f} months)")
        if enq_l3m == 0:
            reasons.append("No recent credit enquiries")
        if not reasons:
            reasons.append(f"Acceptable overall credit profile (score {credit_score:.0f})")
    else:
        if tot_missed > 0:
            reasons.append(f"{int(tot_missed)} missed payment(s) on record")
        if num_delinquent > 0:
            reasons.append("Delinquency history recorded")
        if age_oldest_tl < 24:
            reasons.append(f"Limited credit history ({age_oldest_tl:.0f} months)")
        if enq_l3m >= 3:
            reasons.append(f"High recent enquiry volume ({int(enq_l3m)} in last 3 months)")
        if not reasons:
            reasons.append(f"Low credit score ({credit_score:.0f})")
    return "; ".join(reasons)


# ---------------------------------------------------------------------------
# Form field spec (drivers the live-prediction page asks for)
# ---------------------------------------------------------------------------
# (internal_name, plain-language label, min, max, default) -- labels are written for
# ordinary users, not banking staff. Only the label (2nd item) is shown in the UI.
FORM_FIELDS = [
    ("Credit_Score",         "Credit Score (CIBIL, 300–900)",              300, 900, 700),
    ("NETMONTHLYINCOME",     "Monthly Take-Home Income (₹)",               0,   500000, 35000),
    ("AGE",                  "Age (years)",                                18,  75, 35),
    ("Total_TL",             "Total Loans & Credit Cards (ever taken)",    0,   50, 5),
    ("Tot_Active_TL",        "Loans & Credit Cards Currently Running",      0,   40, 2),
    ("Tot_Missed_Pmnt",      "Total Missed Payments (ever)",               0,   30, 0),
    ("num_times_delinquent", "Times Seriously Behind on Payments",         0,   30, 0),
    ("num_times_30p_dpd",    "Times a Payment Was 30+ Days Late",          0,   30, 0),
    ("Age_Oldest_TL",        "Age of Oldest Loan/Card (in months)",        0, 400, 72),
    ("enq_L3m",              "New Loan/Card Applications (last 3 months)",  0, 20, 0),
    ("Time_With_Curr_Empr",  "Time at Current Job (in months)",            0, 600, 48),
]


def _prepare_features(inputs: dict):
    """Turn raw form driver values into the full model feature row + the derived
    values reused by the reason/loan logic."""
    row = dict(FEATURE_MEDIANS)  # start from median profile

    d = {k: float(inputs[k]) for k, *_ in FORM_FIELDS}
    income_capped = float(np.clip(d["NETMONTHLYINCOME"], INCOME_LOW, INCOME_HIGH))
    active_tl = d["Tot_Active_TL"]
    income_tl_ratio = round(income_capped / (active_tl if active_tl else 1), 2)
    chs = credit_health_score(d["Credit_Score"], d["Age_Oldest_TL"], d["Tot_Missed_Pmnt"],
                              d["Total_TL"], d["num_times_delinquent"], d["num_times_30p_dpd"])

    row.update({
        "Credit_Score": d["Credit_Score"],
        "NETMONTHLYINCOME_Capped": income_capped,
        "AGE": d["AGE"],
        "Total_TL": d["Total_TL"],
        "Tot_Active_TL": active_tl,
        "Tot_Missed_Pmnt": d["Tot_Missed_Pmnt"],
        "num_times_delinquent": d["num_times_delinquent"],
        "num_times_30p_dpd": d["num_times_30p_dpd"],
        "Age_Oldest_TL": d["Age_Oldest_TL"],
        "enq_L3m": d["enq_L3m"],
        "Time_With_Curr_Empr": d["Time_With_Curr_Empr"],
        "Income_TL_Ratio": income_tl_ratio,
        "Credit_Health_Score": chs,
    })
    X = pd.DataFrame([[row[c] for c in FEATURE_COLS]], columns=FEATURE_COLS)
    return X, d, income_capped, income_tl_ratio, chs


def score_applicant(inputs: dict, clf_name=None, reg_name=None) -> dict:
    """Score a brand-new applicant. clf_name / reg_name pick which trained model to
    use; when omitted, the best models are used."""
    clf = CLASSIFIERS.get(clf_name, CLASSIFIER)
    reg = REGRESSORS.get(reg_name, REGRESSOR)
    clf_used = clf_name if clf_name in CLASSIFIERS else DEFAULT_CLF_NAME
    reg_used = reg_name if reg_name in REGRESSORS else DEFAULT_REG_NAME

    X, d, income_capped, income_tl_ratio, chs = _prepare_features(inputs)

    tier = str(clf.predict(X)[0])
    proba = clf.predict_proba(X)[0]
    confidence = round(float(proba.max()) * 100, 1)

    rule = TIER_RULES.loc[tier]
    eligible = tier in ("P1", "P2", "P3")

    income_too_low = False
    if eligible:
        interest = float(rule["Interest_Rate_Pct"])
        tenure = int(rule["Tenure_Years"])
        raw_amount = max(float(reg.predict(X)[0]), 0.0)
        # cap by tier max AND by affordability. The affordability limit is the 30%
        # ideal-zone EMI scaled by a credit-risk factor (from Credit_Health_Score),
        # so a weaker payment history -> smaller loan, while the EMI stays <= 30%.
        risk_adj = risk_adjustment(chs)
        affordable = affordable_loan(d["NETMONTHLYINCOME"], interest, tenure) * risk_adj
        loan_amount = round(min(raw_amount, rule["Max_Loan_Amount"], affordable), -2)
        if loan_amount < MIN_VIABLE_LOAN:
            # income can't support the minimum ticket size -> decline
            eligible = False
            income_too_low = True
            loan_amount = interest = tenure = emi = total_payable = total_interest = 0
            schedule = []
        else:
            emi = round(compute_emi(loan_amount, interest, tenure))
            schedule = repayment_schedule(loan_amount, interest, tenure)
            total_payable = emi * tenure * 12
            total_interest = max(total_payable - loan_amount, 0)
    else:
        loan_amount = 0
        interest = tenure = emi = total_payable = total_interest = 0
        schedule = []

    net_income = d["NETMONTHLYINCOME"]
    emi_to_income = round(emi / net_income * 100, 1) if net_income > 0 else 0
    foir_limit = round(max_foir(net_income) * 100)
    zone_label, zone_cls = foir_zone(emi_to_income)

    if income_too_low:
        reason = (f"Would qualify on credit risk (tier {tier}), but stated income "
                  f"Rs.{net_income:,.0f}/mo is too low to service the minimum "
                  f"Rs.{MIN_VIABLE_LOAN:,} loan affordably.")
        eligibility_status = "Rejected — insufficient income"
    else:
        reason = build_reason(tier, d["Credit_Score"], income_capped, d["Tot_Missed_Pmnt"],
                              d["num_times_delinquent"], d["Age_Oldest_TL"], d["enq_L3m"])
        eligibility_status = rule["Eligibility_Status"]

    return {
        "tier": tier,
        "tier_label": TIER_META[tier]["label"],
        "eligible": eligible,
        "eligibility_status": eligibility_status,
        "confidence": confidence,
        "credit_health_score": chs,
        "income_tl_ratio": income_tl_ratio,
        "loan_amount": loan_amount,
        "interest_rate": interest,
        "tenure_years": tenure,
        "repayment_method": rule["Repayment_Method"],
        "monthly_emi": emi,
        "total_payable": total_payable,
        "total_interest": total_interest,
        "emi_to_income": emi_to_income,
        "foir_limit": foir_limit,
        "foir_zone": zone_label,
        "foir_zone_cls": zone_cls,
        "net_income": net_income,
        "reason": reason,
        "schedule": schedule,
        "clf_used": clf_used,
        "reg_used": reg_used,
    }


def compare_classifiers(inputs: dict):
    """Run every trained classifier on the same applicant so the user can see
    whether the decision changes between models."""
    X, _, _, _, _ = _prepare_features(inputs)
    rows = []
    for name, clf in CLASSIFIERS.items():
        tier = str(clf.predict(X)[0])
        conf = round(float(clf.predict_proba(X)[0].max()) * 100, 1)
        rows.append({
            "model": name,
            "tier": tier,
            "tier_label": TIER_META[tier]["label"],
            "decision": "Approved" if tier in ("P1", "P2", "P3") else "Rejected",
            "eligible": tier in ("P1", "P2", "P3"),
            "confidence": conf,
            "is_default": name == DEFAULT_CLF_NAME,
        })
    # keep them in the report's ranked order
    order = {n: i for i, n in enumerate(_CLF_NAMES)}
    rows.sort(key=lambda r: order.get(r["model"], 99))
    return rows


def model_choices():
    """Available models + their validation metric, for the selector dropdowns."""
    clf_cmp = pd.read_csv(_p(REPORTS_DIR, "classifier_comparison.csv"))
    reg_cmp = pd.read_csv(_p(REPORTS_DIR, "regressor_comparison.csv"))
    classifiers = [{"name": r["Model"], "metric": f'{r["Val_Accuracy"]*100:.2f}% acc',
                    "is_default": r["Model"] == DEFAULT_CLF_NAME}
                   for _, r in clf_cmp.iterrows() if r["Model"] in CLASSIFIERS]
    regressors = [{"name": r["Model"], "metric": f'R2 {r["Val_R2"]:.3f}',
                   "is_default": r["Model"] == DEFAULT_REG_NAME}
                  for _, r in reg_cmp.iterrows() if r["Model"] in REGRESSORS]
    return {"classifiers": classifiers, "regressors": regressors}


# ---------------------------------------------------------------------------
# Existing-customer lookups (from the precomputed fact tables)
# ---------------------------------------------------------------------------
_LOAN_APP = None
_REPAYMENT = None
_ALL_APPS = None


def _load_facts():
    global _LOAN_APP, _REPAYMENT, _ALL_APPS
    if _LOAN_APP is None:
        _LOAN_APP = pd.read_csv(_p(DATA_DIR, "fact_LoanApplication.csv"))
        _REPAYMENT = pd.read_csv(_p(DATA_DIR, "fact_RepaymentSchedule.csv"))
        eligible_ids = set(_LOAN_APP["CustomerID"])
        _ALL_APPS = FEATURED[["PROSPECTID", "Approved_Flag", "Credit_Score",
                              "NETMONTHLYINCOME", "Credit_Score_Band"]].copy()
        _ALL_APPS["Is_Eligible"] = _ALL_APPS["PROSPECTID"].isin(eligible_ids).astype(int)
    return _LOAN_APP, _REPAYMENT, _ALL_APPS


def dashboard_stats():
    loan_app, repayment, all_apps = _load_facts()
    tier_counts = all_apps["Approved_Flag"].value_counts().to_dict()
    perf = pd.read_csv(_p(REPORTS_DIR, "model_performance.csv"))
    perf_dict = dict(zip(perf["Metric"].str.strip(), perf["Value"]))

    # Spread of recommended loan sizes across all eligible customers -- shows the
    # model does NOT give everyone the same amount.
    band_edges = [0, 300000, 600000, 900000, 1200000, 1500000, 2500001]
    band_labels = ["< 3L", "3-6L", "6-9L", "9-12L", "12-15L", "15-25L"]
    bands = pd.cut(loan_app["Recommended_Loan_Amount"], bins=band_edges,
                   labels=band_labels, include_lowest=True)
    loan_distribution = [(lbl, int(bands.value_counts().get(lbl, 0))) for lbl in band_labels]

    return {
        "total_customers": int(len(all_apps)),
        "eligible_customers": int(all_apps["Is_Eligible"].sum()),
        "rejected_customers": int((all_apps["Is_Eligible"] == 0).sum()),
        "total_loan_book": int(loan_app["Recommended_Loan_Amount"].sum()),
        "avg_loan": int(loan_app["Recommended_Loan_Amount"].mean()),
        "median_loan": int(loan_app["Recommended_Loan_Amount"].median()),
        "tier_counts": {t: int(tier_counts.get(t, 0)) for t in ["P1", "P2", "P3", "P4"]},
        "loan_distribution": loan_distribution,
        "best_classifier": perf_dict.get("Best Classifier", "-"),
        "test_accuracy": perf_dict.get("Test Accuracy", "-"),
        "best_regressor": perf_dict.get("Best Regressor", "-"),
        "regression_r2": perf_dict.get("Regression Test R2", "-"),
    }


def search_customers(query="", sort="id", limit=100):
    loan_app, _, all_apps = _load_facts()
    df = loan_app.copy()
    if query:
        try:
            cid = int(query)
            df = df[df["CustomerID"] == cid]
        except ValueError:
            df = df.iloc[0:0]
    if sort == "amount_desc":
        df = df.sort_values("Recommended_Loan_Amount", ascending=False)
    elif sort == "amount_asc":
        df = df.sort_values("Recommended_Loan_Amount", ascending=True)
    else:  # natural customer order -> shows the real spread of loan sizes
        df = df.sort_values("CustomerID")
    return df.head(limit).to_dict("records")


def get_customer(customer_id):
    loan_app, repayment, all_apps = _load_facts()
    cid = int(customer_id)
    app_row = all_apps[all_apps["PROSPECTID"] == cid]
    if app_row.empty:
        return None
    app_row = app_row.iloc[0].to_dict()

    loan_row = loan_app[loan_app["CustomerID"] == cid]
    sched = repayment[repayment["CustomerID"] == cid].sort_values("Year")

    result = {"customer_id": cid, "application": app_row, "eligible": bool(app_row["Is_Eligible"])}
    if not loan_row.empty:
        loan = loan_row.iloc[0].to_dict()
        income = app_row.get("NETMONTHLYINCOME", 0) or 0
        loan["EMI_to_Income"] = round(loan["Monthly_EMI"] / income * 100, 1) if income > 0 else 0
        loan["FOIR_Limit"] = round(max_foir(income) * 100)
        loan["FOIR_Zone"], loan["FOIR_Zone_Cls"] = foir_zone(loan["EMI_to_Income"])
        result["loan"] = loan
        result["schedule"] = sched.to_dict("records")
    else:
        result["loan"] = None
        result["schedule"] = []
    return result


def model_report():
    clf_cmp = pd.read_csv(_p(REPORTS_DIR, "classifier_comparison.csv"))
    reg_cmp = pd.read_csv(_p(REPORTS_DIR, "regressor_comparison.csv"))
    importance = pd.read_csv(_p(REPORTS_DIR, "feature_importance.csv")).head(15)
    perf = pd.read_csv(_p(REPORTS_DIR, "model_performance.csv"))
    return {
        "classifier_comparison": clf_cmp.to_dict("records"),
        "regressor_comparison": reg_cmp.to_dict("records"),
        "feature_importance": importance.to_dict("records"),
        "performance": perf.to_dict("records"),
    }


# ---------------------------------------------------------------------------
# FEATURE 1: Insights -- segment analytics + credit-score decision curve
# ---------------------------------------------------------------------------
def _rate_table(df, group_col, order=None):
    """Approval rate (%) and count for each value of a grouping column."""
    df = df.dropna(subset=[group_col])
    grouped = df.groupby(group_col, observed=True)["Is_Eligible"]
    out = grouped.agg(["mean", "count"]).reset_index()
    out["approval_rate"] = (out["mean"] * 100).round(1)
    rows = {r[group_col]: (float(r["approval_rate"]), int(r["count"])) for _, r in out.iterrows()}
    keys = order if order else list(rows.keys())
    return [(str(k), rows[k][0], rows[k][1]) for k in keys if k in rows]


def insights_data():
    loan_app, _, _ = _load_facts()
    df = FEATURED.copy()
    df["Is_Eligible"] = df["Approved_Flag"].isin(["P1", "P2", "P3"]).astype(int)

    # Decision curve: approval rate by fine credit-score bands (shows the ~650 cliff)
    score_bins = [0, 620, 640, 650, 660, 670, 700, 750, 900]
    score_labels = ["<620", "620-639", "640-649", "650-659", "660-669",
                    "670-699", "700-749", "750+"]
    df["score_band"] = pd.cut(df["Credit_Score"], bins=score_bins,
                              labels=score_labels, right=False)
    threshold_curve = _rate_table(df, "score_band", order=score_labels)

    income_order = ["Low (<15K)", "Lower-Mid (15K-30K)", "Mid (30K-60K)",
                    "Upper-Mid (60K-100K)", "High (100K+)"]
    age_order = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

    # Risk exposure + projected interest income per tier
    exposure = (loan_app.groupby("RiskTierID")
                .agg(customers=("CustomerID", "count"),
                     loan_book=("Recommended_Loan_Amount", "sum"),
                     interest_income=("Total_Interest_Payable", "sum"),
                     avg_loan=("Recommended_Loan_Amount", "mean"))
                .reindex(["P1", "P2", "P3"]).dropna(how="all").reset_index())
    exposure_rows = [{
        "tier": r["RiskTierID"],
        "customers": int(r["customers"]),
        "loan_book": float(r["loan_book"]),
        "interest_income": float(r["interest_income"]),
        "avg_loan": float(r["avg_loan"]),
    } for _, r in exposure.iterrows()]

    return {
        "threshold_curve": threshold_curve,
        "by_income": _rate_table(df, "Income_Segment", order=income_order),
        "by_age": _rate_table(df, "Age_Group", order=age_order),
        "exposure": exposure_rows,
        "total_interest_income": float(loan_app["Total_Interest_Payable"].sum()),
    }


# ---------------------------------------------------------------------------
# FEATURE 2: Batch scoring -- score an uploaded file of many applicants
# ---------------------------------------------------------------------------
BATCH_TEMPLATE_COLS = [name for name, *_ in FORM_FIELDS]
MAX_BATCH_ROWS = 2000


def batch_template_df():
    """A blank template with one example row for users to fill in."""
    example = {name: default for name, _, _, _, default in FORM_FIELDS}
    return pd.DataFrame([example], columns=BATCH_TEMPLATE_COLS)


def score_batch(df_in):
    """Score every row of an uploaded applicant file. Missing driver columns are
    filled from the dataset median, so partial files still work."""
    df = df_in.head(MAX_BATCH_ROWS).copy()
    results = []
    for idx, r in df.iterrows():
        inputs = {}
        for name, *_ in FORM_FIELDS:
            val = r.get(name, None)
            try:
                val = float(val)
                if pd.isna(val):
                    raise ValueError
            except (ValueError, TypeError):
                val = float(FEATURED[name].median())
            inputs[name] = val
        res = score_applicant(inputs)
        results.append({
            "Row": int(idx) + 1,
            "Credit_Score": int(inputs["Credit_Score"]),
            "Net_Monthly_Income": int(inputs["NETMONTHLYINCOME"]),
            "Predicted_Tier": res["tier"],
            "Decision": "Approved" if res["eligible"] else "Rejected",
            "Confidence_%": res["confidence"],
            "Recommended_Loan": res["loan_amount"],
            "Interest_Rate_%": res["interest_rate"],
            "Tenure_Years": res["tenure_years"],
            "Monthly_EMI": res["monthly_emi"],
            "Reason": res["reason"],
        })
    return pd.DataFrame(results)
