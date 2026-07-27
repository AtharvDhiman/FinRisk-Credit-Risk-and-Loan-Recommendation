"""
Flask dashboard for the AI-Powered Credit Risk & Smart Loan Recommendation System.

Run from the project root:
    python dashboard/app.py
then open http://localhost:5000
"""
import os
import pandas as pd
from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    abort,
    Response,
)

import pipeline as pl

app = Flask(__name__)

BATCH_RESULT_PATH = os.path.join(pl.DATA_DIR, "last_batch_results.csv")


@app.context_processor
def inject_asset_version():
    """Cache-busting token so browsers reload static assets whenever they change."""
    v = 0
    for fname in ("style.css", "payoff.js"):
        try:
            v = max(v, int(os.path.getmtime(os.path.join(app.static_folder, fname))))
        except OSError:
            pass
    return {"asset_version": v}


@app.route("/")
def index():
    return render_template("index.html", stats=pl.dashboard_stats(),
                           tier_rules=pl.TIER_RULES.reset_index().to_dict("records"))


@app.route("/customers")
def customers():
    query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "id")
    rows = pl.search_customers(query=query, sort=sort, limit=100)
    return render_template("customers.html", rows=rows, query=query, sort=sort)


@app.route("/customer/<int:customer_id>")
def customer_detail(customer_id):
    data = pl.get_customer(customer_id)
    if data is None:
        abort(404)
    # scale schedule bars relative to the largest yearly payment
    max_total = max((r["Total_Paid_Year"] for r in data["schedule"]), default=1) or 1
    return render_template("customer_detail.html", data=data, max_total=max_total)


@app.route("/predict", methods=["GET", "POST"])
def predict():
    result = comparison = error = None
    values = {f[0]: f[4] for f in pl.FORM_FIELDS}  # defaults
    clf_name = request.form.get("clf_name") or pl.DEFAULT_CLF_NAME
    reg_name = request.form.get("reg_name") or pl.DEFAULT_REG_NAME
    if request.method == "POST":
        try:
            for name, *_ in pl.FORM_FIELDS:
                values[name] = float(request.form.get(name, ""))
            result = pl.score_applicant(values, clf_name=clf_name, reg_name=reg_name)
            comparison = pl.compare_classifiers(values)
        except (ValueError, TypeError):
            error = "Please enter valid numbers in every field."
    max_total = 1
    if result and result["schedule"]:
        max_total = max(r["total_paid"] for r in result["schedule"]) or 1
    return render_template("predict.html", fields=pl.FORM_FIELDS, values=values,
                           result=result, comparison=comparison, error=error,
                           max_total=max_total, choices=pl.model_choices(),
                           clf_name=clf_name, reg_name=reg_name)


@app.route("/model")
def model():
    return render_template("model.html", report=pl.model_report())


@app.route("/insights")
def insights():
    return render_template("insights.html", data=pl.insights_data())


@app.route("/batch", methods=["GET", "POST"])
def batch():
    results = summary = error = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            error = "Please choose a CSV or Excel file to upload."
        else:
            try:
                if file.filename.lower().endswith((".xlsx", ".xls")):
                    df_in = pd.read_excel(file)
                else:
                    df_in = pd.read_csv(file)
                res = pl.score_batch(df_in)
                res.to_csv(BATCH_RESULT_PATH, index=False)
                approved = res["Decision"] == "Approved"
                summary = {
                    "total": int(len(res)),
                    "approved": int(approved.sum()),
                    "rejected": int((~approved).sum()),
                    "avg_loan": int(res.loc[approved, "Recommended_Loan"].mean()) if approved.any() else 0,
                    "total_book": int(res.loc[approved, "Recommended_Loan"].sum()),
                }
                results = res.head(200).to_dict("records")
            except Exception as exc:
                error = f"Could not process that file: {exc}"
    return render_template("batch.html", results=results, summary=summary,
                           error=error, cols=pl.BATCH_TEMPLATE_COLS)


@app.route("/batch/template")
def batch_template():
    csv = pl.batch_template_df().to_csv(index=False)
    return Response(csv, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=applicants_template.csv"})


@app.route("/batch/download")
def batch_download():
    if not os.path.exists(BATCH_RESULT_PATH):
        abort(404)
    return send_from_directory(os.path.dirname(BATCH_RESULT_PATH),
                               os.path.basename(BATCH_RESULT_PATH),
                               as_attachment=True, download_name="scored_applicants.csv")


@app.route("/figure/<path:name>")
def figure(name):
    if not name.endswith(".png"):
        abort(404)
    return send_from_directory(pl.FIGURES_DIR, name)


@app.template_filter("inr")
def inr(value):
    """Format a number in the Indian numbering system with a Rs. prefix."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    neg = value < 0
    value = abs(int(round(value)))
    s = str(value)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        s = ",".join(parts) + "," + last3
    return ("-Rs." if neg else "Rs.") + s


@app.template_filter("inr_compact")
def inr_compact(value):
    """Compact Indian currency for headline stats: crore (Cr) / lakh (L)."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e7:
        return f"{sign}Rs.{v / 1e7:,.2f} Cr"
    if v >= 1e5:
        return f"{sign}Rs.{v / 1e5:,.2f} L"
    return inr(value)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)