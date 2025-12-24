import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__)

# Configure the Flask application
app.secret_key = os.environ.get("SESSION_SECRET", "expense_tracker_secret_key")

# Configure the SQLAlchemy database connection
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Fallback to SQLite for local development or when no DATABASE_URL is provided
    database_url = "sqlite:///expense_tracker.db"
    logger.warning("No DATABASE_URL found, using SQLite as fallback")
    
# Check if DATABASE_URL starts with postgres:// (Heroku style) and change to postgresql://
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    logger.info("Converted postgres:// to postgresql:// in DATABASE_URL")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize SQLAlchemy with the Flask application
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Default budget categories
DEFAULT_CATEGORIES = [
    "Groceries",
    "Dining",
    "Transportation", 
    "Utilities",
    "Shopping",
    "Healthcare",
    "Other"
]

class Configuration(db.Model):
    """Configuration settings for the expense tracker"""
    id = db.Column(db.Integer, primary_key=True)
    sheet_name = db.Column(db.String(100), nullable=False, default="Family Expenses")
    sheet_id = db.Column(db.String(100))
    is_configured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Default currency
    default_currency = db.Column(db.String(10), default="rupees")

class FamilyMember(db.Model):
    """Represents a family member who logs expenses"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with expenses
    expenses = db.relationship('Expense', backref='family_member', lazy=True)

class Expense(db.Model):
    """Represents a single expense entry"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="rupees")
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Store month and year of expense for easier filtering
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    # Foreign key to link to family member
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_member.id'), nullable=False)
    
    def __repr__(self):
        return f"<Expense: {self.category} {self.amount} {self.currency}>"

