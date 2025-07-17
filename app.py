# --- app.py (Flask backend) ---

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import pickle
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

# Expense model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10))  # Income or Expense
    category = db.Column(db.String(80))
    amount = db.Column(db.Float)
    description = db.Column(db.String(200))
    date = db.Column(db.String(20))

# Budget model
class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), unique=True)
    limit = db.Column(db.Float)

with app.app_context():
    db.create_all()

@app.route("/add", methods=["POST"])
def add_transaction():
    data = request.get_json()
    txn = Transaction(
        type=data['type'],
        category=data['category'],
        amount=float(data['amount']),
        description=data['description'],
        date=data['date']
    )
    db.session.add(txn)
    db.session.commit()
    return jsonify({"message": "Transaction added!"}), 201

@app.route("/transactions", methods=["GET"])
def get_transactions():
    transactions = Transaction.query.all()
    result = [
        {
            "id": t.id,
            "type": t.type,
            "category": t.category,
            "amount": t.amount,
            "description": t.description,
            "date": t.date
        } for t in transactions
    ]
    return jsonify({"transactions": result}), 200
@app.route("/delete/<int:txn_id>", methods=["DELETE"])
def delete_transaction(txn_id):
    txn = Transaction.query.get(txn_id)
    if not txn:
        return jsonify({"message": "Transaction not found"}), 404
    db.session.delete(txn)
    db.session.commit()
    return jsonify({"message": "Transaction deleted successfully"}), 200


@app.route("/budget", methods=["GET"])
def get_budget():
    budgets = Budget.query.all()
    result = [
        {
            "category": b.category,
            "limit": b.limit
        } for b in budgets
    ]
    return jsonify(result)

@app.route("/budget", methods=["POST"])
def set_budget():
    data = request.get_json()
    existing = Budget.query.filter_by(category=data['category']).first()
    if existing:
        existing.limit = data['limit']
    else:
        new_budget = Budget(category=data['category'], limit=data['limit'])
        db.session.add(new_budget)
    db.session.commit()
    return jsonify({"message": "Budget goal set!"})

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import numpy as np
from datetime import datetime, timedelta

@app.route("/forecast", methods=["GET"])
def forecast():
    try:
        # Get all transactions with additional filtering
        transactions = Transaction.query.filter_by(type="Expense").order_by(Transaction.date).all()
        
        if len(transactions) < 14:  # Need at least 2 weeks of data
            return jsonify({"error": "Insufficient data for forecasting (need at least 14 days)"}), 400

        # Create DataFrame with enhanced features
        df = pd.DataFrame([{
            'date': datetime.strptime(txn.date, '%Y-%m-%d'),
            'amount': txn.amount,
            'category': txn.category
        } for txn in transactions])

        # Daily aggregation with additional features
        daily = df.groupby('date').agg({
            'amount': ['sum', 'count'],
            'category': lambda x: x.mode()[0] if not x.empty else None
        }).reset_index()
        daily.columns = ['date', 'total_amount', 'transaction_count', 'common_category']
        daily['day_of_week'] = pd.to_datetime(daily['date']).dt.dayofweek
        daily['is_weekend'] = daily['day_of_week'].isin([5, 6]).astype(int)
        
        # Create time-based features
        daily['day'] = (daily['date'] - daily['date'].min()).dt.days
        daily['rolling_avg'] = daily['total_amount'].rolling(window=7, min_periods=1).mean()
        daily['rolling_std'] = daily['total_amount'].rolling(window=7, min_periods=1).std()
        
        # Train multiple models
        X = daily[['day', 'day_of_week', 'is_weekend', 'rolling_avg']]
        y = daily['total_amount']
        
        # Model 1: Random Forest
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X, y)
        
        # Model 2: Polynomial Regression
        poly_model = make_pipeline(
            PolynomialFeatures(degree=2),
            LinearRegression()
        )
        poly_model.fit(X[['day']], y)
        
        # Generate forecast dates
        last_date = daily['date'].max()
        forecast_dates = [(last_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 8)]
        
        # Prepare features for future predictions
        future_days = [(last_date + timedelta(days=i)) for i in range(1, 8)]
        future_df = pd.DataFrame({
            'date': future_days,
            'day': [(d - daily['date'].min()).days for d in future_days],
            'day_of_week': [d.weekday() for d in future_days],
            'is_weekend': [int(d.weekday() in [5, 6]) for d in future_days],
            'rolling_avg': [daily['total_amount'].iloc[-7:].mean()] * 7
        })
        
        # Make predictions
        rf_pred = rf_model.predict(future_df[X.columns])
        poly_pred = poly_model.predict(future_df[['day']])
        
        # Combine predictions (weighted average)
        final_pred = (rf_pred * 0.7 + poly_pred * 0.3)
        
        # Calculate confidence intervals using rolling standard deviation
        avg_std = daily['rolling_std'].mean()
        
        return jsonify([{
            'date': d,
            'predicted_amount': float(p),
            'confidence_low': float(max(0, p - avg_std)),
            'confidence_high': float(p + avg_std),
            'day_of_week': datetime.strptime(d, '%Y-%m-%d').strftime('%A')
        } for i, (d, p) in enumerate(zip(forecast_dates, final_pred))])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/advisor", methods=["GET"])
