from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, Image, KeepTogether, Flowable)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "pdf" / "FinRisk_Internship_Project_Report.pdf"

BLUE = colors.HexColor("#12355B")
TEAL = colors.HexColor("#0F766E")
LIGHT = colors.HexColor("#EAF2F8")
TEXT = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#52616B")
GREEN = colors.HexColor("#0F766E")
ORANGE = colors.HexColor("#C2410C")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27,
                           leading=33, textColor=BLUE, alignment=TA_CENTER, spaceAfter=12))
styles.add(ParagraphStyle(name="SubTitleX", parent=styles["Normal"], fontName="Helvetica", fontSize=12,
                           leading=17, textColor=MUTED, alignment=TA_CENTER, spaceAfter=20))
styles.add(ParagraphStyle(name="H1X", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=17,
                           leading=22, textColor=BLUE, spaceBefore=10, spaceAfter=9))
styles.add(ParagraphStyle(name="H2X", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12,
                           leading=16, textColor=TEAL, spaceBefore=9, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.3,
                           leading=14, textColor=TEXT, spaceAfter=6))
styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontName="Helvetica", fontSize=8,
                           leading=11, textColor=TEXT, spaceAfter=3))
styles.add(ParagraphStyle(name="TableHeadX", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8,
                           leading=10, textColor=colors.white, spaceAfter=0))
styles.add(ParagraphStyle(name="CalloutX", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10,
                           leading=15, textColor=BLUE, backColor=LIGHT, borderColor=colors.HexColor("#B8D7EB"),
                           borderWidth=0.5, borderPadding=8, spaceBefore=5, spaceAfter=10))

def P(text, style="BodyX"):
    return Paragraph(text, styles[style])

def bullet(text):
    return Paragraph("- " + text, styles["BodyX"])

def table(rows, widths, header=True, font=8):
    cooked = []
    for idx, row in enumerate(rows):
        style = "TableHeadX" if header and idx == 0 else "SmallX"
        cooked.append([P(str(c), style) for c in row])
    t = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    for r in range(1 if header else 0, len(rows)):
        if r % 2 == 0:
            cmds.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F8FAFC")))
    t.setStyle(TableStyle(cmds))
    return t

def img(name, width=15.5*cm):
    path = ROOT / "figures" / name
    if not path.exists():
        return Spacer(1, 1)
    im = Image(str(path))
    im._restrictSize(width, 10.5*cm)
    return im

def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.line(1.5*cm, h-1.25*cm, w-1.5*cm, h-1.25*cm)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(BLUE)
    canvas.drawString(1.5*cm, h-1.0*cm, "FinRisk - Credit Risk Assessment & Smart Loan Recommendation")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(w-1.5*cm, 1.0*cm, f"Page {doc.page}")
    canvas.drawString(1.5*cm, 1.0*cm, "Internship Project Report")
    canvas.restoreState()