class Budget(db.Model):
    """Monthly budget for each expense category"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="rupees")
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Make combination of category, month, and year unique
    __table_args__ = (
        db.UniqueConstraint('category', 'month', 'year', name='uix_budget_category_month_year'),
    )
    
    def __repr__(self):
        return f"<Budget: {self.category} {self.amount} {self.currency} {self.month}/{self.year}>"

def get_current_month_year():
    """Get the current month and year"""
    now = datetime.now()
    return now.month, now.year

def get_budget_status(category, month, year):
    """
    Get budget status for a category in a specific month/year
    Returns dict with budget info, spent amount, and remaining amount
    """
    # Get budget for this category and month/year
    budget = Budget.query.filter_by(
        category=category,
        month=month,
        year=year
    ).first()
    
    # Calculate total spent in this category for the month
    expenses = Expense.query.filter_by(
        category=category,
        month=month,
        year=year
    ).all()
    
    total_spent = sum(expense.amount for expense in expenses)
    
    # Prepare the response
    budget_amount = budget.amount if budget else 0
    remaining = budget_amount - total_spent if budget else -total_spent
    
    return {
        'category': category,
        'budget': budget_amount,
        'spent': total_spent,
        'remaining': remaining,
        'over_budget': remaining < 0,
        'month': month,
        'year': year,
        'currency': budget.currency if budget else 'rupees'
    }

def initialize_database():
    """Initialize the database with default values if needed"""
    try:
        db.create_all()
        
        # Check if we need to initialize the database
        config = Configuration.query.first()
        family_members = FamilyMember.query.all()
        
        if not config:
            # Create default configuration
            config = Configuration(
                sheet_name="Family Expenses",
                is_configured=True,
                default_currency="rupees"
            )
            db.session.add(config)
            
            # Add default family members if none exist
            if not family_members:
                default_members = [
                    FamilyMember(name="Jyoti"),
                    FamilyMember(name="Prakash"),
                    FamilyMember(name="Kshitij"),
                    FamilyMember(name="Sahil")
                ]
                for member in default_members:
                    db.session.add(member)
                    
            db.session.commit()
            print("Added default family members: Jyoti, Prakash, Kshitij, Sahil")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        db.session.rollback()

# Initialize database
with app.app_context():
    initialize_database()

@app.route('/', methods=['GET', 'POST'])
def index():
    """Home page with the expense form"""
    if request.method == 'POST':
        try:
            family_member_id = request.form.get('family_member')
            category = request.form.get('category')
            amount = request.form.get('amount')
            description = request.form.get('description', '')
            
            if not family_member_id or not category or not amount:
                return render_template('expense_form.html', family_members=FamilyMember.query.all(), 
                                     error='Please fill in all required fields'), 400
            
            family_member = FamilyMember.query.get(family_member_id)
            if not family_member:
                return render_template('expense_form.html', family_members=FamilyMember.query.all(),
                                     error='Family member not found'), 404
            
            current_month, current_year = get_current_month_year()
            expense = Expense(
                category=category,
                amount=float(amount),
                currency='rupees',
                description=description,
                family_member_id=family_member.id,
                month=current_month,
                year=current_year
            )
            
            db.session.add(expense)
            db.session.commit()
            
            return render_template('expense_form.html', family_members=FamilyMember.query.all(),
                                 message=f'Expense added: {category} ₹{amount}')
        except Exception as e:
            logger.error(f"Error adding expense: {str(e)}")
            return render_template('expense_form.html', family_members=FamilyMember.query.all(),
                                 error=f'Error: {str(e)}'), 500
    
    family_members = FamilyMember.query.all()
    return render_template('expense_form.html', family_members=family_members)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Setup page for initial configuration"""
    if request.method == 'POST':
        # Process form data
        sheet_name = request.form.get('sheet_name', 'Family Expenses')
        
        # Get family member names
        member_names = [
            request.form.get('member1', 'Jyoti'),
            request.form.get('member2', 'Prakash'),
            request.form.get('member3', 'Kshitij'),
            request.form.get('member4', 'Sahil')
        ]
        
        # Create or update configuration
        try:
            config = Configuration.query.first()
            if not config:
                config = Configuration(
                    sheet_name=sheet_name,
                    is_configured=True
                )
                db.session.add(config)
            else:
                config.sheet_name = sheet_name
                config.is_configured = True
            
            # Clear existing members if reconfiguring
            FamilyMember.query.delete()
            
            for name in member_names:
                if name and name.strip():
                    member = FamilyMember(name=name.strip())
                    db.session.add(member)
            
            db.session.commit()
            flash('Setup completed successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Setup error: {str(e)}")
            flash(f'Error during setup: {str(e)}', 'danger')
    
    return render_template('setup.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard with visual representation of expenses"""
    import json
    from datetime import datetime, timedelta
    
    all_expenses = Expense.query.order_by(Expense.timestamp.desc()).all()
    
    # Get last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_expenses = [e for e in all_expenses if e.timestamp >= twenty_four_hours_ago]
    
    # Calculate monthly stats (current month only)
    now = datetime.utcnow()
    current_month = now.month
    current_year = now.year
    
    monthly_expenses = [e for e in all_expenses 
                       if e.month == current_month and e.year == current_year]
    
    monthly_total = sum(e.amount for e in monthly_expenses)
    monthly_count = len(monthly_expenses)
    
    # Monthly average: total amount / number of months with expenses
    months_with_expenses = set()
    for expense in all_expenses:
        months_with_expenses.add((expense.year, expense.month))
    
    monthly_average = round(monthly_total / len(months_with_expenses), 2) if len(months_with_expenses) > 0 else 0
    
    # Member-wise contribution (monthly)
    member_data = {}
    for expense in monthly_expenses:
        member_name = expense.family_member.name if expense.family_member else 'Unknown'
        member_data[member_name] = member_data.get(member_name, 0) + expense.amount
    
    # Category-wise distribution (monthly)
    category_data = {}
    for expense in monthly_expenses:
        category_data[expense.category] = category_data.get(expense.category, 0) + expense.amount
    
    # Month names for display
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    
    return render_template('dashboard.html', 
                         all_expenses=all_expenses,
                         recent_expenses=recent_expenses,
                         monthly_total=round(monthly_total, 2),
                         monthly_average=monthly_average,
                         member_data=json.dumps(member_data),
                         category_data=json.dumps(category_data),
                         months=months)

@app.route('/api/summary')
def expense_summary():
    """API endpoint to get expense summary data"""
    family_members = FamilyMember.query.all()
    summary = {}
    
    for member in family_members:
        member_expenses = Expense.query.filter_by(family_member_id=member.id).all()
        total = sum(expense.amount for expense in member_expenses)
        summary[member.name] = total
    
    return jsonify(summary)

@app.route('/api/expenses')
def get_expenses():
    """API endpoint to get detailed expense data for dashboard"""
    # Get recent expenses with member names
    expenses_query = db.session.query(
        Expense, FamilyMember.name.label('member_name')
    ).join(
        FamilyMember, Expense.family_member_id == FamilyMember.id
    ).order_by(
        Expense.timestamp.desc()
    ).limit(20)
    
    recent_expenses = []
    for expense, member_name in expenses_query:
        # Convert UTC timestamp to IST (UTC+5:30)
        ist_timestamp = expense.timestamp + timedelta(hours=5, minutes=30)
        recent_expenses.append({
            'id': expense.id,
            'category': expense.category,
            'amount': expense.amount,
            'currency': expense.currency,
            'description': expense.description,
            'timestamp': ist_timestamp.isoformat(),
            'month': expense.month,
            'year': expense.year,
            'member_name': member_name
        })
    
    # Calculate totals by member
    family_members = FamilyMember.query.all()
    member_totals = {}
    for member in family_members:
        member_expenses = Expense.query.filter_by(family_member_id=member.id).all()
        total = sum(expense.amount for expense in member_expenses)
        member_totals[member.name] = total
    
    # Calculate totals by category
    category_totals = db.session.query(
        Expense.category,
        func.sum(Expense.amount).label('total')
    ).group_by(
        Expense.category
    ).order_by(
        func.sum(Expense.amount).desc()
    ).all()
    
    category_data = [
        {'category': cat, 'amount': float(total)}
        for cat, total in category_totals
    ]
    
    return jsonify({
        'recent_expenses': recent_expenses,
        'member_totals': member_totals,
        'category_totals': category_data
    })

@app.route('/api/settlements')
def get_settlements():
    """API endpoint to get settlement suggestions"""
    # Get all family members
    family_members = FamilyMember.query.all()
    
    if not family_members:
        return jsonify({'error': 'No family members found'})
    
    # Calculate totals
    totals = {}
    total_expenses = 0
    currency = "rupees"
    
    # First get expenses
    all_expenses = Expense.query.all()
    if all_expenses and len(all_expenses) > 0:
        currency = all_expenses[0].currency
    
    # Calculate per member totals
    for member in family_members:
        member_expenses = Expense.query.filter_by(family_member_id=member.id).all()
        member_total = sum(expense.amount for expense in member_expenses)
        totals[member.name] = member_total
        total_expenses += member_total
    
    # Calculate fair share
    member_count = len(family_members)
    fair_share = total_expenses / member_count if member_count > 0 and total_expenses > 0 else 0
    
    # Split members into those who paid more and those who paid less
    paid_more = []
    paid_less = []
    
    for name, total in totals.items():
        difference = total - fair_share
        if difference > 1:  # More than 1 rupee difference (avoid rounding issues)
            paid_more.append((name, difference))
        elif difference < -1:  # Less than -1 rupee difference
            paid_less.append((name, -difference))
    
    # Sort by amount
    paid_more.sort(key=lambda x: x[1], reverse=True)
    paid_less.sort(key=lambda x: x[1], reverse=True)
    
    # Generate settlement suggestions
    settlements = []
    
    # Create a copy of the lists for settlement calculations
    payers = sorted(paid_less, key=lambda x: x[1], reverse=True)
    receivers = sorted(paid_more, key=lambda x: x[1], reverse=True)
    
    # Simple greedy algorithm to suggest settlements
    while payers and receivers:
        payer_name, payer_amount = payers[0]
        receiver_name, receiver_amount = receivers[0]
        
        amount_to_transfer = min(payer_amount, receiver_amount)
        
        settlements.append({
            'from': payer_name,
            'to': receiver_name,
            'amount': round(amount_to_transfer, 2)
        })
        
        # Update amounts
        payer_amount -= amount_to_transfer
        receiver_amount -= amount_to_transfer
        
        # Remove settled parties or update their remaining amounts
        if payer_amount < 1:  # Less than 1 rupee (avoid rounding issues)
            payers.pop(0)
        else:
            payers[0] = (payer_name, payer_amount)
            
        if receiver_amount < 1:  # Less than 1 rupee (avoid rounding issues)
            receivers.pop(0)
        else:
            receivers[0] = (receiver_name, receiver_amount)
    
    return jsonify({
        'total_expenses': round(total_expenses, 2),
        'fair_share': round(fair_share, 2),
        'currency': currency,
        'settlements': settlements
    })

@app.route('/api/add_expense', methods=['POST'])
def add_expense():
    """API endpoint to add a new expense from the web form"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('amount') or not data.get('category') or not data.get('familyMemberId'):
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        # Get family member
        family_member = FamilyMember.query.get(data.get('familyMemberId'))
        if not family_member:
            return jsonify({'success': False, 'error': 'Family member not found'})
        
        # Get current month and year for the expense
        current_month, current_year = get_current_month_year()
        
        # Create expense with month and year
        expense = Expense(
            category=data.get('category'),
            amount=float(data.get('amount')),
            currency=data.get('currency', 'rupees'),
            description=data.get('description', ''),
            family_member_id=family_member.id,
            month=current_month,
            year=current_year
        )
        
        db.session.add(expense)
        db.session.commit()
        
        # Calculate budget status for this category
        budget_info = get_budget_status(expense.category, current_month, current_year)
        
        # Return success with expense data
        return jsonify({
            'success': True,
            'expense': {
                'id': expense.id,
                'category': expense.category,
                'amount': expense.amount,
                'currency': expense.currency,
                'description': expense.description,
                'timestamp': (expense.timestamp + timedelta(hours=5, minutes=30)).isoformat(),
                'month': expense.month,
                'year': expense.year,
                'member_name': family_member.name
            },
            'budget_status': budget_info
        })
    except Exception as e:
        logger.error(f"Error adding expense: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recent_expenses')
def get_recent_expenses():
    """API endpoint to get the most recent expenses"""
    try:
        # Get recent expenses with member names
        expenses_query = db.session.query(
            Expense, FamilyMember.name.label('member_name')
        ).join(
            FamilyMember, Expense.family_member_id == FamilyMember.id
        ).order_by(
            Expense.timestamp.desc()
        ).limit(5)
        
        expenses = []
        for expense, member_name in expenses_query:
            # Convert UTC timestamp to IST (UTC+5:30)
            ist_timestamp = expense.timestamp + timedelta(hours=5, minutes=30)
            expenses.append({
                'id': expense.id,
                'category': expense.category,
                'amount': f"{expense.amount} {expense.currency}",
                'currency': expense.currency,
                'description': expense.description,
                'timestamp': ist_timestamp.isoformat(),
                'month': expense.month,
                'year': expense.year,
                'member_name': member_name
            })
        
        return jsonify({'success': True, 'expenses': expenses})
    except Exception as e:
        logger.error(f"Error getting recent expenses: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load recent expenses', 'message': str(e)})

@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    """API endpoint to get budget information for current month"""
    try:
        # Get current month and year
        current_month, current_year = get_current_month_year()
        
        # Get all budgets for the current month/year
        budgets = Budget.query.filter_by(
            month=current_month,
            year=current_year
        ).all()
        
        # Organize into a dictionary by category
        budget_dict = {budget.category: budget.amount for budget in budgets}
        
        # Get all expenses for the current month/year
        expenses = Expense.query.filter_by(
            month=current_month,
            year=current_year
        ).all()
        
        # Group expenses by category
        expense_by_category = {}
        for expense in expenses:
            if expense.category not in expense_by_category:
                expense_by_category[expense.category] = 0
            expense_by_category[expense.category] += expense.amount
        
        # Build combined budget and expense data
        all_categories = set(list(budget_dict.keys()) + list(expense_by_category.keys()) + DEFAULT_CATEGORIES)
        
        result = []
        for category in all_categories:
            budget_amount = budget_dict.get(category, 0)
            spent_amount = expense_by_category.get(category, 0)
            remaining = budget_amount - spent_amount
            
            result.append({
                'category': category,
                'budget': budget_amount,
                'spent': spent_amount,
                'remaining': remaining,
                'over_budget': remaining < 0,
                'month': current_month,
                'year': current_year
            })
        
        # Sort by category
        result.sort(key=lambda x: x['category'])
        
        return jsonify({
            'success': True, 
            'budgets': result,
            'month': current_month,
            'year': current_year
        })
    except Exception as e:
        logger.error(f"Error getting budget information: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/budgets', methods=['POST'])
def set_budget():
    """API endpoint to set a budget for a category"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('amount') or not data.get('category'):
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        # Get current month and year if not specified
        month = data.get('month')
        year = data.get('year')
        if not month or not year:
            month, year = get_current_month_year()
        
        # Look for existing budget for this category/month/year
        budget = Budget.query.filter_by(
            category=data.get('category'),
            month=month,
            year=year
        ).first()
        
        if budget:
            # Update existing budget
            budget.amount = float(data.get('amount'))
            budget.currency = data.get('currency', 'rupees')
        else:
            # Create new budget
            budget = Budget(
                category=data.get('category'),
                amount=float(data.get('amount')),
                currency=data.get('currency', 'rupees'),
                month=month,
                year=year
            )
            db.session.add(budget)
        
        db.session.commit()
        
        # Get the updated budget status
        budget_status = get_budget_status(budget.category, budget.month, budget.year)
        
        return jsonify({
            'success': True,
            'budget': {
                'id': budget.id,
                'category': budget.category,
                'amount': budget.amount,
                'currency': budget.currency,
                'month': budget.month,
                'year': budget.year
            },
            'budget_status': budget_status
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error setting budget: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_expense/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    """API endpoint to delete an expense by ID"""
    try:
        # Find the expense
        expense = Expense.query.get(expense_id)
        
        if not expense:
            return jsonify({'success': False, 'error': 'Expense not found'}), 404
        
        # Get the expense details for response
        family_member = FamilyMember.query.get(expense.family_member_id)
        
        # Store information for the response before deleting
        response_data = {
            'id': expense.id,
            'category': expense.category,
            'amount': expense.amount,
            'member_name': family_member.name if family_member else 'Unknown',
            'month': expense.month,
            'year': expense.year
        }
        
        # Delete the expense
        db.session.delete(expense)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Expense deleted successfully',
            'deleted_expense': response_data
        })
    except Exception as e:
        logger.error(f"Error deleting expense: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/service-worker.js')
def serve_service_worker():
    """Serve the service worker from the root for PWA support"""
    from flask import send_from_directory
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)