def spending_advisor():
    try:
        # Get recent transactions with categories
        transactions = Transaction.query.order_by(Transaction.date.desc()).limit(30).all()
        
        if len(transactions) < 7:
            return jsonify({'advice': "Not enough data to generate advice. Please track at least 7 days of transactions."}), 200
        
        # Create DataFrame with enhanced analysis
        df = pd.DataFrame([{
            'date': txn.date,
            'amount': txn.amount,
            'type': txn.type,
            'category': txn.category,
            'description': txn.description
        } for txn in transactions])
        
        # Basic spending analysis
        expenses = df[df['type'] == "Expense"]
        income = df[df['type'] == "Income"]
        
        total_income = income['amount'].sum()
        total_expenses = expenses['amount'].sum()
        savings_rate = (total_income - total_expenses) / total_income if total_income > 0 else 0
        
        # Category analysis
        category_spending = expenses.groupby('category')['amount'].sum().sort_values(ascending=False)
        top_category = category_spending.idxmax()
        top_category_pct = category_spending.max() / total_expenses
        
        # Weekly patterns
        expenses['date'] = pd.to_datetime(expenses['date'])
        expenses['day_of_week'] = expenses['date'].dt.day_name()
        weekday_spending = expenses.groupby('day_of_week')['amount'].sum()
        
        # Generate personalized advice
        advice = []
        
        # Savings advice
        if savings_rate < 0.1:
            advice.append(f"⚠️ Low savings rate ({savings_rate:.0%}). Aim to save at least 20% of income.")
        elif savings_rate < 0.2:
            advice.append(f"Savings rate is okay ({savings_rate:.0%}), but could improve to 20%+.")
        else:
            advice.append(f"Great savings rate! ({savings_rate:.0%}) Keep it up!")
        
        # Category advice
        if top_category_pct > 0.4:
            advice.append(f"🚨 {top_category} is {top_category_pct:.0%} of spending. Consider budgeting this category.")
        elif top_category_pct > 0.25:
            advice.append(f"📊 Your top spending category is {top_category}. Look for potential savings here.")
        
        # Daily spending patterns
        max_day = weekday_spending.idxmax()
        min_day = weekday_spending.idxmin()
        if weekday_spending[max_day] > 2 * weekday_spending[min_day]:
            advice.append(f"📅 You spend {weekday_spending[max_day]/weekday_spending[min_day]:.1f}x more on {max_day}s than {min_day}s.")
        
        # Recent trend analysis
        weekly_trend = expenses.groupby(pd.Grouper(key='date', freq='W'))['amount'].sum()
        if len(weekly_trend) > 2:
            last_week = weekly_trend.iloc[-1]
            prev_week = weekly_trend.iloc[-2]
            if last_week > prev_week * 1.3:
                advice.append(f"📈 Last week's spending was {last_week/prev_week:.1f}x higher than previous week. Review recent purchases.")
        
        # If no specific advice was generated
        if not advice:
            advice.append("Your spending patterns look healthy. Keep tracking to maintain good habits!")
        
        return jsonify({
            'advice': " ".join(advice),
            'stats': {
                'total_income': float(total_income),
                'total_expenses': float(total_expenses),
                'savings_rate': float(savings_rate),
                'top_category': top_category,
                'top_category_percentage': float(top_category_pct)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "🎉 Backend is running!"

if __name__ == '__main__':
    app.run(debug=True)