class UMLComponentDiagram(Flowable):
    """Native-vector UML-style component diagram for the FinRisk architecture."""
    def __init__(self, width=16.0*cm, height=16.1*cm):
        Flowable.__init__(self)
        self.width, self.height = width, height

    def wrap(self, avail_w, avail_h):
        return min(self.width, avail_w), self.height

    def draw_box(self, c, x, y, w, h, title, lines, fill=colors.HexColor("#EAF2F8")):
        c.setFillColor(fill); c.setStrokeColor(BLUE); c.setLineWidth(.8)
        c.roundRect(x, y, w, h, 7, fill=1, stroke=1)
        c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x+w/2, y+h-15, "<<component>>")
        c.setFont("Helvetica-Bold", 9); c.drawCentredString(x+w/2, y+h-28, title)
        c.setFillColor(TEXT); c.setFont("Helvetica", 7.1)
        for i, line in enumerate(lines):
            c.drawCentredString(x+w/2, y+h-42-(i*10), line)

    def arrow(self, c, x1, y1, x2, y2, label="", dashed=False):
        c.saveState(); c.setStrokeColor(TEAL); c.setFillColor(TEAL); c.setLineWidth(1.1)
        if dashed: c.setDash(4, 3)
        c.line(x1, y1, x2, y2)
        import math
        ang = math.atan2(y2-y1, x2-x1)
        for offset in (2.55, -2.55):
            c.line(x2, y2, x2-7*math.cos(ang+offset), y2-7*math.sin(ang+offset))
        c.restoreState()
        if label:
            c.setFillColor(MUTED); c.setFont("Helvetica-Oblique", 6.8)
            c.drawCentredString((x1+x2)/2, (y1+y2)/2+4, label)

    def draw(self):
        c = self.canv; w, h = self.width, self.height
        c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 13)
        c.drawString(0, h-14, "UML-style component diagram")
        c.setFillColor(MUTED); c.setFont("Helvetica", 8)
        c.drawString(0, h-27, "Main software components and their dependencies in FinRisk")
        # Components
        self.draw_box(c, 5, h-116, 128, 80, "Data notebooks", ["01 Data understanding", "02 EDA & features", "03 Model training", "04 Loan policy"], colors.HexColor("#E8F3EC"))
        self.draw_box(c, 171, h-116, 128, 80, "Saved artifacts", ["joblib classifiers", "joblib regressors", "processed CSV data", "reports and figures"], colors.HexColor("#FFF4E5"))
        self.draw_box(c, 5, h-242, 150, 84, "Flask dashboard - app.py", ["HTTP routes", "form / upload validation", "HTML template rendering", "CSV download"], colors.HexColor("#EAF2F8"))
        self.draw_box(c, 181, h-242, 150, 84, "Scoring pipeline - pipeline.py", ["feature preparation", "ML prediction", "FOIR / eligibility rules", "EMI and repayment schedule"], colors.HexColor("#EAF2F8"))
        self.draw_box(c, 5, h-370, 150, 80, "Presentation layer", ["Jinja templates", "CSS + payoff JavaScript", "overview, model, insights", "customer and batch pages"], colors.HexColor("#F3E8FF"))
        self.draw_box(c, 181, h-370, 150, 80, "Deployment layer", ["api/index.py", "Gunicorn", "render.yaml", "vercel.json"], colors.HexColor("#F3E8FF"))
        # Dependencies
        self.arrow(c, 133, h-83, 171, h-83, "creates")
        self.arrow(c, 155, h-204, 181, h-204, "calls")
        self.arrow(c, 256, h-166, 256, h-116, "loads")
        self.arrow(c, 80, h-242, 80, h-290, "renders")
        self.arrow(c, 331, h-205, 331, h-290, "serves", dashed=True)
        self.arrow(c, 155, h-335, 181, h-335, "uses")
        c.setFillColor(MUTED); c.setFont("Helvetica", 7.3)
        c.drawString(5, 15, "Solid arrow: direct runtime call or data dependency. Dashed arrow: hosting / deployment relationship.")


class ProjectFlowDiagram(Flowable):
    """Native-vector end-to-end flow diagram for the FinRisk data lifecycle."""
    def __init__(self, width=16.0*cm, height=16.0*cm):
        Flowable.__init__(self)
        self.width, self.height = width, height

    def wrap(self, avail_w, avail_h):
        return min(self.width, avail_w), self.height

    def box(self, c, x, y, w, h, title, lines, fill):
        c.setFillColor(fill); c.setStrokeColor(BLUE); c.setLineWidth(.8)
        c.roundRect(x, y, w, h, 8, fill=1, stroke=1)
        c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 9); c.drawCentredString(x+w/2, y+h-18, title)
        c.setFillColor(TEXT); c.setFont("Helvetica", 7.2)
        for i, ln in enumerate(lines): c.drawCentredString(x+w/2, y+h-33-i*10, ln)

    def down(self, c, x, y1, y2):
        c.setStrokeColor(TEAL); c.setFillColor(TEAL); c.setLineWidth(1.25); c.line(x, y1, x, y2)
        c.line(x, y2, x-4, y2+7); c.line(x, y2, x+4, y2+7)

    def draw(self):
        c = self.canv; w, h = self.width, self.height; bw=260; bh=57; x=(w-bw)/2
        c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 13); c.drawString(0, h-14, "End-to-end project flow")
        c.setFillColor(MUTED); c.setFont("Helvetica", 8); c.drawString(0, h-27, "How data moves from input files to loan decisions and downloadable results")
        nodes = [
            (h-98, "1. Data sources", ["Internal bank data", "CIBIL bureau data"], colors.HexColor("#E8F3EC")),
            (h-178, "2. Merge and understand", ["Join on PROSPECTID", "51,336 usable applicants"], colors.HexColor("#EAF2F8")),
            (h-258, "3. Clean and explore", ["Missing values, outliers", "redundancy and EDA"], colors.HexColor("#EAF2F8")),
            (h-338, "4. Engineer features", ["Income_TL_Ratio", "Credit_Health_Score"], colors.HexColor("#FFF4E5")),
            (h-418, "5. Train and evaluate", ["Risk classifier P1-P4", "Loan amount regressors"], colors.HexColor("#FFF4E5")),
            (h-498, "6. Save artifacts", ["Joblib models and feature list", "Reports, figures, fact tables"], colors.HexColor("#F3E8FF")),
            (h-578, "7. Score applicant", ["Risk tier + confidence", "Policy cap + FOIR + EMI"], colors.HexColor("#F3E8FF")),
            (h-658, "8. Deliver decision", ["Dashboard, customer lookup", "Batch CSV/Excel results"], colors.HexColor("#E8F3EC")),
        ]
        for i, (y, title, lines, fill) in enumerate(nodes):
            self.box(c, x, y, bw, bh, title, lines, fill)
            if i < len(nodes)-1: self.down(c, x+bw/2, y, nodes[i+1][0]+bh)

