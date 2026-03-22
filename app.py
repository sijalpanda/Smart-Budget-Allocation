"""
Smart Budget Allocation System
================================
A Streamlit web application to plan, track and improve your budget.
Author: Generated for College Project
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

DATA_FOLDER = "data"

DEFAULT_CATEGORIES = [
    "Rent", "Food", "Transport", "Entertainment",
    "Utilities", "Health", "Education", "Savings", "Miscellaneous"
]

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# ─────────────────────────────────────────────
# HELPER: CREATE DATA FOLDER IF MISSING
# ─────────────────────────────────────────────

def ensure_data_folder():
    """Create the data/ directory if it doesn't already exist."""
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

# ─────────────────────────────────────────────
# FUNCTION 1: CALCULATE BUDGET SUMMARY
# ─────────────────────────────────────────────

def calculate_budget_summary(total_budget, category_spending, savings_goal, borrowed_lent=0.0):
    """
    Calculate total allocated and remaining budget.
    borrowed_lent reduces remaining funds.
    """
    total_allocated = sum(category_spending.values())
    remaining = total_budget - total_allocated - borrowed_lent
    return {
        "total_allocated": total_allocated,
        "remaining": remaining
    }

# ─────────────────────────────────────────────
# FUNCTION 2: CALCULATE BUDGET HEALTH SCORE
# ─────────────────────────────────────────────

def calculate_budget_health(total_budget, category_spending, savings_goal, borrowed_lent=0.0):
    """
    Generate a budget health score from 0–100.

    Deductions:
    - Low savings ratio
    - Budget almost used up (accounting for borrowed_lent)
    - One category dominates spending

    Returns:
        (score: int, status: str)
    """
    if total_budget <= 0:
        return 0, "Poor 🔴"

    score = 100
    total_allocated = sum(category_spending.values())
    effective_used  = total_allocated + borrowed_lent

    # Deduct if savings ratio is low (< 10%)
    savings_ratio = savings_goal / total_budget
    if savings_ratio < 0.10:
        score -= 20
    elif savings_ratio < 0.20:
        score -= 10

    # Deduct if effective usage is high
    usage_ratio = effective_used / total_budget
    if usage_ratio > 1.0:
        score -= 30
    elif usage_ratio > 0.90:
        score -= 15

    # Deduct if any single category uses > 50% of budget
    for category, amount in category_spending.items():
        if amount / total_budget > 0.50:
            score -= 15
            break

    # Clamp score between 0 and 100
    score = max(0, min(100, score))

    if score >= 80:
        status = "Good 🟢"
    elif score >= 50:
        status = "Moderate 🟡"
    else:
        status = "Poor 🔴"

    return score, status

# ─────────────────────────────────────────────
# FUNCTION 3: GENERATE SUGGESTIONS
# ─────────────────────────────────────────────

def generate_suggestions(total_budget, category_spending, savings_goal, borrowed_lent=0.0):
    """
    Produce a list of smart financial suggestions based on spending patterns.

    Returns:
        list of suggestion strings
    """
    suggestions = []

    if total_budget <= 0:
        return ["⚠️ Please enter a valid total budget first."]

    food_amount = category_spending.get("Food", 0)
    if food_amount / total_budget > 0.30:
        suggestions.append("🍽️ Food spending is above 30% of your budget. Try meal prepping to cut costs.")

    savings_ratio = savings_goal / total_budget
    if savings_ratio < 0.10:
        suggestions.append("💰 Your savings goal is below 10%. Consider the 50/30/20 rule.")

    entertainment = category_spending.get("Entertainment", 0)
    if entertainment / total_budget > 0.15:
        suggestions.append("🎮 Entertainment spending is high (>15%). Look for free or low-cost activities.")

    transport = category_spending.get("Transport", 0)
    if transport / total_budget > 0.20:
        suggestions.append("🚌 Transport costs are above 20%. Consider public transport or carpooling.")

    if borrowed_lent > 0:
        borrow_pct = borrowed_lent / total_budget * 100
        suggestions.append(f"🔁 ₹{borrowed_lent:,.0f} ({borrow_pct:.1f}%) is tied up in borrowed/lent money. Try to settle it soon.")

    total_allocated = sum(category_spending.values())
    if total_allocated + borrowed_lent > total_budget:
        suggestions.append("🚨 You've exceeded your effective budget! Cut spending in non-essential categories.")

    if not suggestions:
        suggestions.append("✅ Your budget looks healthy! Keep maintaining this discipline.")

    return suggestions

