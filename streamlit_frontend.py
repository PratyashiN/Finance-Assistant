# streamlit_frontend.py

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Finance Assistant", layout="wide")

# Base URL for your backend
backend_url = "http://127.0.0.1:5000"

# --- Sidebar Navigation ---
st.sidebar.title(" Navigation")
pages = [
    " Welcome",
    " Add Transaction",
    " Transaction History",
    " Budget Management",
    " Expense Trends",
    " Forecast & Advice",
    " Monthly Salary",
    " About"
]
selected_page = st.sidebar.radio("Go to", pages)

if selected_page == " Welcome":
    # Set background color and font styles
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #000000;  /* Light lemon yellow */
            }
            h1 {
                color: #FFFACD !important;  /* Dark green */
            }
            .stTextInput>div>div>input {
                color: #FFFACD !important;  /* Black text */
                background-color: #000000 !important;
                border: 1px solid #FFFACD !important;
            }
            .stTextInput>div>div>input::placeholder {
                color: #6D7B8D !important;  /* Light slate gray for placeholder */
            }
            .st-b7 {
                color: #FFFACD !important;  /* Black for input labels */
            }
            .stSuccess {
                color: #FFFACD !important;  /* Dark green */
            }
            .css-1aumxhk {
                color: #FFFACD !important;  /* Black for general text */
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.title(" Personal Finance Assistant")
    
    # Create two columns for better layout
    col1, col2 = st.columns([2, 3])
    
    with col1:
        user = st.text_input("", placeholder="Add your name", key="name_input")
        if user:
            st.markdown(
                f'<p style="color:#006400; font-size:20px;">👋 Welcome, {user}! Manage your money smarter.</p>',
                unsafe_allow_html=True
            )
            
            # Finance tips box with black text
            st.markdown("""
            <div style="background-color:#FFFFFF; padding:15px; border-radius:10px; margin-top:20px; color:#000000;">
                <h4 style="color:#013220;">Quick Tips to Get Started:</h4>
                <ul style="color:#000000;">
                    <li>Track all your expenses</li>
                    <li>Set monthly budget goals</li>
                    <li>Review your spending weekly</li>
                    <li>Save at least 20% of income</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Finance animation with container and black text
        st.markdown("""
        <div style="margin-top:20px; background-color:#FFFFFF; padding:10px; border-radius:10px;">
            <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
            <lottie-player src="https://assets9.lottiefiles.com/packages/lf20_0a1eojqk.json"  
                background="transparent" speed="1" style="width: 100%; height: 400px;" loop autoplay>
            </lottie-player>
            <p style="color:#000000; text-align:center;">Your Financial Journey Starts Here</p>
        </div>
        """, unsafe_allow_html=True)

# --- Add Transaction Page ---
elif selected_page == " Add Transaction":
    st.header(" Add Transaction")
    with st.form("add_txn"):
        txn_type = st.selectbox("Type", ["Income", "Expense"])
        category = st.text_input("Category")
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        description = st.text_input("Description")
        date = st.date_input("Date")
        submitted = st.form_submit_button("Add")

    if submitted:
        data = {
            "type": txn_type,
            "category": category,
            "amount": amount,
            "description": description,
            "date": str(date)
        }
        try:
            r = requests.post(f"{backend_url}/add", json=data)
            st.success("✅ Transaction added!")
        except Exception as e:
            st.error(f"Error: {e}")
# --- Transaction History ---
elif selected_page == " Transaction History":
    st.header(" Transaction History")
    
    # Add filters and date range
    with st.expander(" Filter Transactions", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            filter_type = st.selectbox("Type", ["All", "Income", "Expense"])
            category_filter = st.text_input("Category Filter")
        with col2:
            start_date = st.date_input("Start Date", 
                                      value=datetime.now() - timedelta(days=30))
            end_date = st.date_input("End Date", value=datetime.now())
    
    try:
        # Fetch transactions with loading spinner
        with st.spinner("Loading transactions..."):
            res = requests.get(f"{backend_url}/transactions")
            txns = res.json()
            if isinstance(txns, dict):
                txns = txns.get("transactions", [])
            
            df = pd.DataFrame(txns)
            
            if not df.empty:
                # Convert date and filter
                df['date'] = pd.to_datetime(df['date'])
                df = df[(df['date'] >= pd.to_datetime(start_date)) & 
                        (df['date'] <= pd.to_datetime(end_date))]
                
                if filter_type != "All":
                    df = df[df['type'] == filter_type]
                
                if category_filter:
                    df = df[df['category'].str.contains(category_filter, case=False, na=False)]
                
                # Display summary stats
                st.metric("Total Transactions", len(df))
                
                col1, col2 = st.columns(2)
                income = df[df['type'] == 'Income']['amount'].sum()
                expenses = df[df['type'] == 'Expense']['amount'].sum()
                
                col1.metric("Total Income", f"₹{income:,.2f}")
                col2.metric("Total Expenses", f"₹{expenses:,.2f}")
                
                # Add delete functionality
                st.subheader("Manage Transactions")
                df_with_selections = df.copy()
                df_with_selections.insert(0, "Select", False)
                
                # Display editable dataframe
                edited_df = st.data_editor(
                    df_with_selections.sort_values('date', ascending=False),
                    column_config={
                        "Select": st.column_config.CheckboxColumn(required=True),
                        "amount": st.column_config.NumberColumn(format="₹%.2f"),
                        "date": st.column_config.DateColumn(format="YYYY-MM-DD")
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=500
                )
                
                # Delete selected transactions
                selected_rows = edited_df[edited_df.Select]
                if not selected_rows.empty:
                    if st.button("🗑️ Delete Selected Transactions", type="primary"):
                        with st.spinner("Deleting transactions..."):
                            deleted_count = 0
                            for _, row in selected_rows.iterrows():
                                try:
                                    # Assuming your backend has a delete endpoint
                                    response = requests.delete(
                                        f"{backend_url}/transactions/{row['id']}"
                                    )
                                    if response.status_code == 200:
                                        deleted_count += 1
                                except Exception:
                                    continue
                            
                            if deleted_count > 0:
                                st.success(f"✅ Successfully deleted {deleted_count} transactions!")
                                st.experimental_rerun()
                            else:
                                st.error("Failed to delete transactions")
                
                # Add download button
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name='transactions.csv',
                    mime='text/csv'
                )
            else:
                st.info("No transactions found for the selected filters.")
    except Exception as e:
        st.error(f"❌ Error loading transactions: {str(e)}")

# --- Budget Management ---
elif selected_page == " Budget Management":
    st.header(" Budget Management")
    
    # Tab layout
    tab1, tab2 = st.columns(2)  # Changed to columns for better layout
    
    with tab1:
        with st.form("budget_form"):
            st.subheader("💰 Set Budget")
            category = st.text_input("Budget Category", 
                                   placeholder="e.g. Groceries, Entertainment")
            limit = st.number_input("Monthly Limit (₹)", 
                                  min_value=0.0, 
                                  step=100.0,
                                  format="%.2f")
            
            submit_budget = st.form_submit_button("💾 Save Budget", type="primary")
        
        if submit_budget:
            if not category.strip():
                st.error("Please enter a category name")
            elif limit <= 0:
                st.error("Budget limit must be greater than 0")
            else:
                try:
                    with st.spinner("Saving budget..."):
                        r = requests.post(
                            f"{backend_url}/budget", 
                            json={"category": category.strip(), "limit": limit}
                        )
                        if r.status_code == 200:
                            st.success("✅ Budget saved successfully!")
                        else:
                            st.error(f"Error: {r.text}")
                except Exception as e:
                    st.error(f"❌ Connection error: {str(e)}")
    
    with tab2:
        st.subheader("📊 Budget Progress")
        try:
            with st.spinner("Loading budget data..."):
                # Fetch data
                txns = requests.get(f"{backend_url}/transactions").json()
                budgets = requests.get(f"{backend_url}/budget").json()
                
                if isinstance(txns, dict):
                    txns = txns.get("transactions", [])
                
                df_txn = pd.DataFrame(txns)
                df_budget = pd.DataFrame(budgets)
                
                if not df_txn.empty and not df_budget.empty:
                    # Process data
                    spent = df_txn[df_txn["type"] == "Expense"].groupby("category")["amount"].sum().reset_index()
                    progress = pd.merge(df_budget, spent, on="category", how="left").fillna(0)
                    progress["spent"] = progress["amount"]
                    progress["remaining"] = progress["limit"] - progress["spent"]
                    progress["percent"] = (progress["spent"] / progress["limit"]) * 100
                    
                    # Display progress for each category
                    for _, row in progress.iterrows():
                        with st.container():
                            st.markdown(f"#### {row['category']}")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Budget", f"₹{row['limit']:,.2f}")
                            col2.metric("Spent", f"₹{row['spent']:,.2f}", 
                                       delta=f"-₹{row['remaining']:,.2f} remaining")
                            col3.metric("Progress", f"{min(row['percent'], 100):.0f}%")
                            
                            # Progress bar with color coding
                            progress_color = "red" if row['percent'] > 90 else "orange" if row['percent'] > 70 else "green"
                            st.progress(
                                min(int(row["percent"]), 100), 
                                text=f"{min(row['percent'], 100):.0f}% of budget used"
                            )
                            
                            st.divider()
                else:
                    st.info("Add transactions and budgets to view progress.")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# --- Expense Trends ---
elif selected_page == " Expense Trends":
    st.header(" Daily Expense Trends")
    try:
        txns = requests.get(f"{backend_url}/transactions").json()
        if isinstance(txns, dict):
            txns = txns.get("transactions", [])
        df = pd.DataFrame(txns)
        if not df.empty:
            df = df[df["type"] == "Expense"]
            df["date"] = pd.to_datetime(df["date"])
            df_grouped = df.groupby("date")["amount"].sum().reset_index()
            fig = px.line(df_grouped, x="date", y="amount", title="Daily Expenses")
            st.plotly_chart(fig)
        else:
            st.info("No expenses yet.")
    except Exception as e:
        st.error(f"Error loading trends: {e}")
        
        #--- Forecast & Advice ---#

elif selected_page == " Forecast & Advice":
    st.title(" Forecast & Advice")
    
    tab1, tab2 = st.tabs([" Spending Forecast", " AI Advisor"])
    
    with tab1:
        st.header(" 7-Day Spending Forecast")
        try:
            with st.spinner("Generating forecast..."):
                response = requests.get(f"{backend_url}/forecast")
                if response.status_code == 200:
                    forecast_data = response.json()
                    if forecast_data and not isinstance(forecast_data, dict):
                        df = pd.DataFrame(forecast_data)
                        df['date'] = pd.to_datetime(df['date'])
                        
                        # Display forecast chart
                        fig = px.line(
                            df, 
                            x='date', 
                            y='predicted_amount',
                            error_y="predicted_amount",
                            error_y_minus="confidence_low",
                            title="Daily Spending Forecast with Confidence Intervals",
                            labels={
                                "date": "Date",
                                "predicted_amount": "Predicted Amount (₹)",
                                "day_of_week": "Day of Week"
                            }
                        )
                        fig.update_traces(
                            line=dict(color="#013220", width=3),
                            error_y=dict(color="rgba(1,50,32,0.2)", thickness=1)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Display detailed forecast
                        st.subheader("Detailed Forecast")
                        cols = st.columns(4)
                        for i, row in df.iterrows():
                            with cols[i%4]:
                                st.metric(
                                    label=row['day_of_week'],
                                    value=f"₹{row['predicted_amount']:,.2f}",
                                    delta=f"±₹{(row['confidence_high']-row['predicted_amount']):,.2f}"
                                )
                    else:
                        st.warning("Not enough data to generate forecast. Add more transactions.")
                else:
                    st.error(f"Error generating forecast: {response.text}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    with tab2:
        st.header(" Personalized Financial Advice")
        try:
            with st.spinner("Analyzing your spending patterns..."):
                response = requests.get(f"{backend_url}/advisor")
                if response.status_code == 200:
                    advice_data = response.json()
                    
                    # Display advice
                    st.markdown(
                        f"""
                        <div style="background-color:#FFFFFF; padding:20px; border-radius:10px; border-left: 4px solid #013220;">
                            <h3 style="color:#013220;">Your Personalized Advice</h3>
                            <p style="color:#000000; font-size:16px;">{advice_data.get('advice', 'No advice generated')}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Display stats if available
                    if 'stats' in advice_data:
                        st.subheader("📈 Your Financial Snapshot")
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric(
                            "Total Income", 
                            f"₹{advice_data['stats']['total_income']:,.2f}"
                        )
                        col2.metric(
                            "Total Expenses", 
                            f"₹{advice_data['stats']['total_expenses']:,.2f}"
                        )
                        col3.metric(
                            "Savings Rate", 
                            f"{advice_data['stats']['savings_rate']:.0%}"
                        )
                        
                        # Top spending category
                        st.markdown(
                            f"""
                            <div style="background-color:#FFFFFF; padding:15px; border-radius:10px; margin-top:20px;">
                                <h4 style="color:#013220;">Top Spending Category</h4>
                                <p style="color:#000000; font-size:18px;">
                                    <strong>{advice_data['stats']['top_category']}</strong> - 
                                    {advice_data['stats']['top_category_percentage']:.0%} of expenses
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.error(f"Error getting advice: {response.text}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
# --- Monthly Salary ---
elif selected_page == " Monthly Salary":
    st.header(" Add Salary")
    with st.form("salary_form"):
        salary = st.number_input("Monthly Salary ₹", min_value=0.0)
        date = st.date_input("Date")
        submit_salary = st.form_submit_button("Submit")

    if submit_salary:
        try:
            data = {
                "type": "Income",
                "category": "Salary",
                "amount": salary,
                "description": "Monthly Salary",
                "date": str(date)
            }
            requests.post(f"{backend_url}/add", json=data)
            st.success("✅ Salary added.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- About Page ---
elif selected_page == " About":
    st.title(" About the App")
    st.markdown("""
    This **Personal Finance Assistant** helps you:
    - ✅ Track your daily expenses & income
    - 📊 Set and visualize budget goals
    - 📉 See trends & spending patterns
    - 🤖 Get AI-powered forecasts & financial advice
    - 💼 Monitor your salary and savings monthly
    ---
    Built with ❤️ using **Streamlit + Flask + ML**.
    """)