story = []
story += [Spacer(1, 2.1*cm), P("FinRisk", "TitleX"),
          P("Credit Risk Assessment and Smart Loan Recommendation System", "SubTitleX"),
          P("Internship Project Report", "CalloutX"), Spacer(1, .4*cm)]
story += [P("Executive summary", "H1X"),
          P("FinRisk is an end-to-end data-science and web application for loan underwriting support. It combines an internal-bank dataset with CIBIL bureau data, predicts a customer's risk tier, applies lending policy and affordability rules, recommends a safe loan amount, calculates EMI, and displays a repayment schedule.", "BodyX"),
          P("The purpose is not merely to classify applicants. The project turns a model prediction into a usable lending decision: approve or reject, interest rate, loan tenure, recommended principal, EMI burden, and plain-language reason.", "BodyX"),
          Spacer(1, .3*cm),
          table([["Project objective", "Build a practical decision-support dashboard for bank loan applicants."],
                 ["Dataset", "51,336 applicants after merging bank and CIBIL data on PROSPECTID."],
                 ["Best classifier", "Gradient Boosting - 99.49% test accuracy."],
                 ["Best loan model", "Random Forest Regressor (compact, monotonic) - R2 0.96, MAE about Rs.6,052."],
                 ["Delivery", "Flask dashboard, individual scoring, batch CSV/Excel scoring, Render/Vercel configuration."]], [4.2*cm, 11.4*cm], header=False, font=8),
          Spacer(1, .4*cm),
          P("Submission-ready one-line explanation: I developed an ML-powered loan underwriting decision-support system that combines customer credit history, income, affordability constraints, and bank policy to provide a risk tier, approval decision, safe loan amount, EMI, and repayment plan.", "CalloutX"), PageBreak()]

story += [P("1. Business problem and solution", "H1X"),
          P("Banks process many loan applications. Approving a risky borrower can create losses; rejecting a reliable borrower loses business. FinRisk gives a fast, consistent, explainable first-level decision for an applicant.", "BodyX"),
          table([["Question", "FinRisk answer"],
                 ["How risky is the applicant?", "A classifier predicts P1, P2, P3, or P4 risk tier."],
                 ["Should the bank approve?", "P1-P3 are eligible subject to a minimum viable loan check; P4 is rejected."],
                 ["How much is safe?", "The minimum of ML prediction, policy cap, and risk-adjusted affordability."],
                 ["Can the applicant afford it?", "EMI is targeted to remain within 30% of net monthly income (FOIR)."],
                 ["How will the loan repay?", "A year-wise amortization schedule shows principal, interest, and balance."]], [5.2*cm, 10.4*cm]),
          P("End-to-end architecture", "H2X"),
          P("Raw bank data + CIBIL data -> merged dataset -> cleaning and feature engineering -> model training and evaluation -> trained joblib models -> Flask scoring pipeline -> dashboard and batch-download results.", "CalloutX"),
          P("Technology stack", "H2X"),
          table([["Layer", "Tools used"],
                 ["Data processing", "Python, pandas, NumPy"],
                 ["Machine learning", "scikit-learn"],
                 ["Visual analysis", "matplotlib, seaborn, scipy"],
                 ["Web application", "Flask, Jinja2, HTML, CSS, JavaScript"],
                 ["File support", "openpyxl for Excel upload/export; joblib for saved models"],
                 ["Deployment", "Gunicorn, Render configuration, Vercel entry point"]], [4.3*cm, 11.3*cm]), PageBreak()]