# ─────────────────────────────────────────────
# FUNCTION 4: PREDICT FUTURE SPENDING
# Enhanced with growth rate
# ─────────────────────────────────────────────

def predict_future_spending(history_data):
    """
    Predict next month's spending.
    If >= 2 records: uses average + growth rate (last two months trend).
    If < 2 records: falls back to simple average.

    Returns:
        (predicted_spending: float, predicted_savings: float, method: str)
    """
    if not history_data:
        return 0.0, 0.0, "none"

    past_spending = [entry.get("total_allocated", 0) for entry in history_data]
    past_budgets  = [entry.get("total_budget", 0)    for entry in history_data]

    avg_spending = sum(past_spending) / len(past_spending)
    avg_budget   = sum(past_budgets)  / len(past_budgets)

    if len(past_spending) >= 2:
        # Growth rate = difference between the last two entries
        growth_rate        = past_spending[-1] - past_spending[-2]
        predicted_spending = avg_spending + growth_rate
        method             = "avg + growth rate"
    else:
        predicted_spending = avg_spending
        method             = "simple average"

    predicted_spending = max(0.0, predicted_spending)
    predicted_savings  = avg_budget - predicted_spending

    return round(predicted_spending, 2), round(predicted_savings, 2), method

# ─────────────────────────────────────────────
# FUNCTION 5: SAVE BUDGET
# ─────────────────────────────────────────────

def save_budget(budget_data, filename):
    """Save budget data as a JSON file inside the data/ folder."""
    ensure_data_folder()
    filepath = os.path.join(DATA_FOLDER, filename)
    with open(filepath, "w") as f:
        json.dump(budget_data, f, indent=4)
    return filepath

# ─────────────────────────────────────────────
# FUNCTION 6: LOAD BUDGET
# ─────────────────────────────────────────────

