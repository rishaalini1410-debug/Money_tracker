import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# DATABASE SETUP & HELPERS
# ---------------------------------------------------------
DB_FILE = "tracker.db"


def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        default_cats = [
            ("Food & Dining",),
            ("Bills & Utilities",),
            ("Shopping",),
            ("Transport",),
            ("Emergency Fund",),
            ("Fixed Savings",)
        ]
        c.executemany("INSERT INTO categories (name) VALUES (?)", default_cats)

    c.execute('''
        CREATE TABLE IF NOT EXISTS income_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT,
            source TEXT,
            amount REAL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT,
            category TEXT,
            allocated_amount REAL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            month_year TEXT,
            amount REAL,
            category TEXT,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()


# ---------------------------------------------------------
# CATEGORY MANAGEMENT FUNCTIONS
# ---------------------------------------------------------
def get_categories():
    conn = get_connection()
    df = pd.read_sql_query("SELECT name FROM categories ORDER BY id ASC", conn)
    conn.close()
    return df["name"].tolist() if not df.empty else []


def add_category(cat_name):
    cat_name = cat_name.strip()
    if not cat_name:
        return False, "Category name cannot be empty."
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
        conn.commit()
        conn.close()
        return True, f"Category '{cat_name}' added!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"Category '{cat_name}' already exists."


def rename_category(old_name, new_name):
    new_name = new_name.strip()
    if not new_name:
        return False, "New category name cannot be empty."
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE categories SET name = ? WHERE name = ?", (new_name, old_name))
        c.execute("UPDATE allocations SET category = ? WHERE category = ?", (new_name, old_name))
        c.execute("UPDATE expenses SET category = ? WHERE category = ?", (new_name, old_name))
        conn.commit()
        conn.close()
        return True, f"Renamed '{old_name}' to '{new_name}' across all records!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"Category '{new_name}' already exists."


def delete_category(cat_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM categories WHERE name = ?", (cat_name,))
    c.execute("DELETE FROM allocations WHERE category = ?", (cat_name,))
    c.execute("DELETE FROM expenses WHERE category = ?", (cat_name,))
    conn.commit()
    conn.close()
    return True, f"Deleted category '{cat_name}' and its associated records."


# ---------------------------------------------------------
# EXPENSE EDIT & DELETE HELPERS
# ---------------------------------------------------------
def update_expense(expense_id, new_date, new_amount, new_cat, new_desc):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE expenses 
        SET date = ?, amount = ?, category = ?, description = ?
        WHERE id = ?
    """, (new_date, new_amount, new_cat, new_desc, expense_id))
    conn.commit()
    conn.close()


def delete_expense(expense_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------
# UI CONFIGURATION & STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Money Tracker", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .metric-card {
        background-color: #1E1E1E;
        border: 1px solid #333333;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin-bottom: 15px;
    }
    .metric-title { font-size: 14px; color: #AAAAAA; font-weight: bold; }
    .metric-value { font-size: 26px; font-weight: bold; color: #4CAF50; }
    .metric-value-accent { font-size: 24px; font-weight: bold; color: #2196F3; }
    .metric-value-alert { font-size: 24px; font-weight: bold; color: #FF5252; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIDEBAR: MONTH/YEAR SELECTOR
# ---------------------------------------------------------
st.sidebar.header("🗓️ Select Period")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox("Year", range(current_year - 2, current_year + 5), index=2)
months = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
selected_month = st.sidebar.selectbox("Month", months, index=datetime.now().month - 1)
selected_period = f"{selected_month} {selected_year}"

view_mode = st.sidebar.radio("Navigation", ["Dashboard", "Set Monthly Budget", "Monthly Report", "Yearly Report"])


# ---------------------------------------------------------
# DATA CALCULATION HELPERS
# ---------------------------------------------------------
def get_month_income(period):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM income_sources WHERE month_year = ?", conn, params=(period,))
    conn.close()
    return df


def get_month_allocations(period):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM allocations WHERE month_year = ?", conn, params=(period,))
    conn.close()
    return df


def get_month_expenses(period):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM expenses WHERE month_year = ?", conn, params=(period,))
    conn.close()
    return df


def get_all_expenses():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM expenses", conn)
    conn.close()
    return df


# ---------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------
if view_mode == "Dashboard":
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<h1 style='text-align: center;'>💰 Money Tracker</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; color: #888888;'>{selected_period.upper()}</h3>",
                    unsafe_allow_html=True)

    inc_df = get_month_income(selected_period)
    alloc_df = get_month_allocations(selected_period)
    exp_df = get_month_expenses(selected_period)
    all_exp_df = get_all_expenses()

    available_categories = get_categories()

    total_income = inc_df["amount"].sum() if not inc_df.empty else 0.0

    regular_exp_df = exp_df[
        ~exp_df["category"].isin(["Emergency Fund", "Fixed Savings"])] if not exp_df.empty else pd.DataFrame()
    total_spent_regular = regular_exp_df["amount"].sum() if not regular_exp_df.empty else 0.0

    savings_alloc = alloc_df[alloc_df["category"].isin(["Emergency Fund", "Fixed Savings"])][
        "allocated_amount"].sum() if not alloc_df.empty else 0.0
    balance_available = total_income - savings_alloc - total_spent_regular

    # BIG BOX: Total Balance Available
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">TOTAL BALANCE AVAILABLE ({selected_period})</div>
            <div class="metric-value">RM {balance_available:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

    # CATEGORY BOXES
    budget_cats = [c for c in available_categories if c not in ["Emergency Fund", "Fixed Savings"]]

    if budget_cats:
        num_cols = min(len(budget_cats), 4)
        cat_cols = st.columns(num_cols)

        for idx, cat in enumerate(budget_cats):
            cat_alloc_df = alloc_df[alloc_df["category"] == cat] if not alloc_df.empty else pd.DataFrame()
            allocated = cat_alloc_df["allocated_amount"].sum() if not cat_alloc_df.empty else 0.0
            has_budget = allocated > 0.0
            spent = exp_df[exp_df["category"] == cat]["amount"].sum() if not exp_df.empty else 0.0

            with cat_cols[idx % num_cols]:
                if not has_budget:
                    # Blue if spent is exactly 0, Red for any non-zero value
                    val_class = "metric-value-accent" if spent == 0 else "metric-value-alert"
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-title">{cat.upper()}</div>
                            <div class="{val_class}">RM {spent:,.2f}</div>
                            <small style='color: #888888;'>Spent (No Budget Set)</small>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    remaining = allocated - spent

                    # Blue when balance is exactly 0, Red for any non-zero value
                    val_class = "metric-value-accent" if remaining == 0 else "metric-value-alert"

                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-title">{cat.upper()}</div>
                            <div class="{val_class}">RM {remaining:,.2f}</div>
                            <small style='color: #888888;'>Allocated: RM {allocated:,.2f} | Spent: RM {spent:,.2f}</small>
                        </div>
                    """, unsafe_allow_html=True)

    # BUTTON ACTION AREA
    btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])

    if "show_summary" not in st.session_state:
        st.session_state.show_summary = False

    with btn_col1:
        if st.button("👀 Summary Table", use_container_width=True):
            st.session_state.show_summary = not st.session_state.show_summary

    with btn_col2:
        add_exp_pop = st.popover("➕ Add Expense", use_container_width=True)

    with add_exp_pop:
        st.subheader("Add New Expense")
        with st.form("expense_form", clear_on_submit=True):
            exp_amount = st.number_input("Amount (RM)", min_value=0.0, step=1.0, format="%.2f")
            exp_cat = st.selectbox("Category", available_categories)
            exp_desc = st.text_input("Description")
            exp_date = st.date_input("Date", value=datetime.now())
            submit_exp = st.form_submit_button("Submit Expense")

            if submit_exp:
                if exp_amount > 0:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute(
                        "INSERT INTO expenses (date, month_year, amount, category, description) VALUES (?, ?, ?, ?, ?)",
                        (exp_date.strftime("%Y-%m-%d"), selected_period, exp_amount, exp_cat, exp_desc)
                    )
                    conn.commit()
                    conn.close()
                    st.success("Expense logged successfully!")
                    st.rerun()

    # SUMMARY TABLE & VISUAL ANALYTICS
    if st.session_state.show_summary:
        st.markdown("---")
        st.subheader(f"📊 Monthly Financial Summary ({selected_period})")

        # 1. Income Summary Breakdown
        st.markdown("##### 💵 Income Breakdown")
        if not inc_df.empty:
            st.dataframe(
                inc_df[["source", "amount"]].rename(columns={"source": "Income Source", "amount": "Amount (RM)"}),
                use_container_width=True)
        else:
            st.warning("No income records set for this month.")

        # 2. Bar Chart: Category Spent Amount Only
        st.markdown("##### 📈 Category Spending Breakdown")

        summary_data = []
        for cat in available_categories:
            spent_val = exp_df[exp_df["category"] == cat]["amount"].sum() if not exp_df.empty else 0.0
            summary_data.append({"Category": cat, "Spent": spent_val})

        chart_df = pd.DataFrame(summary_data).set_index("Category")
        st.bar_chart(chart_df["Spent"])

        # 3. Transaction Log Table with Edit & Delete Options
        st.markdown("##### 📝 Logged Expenses (Edit or Delete)")
        if not exp_df.empty:
            for idx, row in exp_df.iterrows():
                col_info, col_edit, col_del = st.columns([3, 1, 1])

                with col_info:
                    st.write(
                        f"**{row['date']}** | **{row['category']}** - {row['description']}: `RM {row['amount']:,.2f}`"
                    )

                with col_edit:
                    with st.popover("✏️ Edit", key=f"pop_{row['id']}"):
                        with st.form(f"edit_form_{row['id']}"):
                            try:
                                default_date = datetime.strptime(row['date'], "%Y-%m-%d")
                            except ValueError:
                                default_date = datetime.now()

                            edit_date = st.date_input("Date", value=default_date, key=f"d_{row['id']}")
                            edit_amount = st.number_input(
                                "Amount (RM)",
                                value=float(row['amount']),
                                min_value=0.0,
                                step=1.0,
                                format="%.2f",
                                key=f"a_{row['id']}"
                            )
                            cat_index = available_categories.index(row['category']) if row[
                                                                                           'category'] in available_categories else 0
                            edit_cat = st.selectbox(
                                "Category",
                                available_categories,
                                index=cat_index,
                                key=f"c_{row['id']}"
                            )
                            edit_desc = st.text_input("Description", value=row['description'], key=f"desc_{row['id']}")

                            if st.form_submit_button("Save Changes"):
                                update_expense(
                                    row['id'],
                                    edit_date.strftime("%Y-%m-%d"),
                                    edit_amount,
                                    edit_cat,
                                    edit_desc
                                )
                                st.success("Updated expense!")
                                st.rerun()

                with col_del:
                    if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                        delete_expense(row['id'])
                        st.success("Expense deleted!")
                        st.rerun()
        else:
            st.info("No expenses logged for this month yet.")

    st.write("---")

    # ACCUMULATED SAVINGS & EMERGENCY FUNDS
    conn = get_connection()
    all_alloc = pd.read_sql_query("SELECT * FROM allocations", conn)
    conn.close()

    total_emerg_alloc = all_alloc[all_alloc["category"] == "Emergency Fund"][
        "allocated_amount"].sum() if not all_alloc.empty else 0.0
    total_emerg_spent = all_exp_df[all_exp_df["category"] == "Emergency Fund"][
        "amount"].sum() if not all_exp_df.empty else 0.0
    accumulated_emergency = total_emerg_alloc - total_emerg_spent

    total_fixed_alloc = all_alloc[all_alloc["category"] == "Fixed Savings"][
        "allocated_amount"].sum() if not all_alloc.empty else 0.0
    total_fixed_spent = all_exp_df[all_exp_df["category"] == "Fixed Savings"][
        "amount"].sum() if not all_exp_df.empty else 0.0
    accumulated_fixed = total_fixed_alloc - total_fixed_spent

    sav_col1, sav_col2 = st.columns(2)
    with sav_col1:
        st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid #FF9800;">
                <div class="metric-title">TOTAL EMERGENCY FUND (ACCUMULATED)</div>
                <div class="metric-value" style="color: #FF9800;">RM {accumulated_emergency:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)

    with sav_col2:
        st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid #9C27B0;">
                <div class="metric-title">TOTAL FIXED SAVINGS (ACCUMULATED)</div>
                <div class="metric-value" style="color: #9C27B0;">RM {accumulated_fixed:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# BUDGET & CATEGORY SETTINGS
# ---------------------------------------------------------
elif view_mode == "Set Monthly Budget":
    st.title("⚙️ Budget & Category Management")

    tab1, tab2 = st.tabs(["Set Budget & Income Allocations", "Manage Categories"])

    with tab1:
        st.subheader(f"Configure Income & Allocation for {selected_period}")
        categories = get_categories()

        existing_inc = get_month_income(selected_period)
        sal_val = existing_inc[existing_inc["source"] == "Salary"]["amount"].sum() if not existing_inc.empty else 0.0
        pass_val = existing_inc[existing_inc["source"] == "Passive Income"][
            "amount"].sum() if not existing_inc.empty else 0.0
        oth_val = existing_inc[existing_inc["source"] == "Other Income"][
            "amount"].sum() if not existing_inc.empty else 0.0


        def get_default_allocation(category_name):
            conn = get_connection()
            df = pd.read_sql_query(
                "SELECT allocated_amount FROM allocations WHERE month_year = ? AND category = ?",
                conn, params=(selected_period, category_name)
            )
            if not df.empty:
                conn.close()
                return float(df["allocated_amount"].iloc[0])

            df_latest = pd.read_sql_query(
                "SELECT allocated_amount FROM allocations WHERE category = ? ORDER BY id DESC LIMIT 1",
                conn, params=(category_name,)
            )
            conn.close()
            if not df_latest.empty:
                return float(df_latest["allocated_amount"].iloc[0])

            return 0.0


        with st.form("budget_form"):
            st.markdown("#### 1. Monthly Income Sources")
            inc_c1, inc_c2, inc_c3 = st.columns(3)
            with inc_c1:
                sal_input = st.number_input("Salary (RM)", min_value=0.0, value=sal_val, step=100.0, format="%.2f")
            with inc_c2:
                pass_input = st.number_input("Passive Income (RM)", min_value=0.0, value=pass_val, step=50.0,
                                             format="%.2f")
            with inc_c3:
                oth_input = st.number_input("Other Income (RM)", min_value=0.0, value=oth_val, step=50.0, format="%.2f")

            st.markdown("#### 2. Category Budget Allocations")
            alloc_inputs = {}
            for cat in categories:
                def_alloc = get_default_allocation(cat)
                alloc_inputs[cat] = st.number_input(f"{cat} (RM)", min_value=0.0, value=def_alloc, step=50.0,
                                                    format="%.2f")

            save_budget = st.form_submit_button("Save Budget Settings")

            if save_budget:
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM income_sources WHERE month_year = ?", (selected_period,))
                c.execute("DELETE FROM allocations WHERE month_year = ?", (selected_period,))

                income_data = [
                    (selected_period, "Salary", sal_input),
                    (selected_period, "Passive Income", pass_input),
                    (selected_period, "Other Income", oth_input)
                ]
                c.executemany("INSERT INTO income_sources (month_year, source, amount) VALUES (?, ?, ?)", income_data)

                alloc_data = [(selected_period, cat, val) for cat, val in alloc_inputs.items()]
                c.executemany("INSERT INTO allocations (month_year, category, allocated_amount) VALUES (?, ?, ?)",
                              alloc_data)

                conn.commit()
                conn.close()
                st.success(f"Budget and Income saved for {selected_period}!")
                st.rerun()

    with tab2:
        st.subheader("Custom Categories")
        current_cats = get_categories()

        col_c1, col_c2, col_c3 = st.columns(3)

        with col_c1:
            st.markdown("**Add New Category**")
            new_cat_name = st.text_input("Category Name", key="add_cat_input")
            if st.button("Add Category"):
                success, msg = add_category(new_cat_name)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with col_c2:
            st.markdown("**Edit/Rename Category**")
            cat_to_edit = st.selectbox("Select Category to Rename", current_cats, key="edit_cat_select")
            renamed_name = st.text_input("New Name", value=cat_to_edit, key="rename_cat_input")
            if st.button("Rename Category"):
                if cat_to_edit != renamed_name:
                    success, msg = rename_category(cat_to_edit, renamed_name)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with col_c3:
            st.markdown("**Delete Category**")
            cat_to_delete = st.selectbox("Select Category to Delete", current_cats, key="del_cat_select")
            st.caption("⚠️ Warning: Deleting a category removes its budget and expense history.")
            if st.button("Delete Category", type="primary"):
                success, msg = delete_category(cat_to_delete)
                if success:
                    st.success(msg)
                    st.rerun()

# ---------------------------------------------------------
# REPORTS
# ---------------------------------------------------------
elif view_mode == "Monthly Report":
    st.title(f"📊 Monthly Report - {selected_period}")
    exp_df = get_month_expenses(selected_period)

    if not exp_df.empty:
        cat_summary = exp_df.groupby("category")["amount"].sum().reset_index()
        st.subheader("Expenses by Category")
        st.bar_chart(cat_summary.set_index("category"))
        st.dataframe(exp_df, use_container_width=True)
    else:
        st.info("No data available for this month.")

elif view_mode == "Yearly Report":
    st.title(f"📈 Yearly Report - {selected_year}")
    all_exp_df = get_all_expenses()

    if not all_exp_df.empty:
        yearly_df = all_exp_df[all_exp_df["month_year"].str.contains(str(selected_year))]
        if not yearly_df.empty:
            yearly_summary = yearly_df.groupby("category")["amount"].sum().reset_index()
            st.subheader(f"Total Expenditure Breakdown for {selected_year}")
            st.bar_chart(yearly_summary.set_index("category"))
            st.dataframe(yearly_df, use_container_width=True)
        else:
            st.info("No data available for this year.")
    else:
        st.info("No expense records found.")