story += [UMLComponentDiagram(), PageBreak(), ProjectFlowDiagram(), PageBreak()]

story += [P("2. Data understanding, cleaning, and EDA", "H1X"),
          P("Notebook 01 loads the internal-bank and external CIBIL datasets and merges them with an inner join on PROSPECTID. Only customers present in both sources are retained. The merged dataset contains 51,336 rows and 87 columns.", "BodyX"),
          P("Notebook 02 prepares the dataset for modelling and investigates relationships between customer attributes and the target risk tier.", "BodyX"),
          table([["Step", "What was done", "Why"],
                 ["Missing values", "Six fields with over 30% missing values were dropped.", "They contain too little reliable information."],
                 ["Redundancy", "Thirteen highly correlated columns were removed.", "Avoids duplicate signals and unnecessary complexity."],
                 ["Imputation", "Numeric missing values use median; categorical fields use mode.", "Models require complete inputs."],
                 ["Income outliers", "Income was capped at the 1st and 99th percentiles.", "Limits unrealistic data-entry values."],
                 ["Categorical encoding", "Five text features were transformed using LabelEncoder.", "scikit-learn models use numeric values."],
                 ["EDA", "Distribution, boxplot, correlation, and chi-square analysis.", "Understands data quality and target relationships."]], [3.0*cm, 7.1*cm, 5.5*cm]),
          P("Target distribution", "H2X"),
          table([["Risk tier", "Applicants", "Meaning"], ["P1", "5,803", "Best risk"], ["P2", "32,199", "Good risk"], ["P3", "7,452", "Moderate risk"], ["P4", "5,882", "High risk"]], [3*cm, 3.4*cm, 9.2*cm]),
          Spacer(1, .15*cm), img("target_distribution.png", 14.5*cm), PageBreak()]

story += [P("3. Feature engineering", "H1X"),
          P("The project uses 68 final ML features. Two custom features make the recommendation logic more interpretable.", "BodyX"),
          table([["Feature", "Formula / construction", "Interpretation"],
                 ["Income_TL_Ratio", "Capped monthly income / active trade lines", "Income available relative to currently active loans/cards."],
                 ["Credit_Health_Score", "0-100 weighted score using credit score, history age, payment ratio, missed payments, delinquency, and 30+ DPD.", "A fuller view of credit quality than credit score alone."],
                 ["Age_Group", "18-24, 25-34, ...", "Reporting and approval-rate insights."],
                 ["Income_Segment", "Low to High income bands", "Reporting and portfolio insights."],
                 ["Credit_Score_Band", "Credit-score ranges", "Shows approval decision curve."]], [3.5*cm, 7.3*cm, 4.8*cm]),
          P("Credit Health Score logic", "H2X"),
          P("Positive factors are credit score (50% weight), age of oldest credit account (30%), and payment ratio (20%). Negative factors are missed payments (40%), serious delinquencies (35%), and 30+ days-past-due events (25%). After normalization, the negative part is subtracted and the result is converted to a 0-100 score.", "BodyX"),
          P("This score does not directly decide approval; the classifier predicts the tier. It does, however, reduce the recommended amount through a risk multiplier between 0.6 and 1.0.", "CalloutX"),
          img("engineered_features.png", 14.5*cm), PageBreak()]