def load_budget(filename):
    """Load a previously saved budget JSON file. Returns dict or None."""
    filepath = os.path.join(DATA_FOLDER, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return json.load(f)

# ─────────────────────────────────────────────
# FUNCTION 7: LOAD ALL HISTORY
# ─────────────────────────────────────────────

def load_all_history():
    """Read all saved JSON files in data/ and compile spending history."""
    ensure_data_folder()
    history = []
    for fname in sorted(os.listdir(DATA_FOLDER)):
        if fname.endswith(".json"):
            data = load_budget(fname)
            if data:
                history.append(data)
    return history

# ─────────────────────────────────────────────
# FUNCTION 8: CHECK TOP SPENDING ALERT
# ─────────────────────────────────────────────

def get_top_spending_alerts(total_budget, category_spending):
    """Returns list of alert strings for categories that exceed 40% of budget."""
    alerts = []
    if total_budget <= 0:
        return alerts
    for cat, amount in category_spending.items():
        if amount > 0 and (amount / total_budget) > 0.40:
            alerts.append(
                f"⚠️ Your spending is heavily concentrated in **{cat}** "
                f"({amount/total_budget*100:.1f}%). Consider diversifying."
            )
    return alerts

# ─────────────────────────────────────────────
# STREAMLIT APP STARTS HERE
# ─────────────────────────────────────────────

def main():
    # ── Page config ──────────────────────────
    st.set_page_config(
        page_title="Smart Budget Allocation",
        page_icon="💸",
        layout="wide"
    )

    # ── App Title ────────────────────────────
    st.title("💸 Smart Budget Allocation System")
    st.subheader("Plan, Track and Improve Your Budget")
    st.markdown("---")

    # ── Initialise session state ─────────────
    if "custom_categories" not in st.session_state:
        st.session_state.custom_categories = []
    if "category_spending" not in st.session_state:
        st.session_state.category_spending = {}
    if "loaded_total_budget" not in st.session_state:
        st.session_state.loaded_total_budget = 10000.0
    if "loaded_savings_goal" not in st.session_state:
        st.session_state.loaded_savings_goal = 2000.0
    if "loaded_borrowed_lent" not in st.session_state:
        st.session_state.loaded_borrowed_lent = 0.0

    # ─────────────────────────────────────────
    # SIDEBAR — Budget Settings & Load/Save
    # ─────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Budget Settings")

        # Budget Mode Selection
        budget_mode = st.radio("Budget Type", ["Monthly Budget", "Annual Budget"])

        if budget_mode == "Monthly Budget":
            selected_month = st.selectbox("Month", MONTHS)
            selected_year  = st.number_input("Year", min_value=2000, max_value=2100,
                                             value=datetime.now().year, step=1)
            period_label = f"{selected_month} {int(selected_year)}"
            file_slug    = f"{selected_month.lower()}_{int(selected_year)}"
        else:
            selected_month = None
            selected_year  = st.number_input("Year", min_value=2000, max_value=2100,
                                             value=datetime.now().year, step=1)
            period_label = f"Annual {int(selected_year)}"
            file_slug    = f"annual_{int(selected_year)}"

        st.markdown("---")

        # Core Financial Inputs — uses session_state loaded values as defaults
        st.header("💰 Financial Inputs")
        total_budget = st.number_input(
            "Total Budget (₹)", min_value=0.0,
            value=st.session_state.loaded_total_budget, step=100.0
        )
        savings_goal = st.number_input(
            "Savings Goal (₹)", min_value=0.0,
            value=st.session_state.loaded_savings_goal, step=100.0
        )
        borrowed_lent = st.number_input(
            "Borrowed / Lent (₹, optional)", min_value=0.0,
            value=st.session_state.loaded_borrowed_lent, step=100.0
        )

        st.markdown("---")

        # Load Previous Budget — fully restores all fields
        st.header("📂 Load / Save")
        ensure_data_folder()
        saved_files = [f for f in sorted(os.listdir(DATA_FOLDER)) if f.endswith(".json")]

        if saved_files:
            selected_file = st.selectbox("Load Previous Budget", ["-- Select --"] + saved_files)
            if st.button("📥 Load Budget"):
                if selected_file != "-- Select --":
                    loaded = load_budget(selected_file)
                    if loaded:
                        st.session_state.category_spending   = loaded.get("category_spending", {})
                        st.session_state.custom_categories   = [
                            c for c in loaded.get("category_spending", {}).keys()
                            if c not in DEFAULT_CATEGORIES
                        ]
                        st.session_state.loaded_total_budget  = float(loaded.get("total_budget", 10000.0))
                        st.session_state.loaded_savings_goal  = float(loaded.get("savings_goal", 2000.0))
                        st.session_state.loaded_borrowed_lent = float(loaded.get("borrowed_lent", 0.0))
                        st.success(f"✅ Loaded: {selected_file}")
                        st.rerun()
                    else:
                        st.error("❌ Could not load file.")
        else:
            st.info("No saved budgets yet.")

        st.markdown("---")

        # Reset Budget
        if st.button("🔄 Reset Budget"):
            st.session_state.category_spending    = {}
            st.session_state.custom_categories    = []
            st.session_state.loaded_total_budget  = 10000.0
            st.session_state.loaded_savings_goal  = 2000.0
            st.session_state.loaded_borrowed_lent = 0.0
            st.rerun()

    # ─────────────────────────────────────────
    # PRE-COMPUTE SHARED VALUES
    # Calculated once here so all tabs can use them without duplication
    # ─────────────────────────────────────────
    summary         = calculate_budget_summary(
        total_budget, st.session_state.category_spending, savings_goal, borrowed_lent
    )
    total_allocated = summary["total_allocated"]
    remaining       = summary["remaining"]
    effective_used  = total_allocated + borrowed_lent
    health_score, health_status = calculate_budget_health(
        total_budget, st.session_state.category_spending, savings_goal, borrowed_lent
    )

    # ─────────────────────────────────────────
    # TABS — Main UI Layout
    # ─────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Budget Planner",
        "📊 Analytics",
        "🔮 Insights",
        "📅 History"
    ])

    # ═════════════════════════════════════════
    # TAB 1 — BUDGET PLANNER
    # Contains: Category Allocation, Custom Categories,
    #           Budget Summary, Progress Indicators, Alerts
    # ═════════════════════════════════════════
    with tab1:
        st.header(f"📋 Category Allocation — {period_label}")
        st.markdown("Enter your spending for each category below.")
        st.markdown("---")

        # Split into two columns: inputs on left, summary on right
        planner_left, planner_right = st.columns([1, 1], gap="large")

        # ── LEFT: Category Inputs ─────────────
        with planner_left:
            st.subheader("🗂️ Spending Categories")

            all_categories = DEFAULT_CATEGORIES + st.session_state.custom_categories

            for cat in all_categories:
                current_val = st.session_state.category_spending.get(cat, 0.0)

                # Show percentage of total budget next to label
                if total_budget > 0 and current_val > 0:
                    pct_label = f"  ({current_val / total_budget * 100:.1f}%)"
                else:
                    pct_label = ""

                is_custom = cat in st.session_state.custom_categories

                if is_custom:
                    # Delete button only for custom categories
                    inp_col, del_col = st.columns([5, 1])
                    with inp_col:
                        val = st.number_input(
                            f"{cat} (₹){pct_label}",
                            min_value=0.0,
                            value=float(current_val),
                            step=100.0,
                            key=f"cat_{cat}"
                        )
                    with del_col:
                        st.write("")  # spacer for vertical alignment
                        if st.button("🗑️", key=f"del_{cat}", help=f"Delete {cat}"):
                            st.session_state.custom_categories.remove(cat)
                            st.session_state.category_spending.pop(cat, None)
                            st.rerun()
                else:
                    val = st.number_input(
                        f"{cat} (₹){pct_label}",
                        min_value=0.0,
                        value=float(current_val),
                        step=100.0,
                        key=f"cat_{cat}"
                    )

                st.session_state.category_spending[cat] = val

            # Add Custom Category
            st.markdown("---")
            st.subheader("➕ Add Custom Category")
            new_cat_name = st.text_input("Category Name", key="new_cat_input")
            if st.button("➕ Add Category"):
                name = new_cat_name.strip()
                if name and name not in all_categories:
                    st.session_state.custom_categories.append(name)
                    st.session_state.category_spending[name] = 0.0
                    st.rerun()
                elif not name:
                    st.warning("Please enter a category name.")
                else:
                    st.warning(f"'{name}' already exists.")

        # ── RIGHT: Summary + Progress + Alerts ──
        with planner_right:

            # Budget Summary Metrics
            st.subheader("📊 Budget Summary")
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Total Budget",  f"₹{total_budget:,.0f}")
            m2.metric("📤 Allocated",     f"₹{total_allocated:,.0f}")
            m3.metric("💵 Remaining",     f"₹{remaining:,.0f}")

            m4, m5 = st.columns(2)
            m4.metric("🎯 Savings Goal",  f"₹{savings_goal:,.0f}")
            m5.metric("🔁 Borrowed/Lent", f"₹{borrowed_lent:,.0f}")

            st.markdown("---")

            # Progress Indicators
            st.subheader("📈 Progress Indicators")

            budget_used_pct = min(effective_used / total_budget, 1.0) if total_budget > 0 else 0
            savings_pct     = min(savings_goal   / total_budget, 1.0) if total_budget > 0 else 0

            st.write(f"**Budget Used (incl. borrowed/lent):** {budget_used_pct*100:.1f}%")
            st.progress(budget_used_pct)
            st.write(f"**Savings Target:** {savings_pct*100:.1f}%")
            st.progress(savings_pct)

            st.markdown("---")

            # Alerts
            st.subheader("🚨 Alerts")

            if effective_used > total_budget:
                st.error("⚠️ Warning: Budget Exceeded (including borrowed/lent)!")
            if remaining < savings_goal:
                st.warning("⚠️ Savings goal may not be achievable with current allocation.")
            if effective_used <= total_budget and remaining >= savings_goal:
                st.success("✅ You're within budget and on track for your savings goal!")

            # Top spending concentration alerts
            top_alerts = get_top_spending_alerts(total_budget, st.session_state.category_spending)
            for alert in top_alerts:
                st.warning(alert)

            # Savings category vs savings goal validation
            st.markdown("---")
            st.subheader("🎯 Savings Goal Validation")
            savings_cat_amount = st.session_state.category_spending.get("Savings", 0)
            if savings_cat_amount < savings_goal:
                st.warning(
                    f"⚠️ Your Savings allocation (₹{savings_cat_amount:,.0f}) is below "
                    f"your Savings Goal (₹{savings_goal:,.0f}). "
                    f"You need ₹{savings_goal - savings_cat_amount:,.0f} more."
                )
            else:
                st.success(
                    f"✅ Savings allocation (₹{savings_cat_amount:,.0f}) meets "
                    f"your Savings Goal (₹{savings_goal:,.0f})!"
                )

    # ═════════════════════════════════════════
    # TAB 2 — ANALYTICS
    # Contains: Budget Health Score, Budget Stress Meter,
    #           Pie Chart, Bar Chart
    # ═════════════════════════════════════════
    with tab2:
        st.header("📊 Budget Analytics")
        st.markdown("Visual breakdown of your spending and budget health.")
        st.markdown("---")

        analytics_left, analytics_right = st.columns([1, 1], gap="large")

        # ── LEFT: Health Score + Stress Meter ──
        with analytics_left:

            # Budget Health Score
            st.subheader("💪 Budget Health Score")
            st.metric("Health Score", f"{health_score}/100", delta=health_status)

            gauge_fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=health_score,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Budget Health"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar":  {"color": "#00cc96" if health_score >= 80 else
                                      "#ffa15a" if health_score >= 50 else "#ef553b"},
                    "steps": [
                        {"range": [0,  50], "color": "#ffe0e0"},
                        {"range": [50, 80], "color": "#fff4d6"},
                        {"range": [80,100], "color": "#d4f5e9"},
                    ]
                }
            ))
            gauge_fig.update_layout(height=280, margin=dict(t=30, b=0))
            st.plotly_chart(gauge_fig, use_container_width=True)

            st.markdown("---")

            # Budget Stress Meter
            st.subheader("😰 Budget Stress Meter")
            remaining_pct = (remaining / total_budget * 100) if total_budget > 0 else 100

            if remaining_pct > 30:
                stress_label = "Low Stress 😊"
                stress_color = "green"
            elif remaining_pct >= 10:
                stress_label = "Medium Stress 😐"
                stress_color = "orange"
            else:
                stress_label = "High Stress 😰"
                stress_color = "red"

            st.markdown(f"**Budget Stress Level:** :{stress_color}[{stress_label}]")
            st.caption(f"Remaining budget: {remaining_pct:.1f}% of total")

        # ── RIGHT: Pie Chart + Bar Chart ───────
        with analytics_right:

            # Pie Chart — Spending Distribution
            st.subheader("🍕 Spending Distribution")
            spend_data = {k: v for k, v in st.session_state.category_spending.items() if v > 0}
            if spend_data:
                pie_fig = px.pie(
                    names=list(spend_data.keys()),
                    values=list(spend_data.values()),
                    title="Category Breakdown",
                    hole=0.3
                )
                pie_fig.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(pie_fig, use_container_width=True)
            else:
                st.info("Enter spending amounts to see the pie chart.")

            st.markdown("---")

            # Bar Chart — Spending History
            st.subheader("📊 Spending History Chart")
            history = load_all_history()
            if history:
                hist_df = pd.DataFrame([{
                    "Period":         h.get("period_label", "Unknown"),
                    "Total Spending": h.get("total_allocated", 0),
                    "Budget":         h.get("total_budget", 0)
                } for h in history])

                bar_fig = px.bar(
                    hist_df, x="Period",
                    y=["Total Spending", "Budget"],
                    barmode="group",
                    title="Spending vs Budget Over Time",
                    labels={"value": "Amount (₹)", "variable": ""}
                )
                st.plotly_chart(bar_fig, use_container_width=True)
            else:
                st.info("Save budgets to see spending history chart.")

    # ═════════════════════════════════════════
    # TAB 3 — INSIGHTS
    # Contains: Smart Suggestions, Future Spending Predictor,
    #           Spending Leaderboard, Full Category Breakdown
    # ═════════════════════════════════════════
    with tab3:
        st.header("🔮 Smart Insights")
        st.markdown("AI-style analysis and recommendations based on your spending.")
        st.markdown("---")

        ins_col1, ins_col2, ins_col3 = st.columns(3, gap="large")

        # Smart Suggestions
        with ins_col1:
            st.subheader("💡 Smart Suggestions")
            suggestions = generate_suggestions(
                total_budget, st.session_state.category_spending, savings_goal, borrowed_lent
            )
            for s in suggestions:
                st.write(s)

        # Future Spending Predictor
        with ins_col2:
            st.subheader("🔮 Future Spending Predictor")
            history = load_all_history()
            pred_spending, pred_savings, pred_method = predict_future_spending(history)
            if pred_spending > 0:
                st.metric("📅 Predicted Next Month Spending", f"₹{pred_spending:,.2f}")
                st.metric("💰 Predicted Savings",             f"₹{pred_savings:,.2f}")
                st.caption(f"Method: {pred_method}")
            else:
                st.info("Save at least one budget to get predictions.")

        # Spending Leaderboard
        with ins_col3:
            st.subheader("🏆 Spending Leaderboard")
            spend_sorted = sorted(
                st.session_state.category_spending.items(),
                key=lambda x: x[1],
                reverse=True
            )
            top3 = [(cat, amt) for cat, amt in spend_sorted if amt > 0][:3]
            if top3:
                for rank, (cat, amt) in enumerate(top3, 1):
                    medal = ["🥇", "🥈", "🥉"][rank - 1]
                    pct   = f"({amt/total_budget*100:.1f}%)" if total_budget > 0 else ""
                    st.write(f"{medal} **{cat}** — ₹{amt:,.0f} {pct}")
            else:
                st.info("Enter spending to see leaderboard.")

        st.markdown("---")

        # Full Category Breakdown Table
        st.subheader("📋 Full Category Breakdown")
        if st.session_state.category_spending:
            breakdown_rows = []
            for cat, amt in st.session_state.category_spending.items():
                pct = (amt / total_budget * 100) if total_budget > 0 else 0
                breakdown_rows.append({
                    "Category":    cat,
                    "Amount (₹)":  amt,
                    "% of Budget": f"{pct:.1f}%",
                    "Status":      "⚠️ High" if pct > 40 else ("✅ OK" if amt > 0 else "—")
                })
            breakdown_df = pd.DataFrame(breakdown_rows)
            st.dataframe(breakdown_df, use_container_width=True)
        else:
            st.info("Enter category spending to see the breakdown.")

    # ═════════════════════════════════════════
    # TAB 4 — HISTORY
    # Contains: Spending History Table, Export CSV, Save Budget
    # ═════════════════════════════════════════
    with tab4:
        st.header("📅 Budget History & Data Management")
        st.markdown("View past budgets, export data, and save your current budget.")
        st.markdown("---")

        # Spending History Table
        st.subheader("📜 Spending History Table")
        history = load_all_history()
        if history:
            rows = []
            for h in history:
                rows.append({
                    "Period":            h.get("period_label", "Unknown"),
                    "Total Budget (₹)":  h.get("total_budget", 0),
                    "Total Spent (₹)":   h.get("total_allocated", 0),
                    "Savings Goal (₹)":  h.get("savings_goal", 0),
                    "Borrowed/Lent (₹)": h.get("borrowed_lent", 0),
                    "Health Score":      h.get("health_score", "N/A"),
                    "Category Count":    h.get("category_count", "N/A"),
                    "Saved At":          h.get("saved_at", ""),
                })
            hist_df = pd.DataFrame(rows)
            st.dataframe(hist_df, use_container_width=True)

            st.markdown("---")

            # Export History as CSV
            csv_data = hist_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Export History as CSV",
                data=csv_data,
                file_name="budget_history.csv",
                mime="text/csv"
            )
        else:
            st.info("No saved history found. Save a budget below to populate this table.")

        st.markdown("---")

        # Save Current Budget
        st.subheader("💾 Save Current Budget")
        st.write(
            f"**Period:** {period_label} &nbsp;|&nbsp; "
            f"**Total Budget:** ₹{total_budget:,.0f} &nbsp;|&nbsp; "
            f"**Allocated:** ₹{total_allocated:,.0f} &nbsp;|&nbsp; "
            f"**Remaining:** ₹{remaining:,.0f}"
        )

        if st.button("💾 Save Budget"):
            budget_data = {
                "period_label":      period_label,
                "budget_mode":       budget_mode,
                "month":             selected_month,
                "year":              int(selected_year),
                "total_budget":      total_budget,
                "savings_goal":      savings_goal,
                "borrowed_lent":     borrowed_lent,
                "total_allocated":   total_allocated,
                "remaining":         remaining,
                "category_spending": st.session_state.category_spending,
                "health_score":      health_score,
                "category_count":    len(st.session_state.category_spending),
                "saved_at":          datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            filename = f"{file_slug}.json"
            filepath = save_budget(budget_data, filename)
            st.success(f"✅ Budget saved to `{filepath}`")

    # ─────────────────────────────────────────
    # Footer
    # ─────────────────────────────────────────
    st.markdown("---")
    st.caption("💸 Smart Budget Allocation System | Built with ❤️ using Streamlit & Plotly")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
