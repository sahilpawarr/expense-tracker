import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)

# Configure the database
database_url = os.environ.get("DATABASE_URL")
# Handle potential "postgres://" to "postgresql://" conversion for SQLAlchemy 1.4+
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///expense_tracker.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Define all models here to ensure they're created
class Configuration(db.Model):
    """Configuration settings for the expense tracker"""
    id = db.Column(db.Integer, primary_key=True)
    sheet_name = db.Column(db.String(100), nullable=False, default="Family Expenses")
    sheet_id = db.Column(db.String(100))
    is_configured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

class FamilyMember(db.Model):
    """Represents a family member who logs expenses"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # Relationship with expenses
    expenses = db.relationship('Expense', backref='family_member', lazy=True)

class Expense(db.Model):
    """Represents a single expense entry"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="rupees")
    description = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.now())
    
    # Foreign key to link to family member
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_member.id'), nullable=False)

# Removed WhatsApp related models

if __name__ == "__main__":
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        # Initialize with default family members
        config = Configuration.query.first()
        family_members = FamilyMember.query.all()
        
        if not config:
            # Create default configuration
            config = Configuration(
                sheet_name="Family Expenses",
                is_configured=True
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
        
        print("Database tables created successfully!")