story += [P("4. Model training and evaluation", "H1X"),
          P("Notebook 03 separates the classification and regression tasks. It uses a train/validation/test split: 35,935 training rows, 7,700 validation rows, and 7,701 test rows. The classification split is stratified so each risk tier remains represented.", "BodyX"),
          P("Classification: predict Approved_Flag / risk tier", "H2X"),
          table([["Model", "Validation accuracy", "Validation macro F1"],
                 ["Gradient Boosting", "99.47%", "98.95%"]], [6*cm, 4.6*cm, 4.9*cm]),
          P("Gradient Boosting is the risk-tier model. Test accuracy is 99.49%.", "CalloutX"),
          P("Regression: predict a policy-based recommended loan amount", "H2X"),
          table([["Model", "Validation R2", "Validation MAE"], ["Random Forest Regressor", "0.9596", "Rs.5,762"]], [6*cm, 4.6*cm, 4.9*cm]),
          P("A compact Random Forest Regressor is the loan-amount model: it is trained to reproduce the lending policy (income multiple, tier cap, affordability) and matches it at R2 0.96, with a monotonic constraint on credit score. For the live recommendation the app applies the policy formula directly, so the loan scales with the applicant's real income and stays fully explainable to an auditor. The project ships one model per task - Gradient Boosting for the risk tier and this Random Forest for the amount.", "BodyX"),
          img("confusion_matrix.png", 11*cm), PageBreak()]

story += [P("5. Risk policy and loan recommendation", "H1X"),
          P("Model output alone is not enough for banking. FinRisk combines it with transparent policy limits.", "BodyX"),
          table([["Tier", "Decision", "Max loan", "Rate", "Tenure", "Repayment"],
                 ["P1", "Approved", "Rs.25,00,000", "8.5%", "5 years", "Fixed monthly EMI"],
                 ["P2", "Approved", "Rs.15,00,000", "10.5%", "4 years", "Fixed monthly EMI"],
                 ["P3", "Conditional", "Rs.7,50,000", "13.5%", "3 years", "Step-up EMI"],
                 ["P4", "Rejected", "-", "-", "-", "Secured/collateral policy"]], [1.2*cm, 2.2*cm, 3.0*cm, 1.6*cm, 2.0*cm, 5.0*cm]),
          P("Loan sizing formula", "H2X"),
          P("Recommended loan = minimum(income multiple [annual income x tier multiplier], tier maximum, risk-adjusted affordable loan) -- each scaled by a credit-risk factor from Credit_Health_Score, on the applicant's real income, so the loan scales with income. A customer must also qualify for at least Rs.50,000; otherwise the decision changes to rejected due to insufficient income.", "CalloutX"),
          P("FOIR means Fixed Obligation to Income Ratio. This project uses an ideal FOIR ceiling of 30%, so the monthly EMI should not take more than 30% of the applicant's net monthly income. This protects room for basic expenses and savings.", "BodyX"),
          P("The affordability function rearranges the standard EMI formula to find the largest principal possible for a maximum EMI. For a loan principal P, monthly rate r, and total months n: EMI = P x r x (1+r)^n / ((1+r)^n - 1).", "BodyX"),
          img("loan_amount_regression.png", 14.3*cm), PageBreak()]

story += [P("6: Major scoring functions", "H1X"),
          P("The core implementation is in dashboard/pipeline.py. These functions are the most important for explaining the project in an interview or viva.", "BodyX"),
          table([["Function", "Purpose"],
                 ["credit_health_score(...) ", "Calculates the custom 0-100 health score from credit and repayment signals."],
                 ["risk_adjustment(chs)", "Maps health score to a safe 0.6-1.0 loan multiplier."],
                 ["max_foir(...) / foir_zone(...) ", "Sets the 30% affordability ceiling and classifies EMI burden."],
                 ["affordable_loan(income, rate, tenure)", "Finds the maximum principal whose EMI remains affordable."],
                 ["compute_emi(principal, rate, tenure)", "Calculates monthly EMI using the standard bank formula."],
                 ["repayment_schedule(...) ", "Simulates monthly repayment and returns yearly principal, interest, and balance."],
                 ["build_reason(...) ", "Creates a plain-language reason for approval or rejection."],
                 ["_prepare_features(inputs)", "Builds a complete 68-column model input from the 11 user-entered fields plus median defaults."],
                 ["score_applicant(inputs)", "Main single-applicant workflow: tier -> eligibility -> loan -> EMI -> schedule -> explanation."],
                 ["score_batch(df)", "Vectorized scoring for up to 2,000 uploaded rows in one model call per model."]], [5.5*cm, 10*cm]), PageBreak()]

story += [P("7. What happens in score_applicant()", "H1X"),
          P("This is the most important function in the project. It receives the live form inputs and returns a complete lending decision.", "BodyX"),
          table([["Step", "Operation"],
                 ["1. Prepare inputs", "Uses the 11 applicant inputs. Remaining model features are filled using training-data medians."],
                 ["2. Engineer features", "Caps income, calculates Income_TL_Ratio and Credit_Health_Score."],
                 ["3. Predict risk tier", "Classifier returns P1-P4 and prediction confidence."],
                 ["4. Eligibility", "P1/P2/P3 proceed; P4 is rejected."],
                 ["5. Apply loan rules", "Gets tier rate, tenure, cap and income multiplier; sizes the loan by the policy (income multiple, cap, affordability)."],
                 ["6. Affordability", "Computes the FOIR-based safe maximum and applies risk adjustment."],
                 ["7. Minimum ticket", "Rejects otherwise eligible applicants if safe amount is below Rs.50,000."],
                 ["8. Output", "Calculates EMI, total payable, total interest, FOIR zone, reasons, and repayment schedule."]], [3.2*cm, 12.3*cm]),
          P("Live form fields", "H2X"),
          table([["Input", "Why it matters"],
                 ["Credit score", "Main risk indicator in this data."], ["Monthly income", "Determines affordability and EMI ceiling."],
                 ["Age", "Customer demographic / life-stage signal."], ["Total and active loans", "Shows current debt footprint."],
                 ["Missed payments and delinquency", "Direct repayment-behaviour risk signals."],
                 ["30+ days late events", "Measures payment stress."], ["Age of oldest account", "Indicates maturity of credit history."],
                 ["Recent enquiries", "Many new applications may indicate credit hunger."], ["Employment tenure", "Indicates job stability."]], [5.0*cm, 10.5*cm]),
          P("Why use median filling? The live web form intentionally asks only for the most understandable drivers. The trained model expects all 68 columns, so missing less-important fields are filled using a typical (median) applicant profile.", "CalloutX"), PageBreak()]

story += [P("8. Flask dashboard and batch scoring", "H1X"),
          P("dashboard/app.py is the Flask presentation layer. It receives browser requests, calls the pipeline, and renders HTML templates.", "BodyX"),
          table([["Route", "Function / user feature"],
                 ["/", "Overview page: portfolio KPIs, tier split, model headline metrics."],
                 ["/customers", "Search and sort approved customers."],
                 ["/customer/<id>", "Single customer profile, loan details, and repayment schedule."],
                 ["/predict", "Manual form for live applicant scoring."],
                 ["/model", "Classifier/regressor metrics and feature importance."],
                 ["/insights", "Approval rates by credit-score band, income, age, and tier exposure."],
                 ["/batch", "Upload CSV/XLS/XLSX and score many applicants."],
                 ["/batch/template", "Download a correct example CSV template."],
                 ["/batch/download", "Download scored batch output as CSV."],
                 ["/figure/<name>", "Safely serves only PNG analysis charts."]], [4.0*cm, 11.5*cm]),
          P("Batch scoring implementation", "H2X"),
          P("score_batch() accepts flexible header names such as Credit Score, CIBIL score, Income, Salary, or Monthly Income. It normalizes headers, fills absent fields with feature medians, builds the full model matrix, and runs vectorized predictions. Vectorization means it does not call the model separately for every row, making batch scoring much faster.", "BodyX"),
          P("The batch limit is 2,000 rows. Results include credit score, predicted tier, decision, confidence, recommended loan, interest rate, tenure, EMI, and reason.", "CalloutX"), PageBreak()]

story += [P("9. Results, interpretation, and honesty", "H1X"),
          P("Reported model performance is strong, but it should be interpreted correctly.", "BodyX"),
          table([["Result", "Interpretation"],
                 ["Gradient Boosting test accuracy: 99.49%", "The classifier predicts the dataset's P1-P4 labels very accurately."],
                 ["Credit Score importance: 99.897%", "The target tier in this case-study data is largely determined by credit-score bands."],
                 ["Random Forest loan R2: 0.9595", "The model closely reproduces the constructed policy-based loan target."],
                 ["FOIR <= 30%", "The final recommended loan is constrained by actual repayment affordability."]], [6.0*cm, 9.5*cm]),
          P("Important limitation", "H2X"),
          P("This is a high-quality end-to-end demonstration, but it is not a production credit-underwriting engine. The risk tier is closely linked to credit score, so the reported classification accuracy is not equivalent to predicting real default probability. Also, the loan-amount target is generated from policy rules because the data has no historical correct loan amount.", "CalloutX"),
          P("For a real bank deployment, next improvements would be: use actual repayment/default outcomes, measure AUC/KS/Gini and calibration, run fairness analysis, monitor data drift, use reason codes and audit logs, validate performance across time, and add human credit-officer review before a final decision.", "BodyX"),
          img("feature_importance.png", 13.5*cm), PageBreak()]

story += [P("10. Demonstration and viva preparation", "H1X"),
          P("Suggested demo sequence", "H2X"),
          table([["Step", "What to show"],
                 ["1", "Open Overview and explain total applicants, eligible customers, loan book, and tier distribution."],
                 ["2", "Open Live Prediction and enter the strong sample profile from data/sample_applicants.csv."],
                 ["3", "Explain the predicted tier, confidence, credit health, recommended amount, rate, EMI, and FOIR."],
                 ["4", "Show the repayment schedule and explain principal versus interest."],
                 ["5", "Drag the debt-payoff simulator to show how a smaller yearly payment increases the payoff time and total interest."],
                 ["6", "Upload sample applicants through Batch Scoring and download the result."],
                 ["7", "Open Insights and discuss the credit-score decision curve and portfolio exposure."],
                 ["8", "Open Model page and show validation comparison and feature importance."]], [2*cm, 13.5*cm]),
          P("Likely viva questions and short answers", "H2X"),
          table([["Question", "Answer"],
                 ["Why did you use Gradient Boosting?", "In development testing it gave the best validation macro-F1 and test accuracy, so it is the model the project ships."],
                 ["Why do you use FOIR?", "It makes recommendations affordable by restricting EMI to 30% of net monthly income."],
                 ["Why a regressor if you already have rules?", "The regressor proves the lending policy is learnable from applicant features (R2 0.96). The app then applies the transparent policy rule directly, so the amount scales with real income and is fully auditable."],
                 ["Why is accuracy so high?", "The dataset's risk tiers are strongly linked to credit score, which is why I clearly state this limitation."],
                 ["What happens if user fields are missing?", "The live form validates numbers; batch scoring fills absent non-provided fields with training-data medians and shows a warning."],
                 ["How would you productionize it?", "Use real default labels, governance, fairness testing, drift monitoring, security, and a human approval step."]], [5.2*cm, 10.3*cm]), PageBreak()]

story += [P("11. Run, deployment, and project files", "H1X"),
          P("Local run instructions", "H2X"),
          P("1. Install dependencies: pip install -r requirements.txt<br/>2. Run notebooks 01 to 04 in sequence if models/data need regeneration.<br/>3. Start the dashboard: python dashboard/app.py<br/>4. Open http://localhost:5000", "BodyX"),
          P("requirements.txt pins Flask, pandas, NumPy, scikit-learn, joblib, and Gunicorn to compatible versions. Pinning scikit-learn is important because joblib model files need a compatible version for reliable loading and prediction.", "BodyX"),
          P("Key files", "H2X"),
          table([["Path", "Responsibility"],
                 ["notebooks/01_Data_Understanding.ipynb", "Merge and initial data understanding."],
                 ["notebooks/02_EDA_and_Feature_Engineering.ipynb", "Cleaning, EDA, encoding, derived features."],
                 ["notebooks/03_Model_Training_Evaluation.ipynb", "Model comparison, evaluation, and model saving."],
                 ["notebooks/04_Loan_Recommendation_and_Repayment.ipynb", "Business rules, EMI, repayment facts."],
                 ["dashboard/pipeline.py", "All scoring and business logic."],
                 ["dashboard/app.py", "Flask routes and dashboard rendering."],
                 ["models/*.joblib", "Saved classifiers, regressors, encoders, and feature lists."],
                 ["reports/*.csv", "Metrics, tier policy, feature importance, and EDA summary."],
                 ["render.yaml / vercel.json", "Cloud deployment configuration."]], [6.3*cm, 9.2*cm]),
          P("Conclusion", "H2X"),
          P("FinRisk demonstrates the complete data-science lifecycle: data integration, cleaning, exploratory analysis, feature engineering, model evaluation, business-rule integration, explainability, dashboard development, batch processing, and deployment readiness. Its best value is that it converts an ML prediction into a lending recommendation a bank employee or applicant can understand.", "CalloutX")]

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm,
                        topMargin=1.7*cm, bottomMargin=1.45*cm, title="FinRisk Internship Project Report")
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(OUT)
