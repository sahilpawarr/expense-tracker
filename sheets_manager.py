import os
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logger = logging.getLogger(__name__)

# The scope we need for read/write access to Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheet_service():
    """
    Create and return a Google Sheets API service object
    
    Returns:
        service: Google Sheets API service object or None if authentication fails
    """
    try:
        # Try to get credentials from environment
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        
        if not creds_json:
            logger.error("No Google Sheets credentials found in environment")
            return None
        
        # Load credentials from the environment variable
        import json
        from tempfile import NamedTemporaryFile
        
        # Create a temporary file to hold the credentials
        with NamedTemporaryFile(suffix='.json', delete=False) as temp:
            temp.write(creds_json.encode())
            temp_path = temp.name
        
        # Use the temporary credentials file
        try:
            credentials = service_account.Credentials.from_service_account_file(
                temp_path, scopes=SCOPES)
            
            # Build and return the service
            service = build('sheets', 'v4', credentials=credentials)
            return service
            
        finally:
            # Always clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"Error setting up Google Sheets service: {str(e)}")
        return None

def setup_sheets(service, sheet_name="Family Expenses"):
    """
    Create a new Google Sheet for tracking family expenses
    
    Args:
        service: Google Sheets API service object
        sheet_name: Name for the new spreadsheet
        
    Returns:
        str: ID of the created spreadsheet
    """
    try:
        # Create a new spreadsheet
        spreadsheet_body = {
            'properties': {
                'title': sheet_name
            },
            'sheets': [
                {
                    'properties': {
                        'title': 'Expenses',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 7
                        }
                    }
                },
                {
                    'properties': {
                        'title': 'Summary',
                        'gridProperties': {
                            'rowCount': 100,
                            'columnCount': 5
                        }
                    }
                }
            ]
        }
        
        spreadsheet = service.spreadsheets().create(body=spreadsheet_body).execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        
        # Set up the headers for the Expenses sheet
        expense_headers = [
            ["Date", "Time", "Person", "Category", "Amount", "Currency", "Description"]
        ]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Expenses!A1:G1',
            valueInputOption='RAW',
            body={'values': expense_headers}
        ).execute()
        
        # Set up the headers for the Summary sheet
        summary_headers = [
            ["Family Member", "Total Spent", "Currency", "% of Total", "Balance"]
        ]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Summary!A1:E1',
            valueInputOption='RAW',
            body={'values': summary_headers}
        ).execute()
        
        # Format headers to be bold
        format_request = {
            'requests': [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': 0,  # First sheet (Expenses)
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {
                                    'bold': True
                                },
                                'backgroundColor': {
                                    'red': 0.9,
                                    'green': 0.9,
                                    'blue': 0.9
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                    }
                },
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': 1,  # Second sheet (Summary)
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {
                                    'bold': True
                                },
                                'backgroundColor': {
                                    'red': 0.9,
                                    'green': 0.9,
                                    'blue': 0.9
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                    }
                }
            ]
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=format_request
        ).execute()
        
        logger.info(f"Created new spreadsheet with ID: {spreadsheet_id}")
        return spreadsheet_id
        
    except HttpError as e:
        logger.error(f"Error creating Google Sheet: {str(e)}")
        raise

def append_expense_to_sheet(spreadsheet_id, person, category, amount, currency, description, timestamp=None):
    """
    Add a new expense entry to the Google Sheet
    
    Args:
        spreadsheet_id: ID of the Google Sheet
        person: Name of the family member
        category: Expense category
        amount: Expense amount
        currency: Currency of the expense
        description: Optional description
        timestamp: When the expense occurred (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # Format the date and time
    date_str = timestamp.strftime('%Y-%m-%d')
    time_str = timestamp.strftime('%H:%M:%S')
    
    # Create row data
    row_data = [
        [date_str, time_str, person, category, amount, currency, description]
    ]
    
    try:
        # Get the sheet service
        service = get_sheet_service()
        if not service:
            logger.error("Could not get Google Sheets service")
            return False
        
        # Append the data
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range='Expenses!A:G',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': row_data}
        ).execute()
        
        # Update the summary sheet
        update_summary_sheet(service, spreadsheet_id)
        
        return True
        
    except HttpError as e:
        logger.error(f"Error appending to Google Sheet: {str(e)}")
        return False

def update_summary_sheet(service, spreadsheet_id):
    """
    Update the summary sheet with the latest totals
    
    Args:
        service: Google Sheets API service object
        spreadsheet_id: ID of the Google Sheet
    """
    try:
        # Get all expense data
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Expenses!A2:G'
        ).execute()
        
        rows = result.get('values', [])
        if not rows:
            logger.info("No expense data found")
            return
        
        # Calculate totals per person
        totals = {}
        currency = 'rupees'  # Default currency
        
        for row in rows:
            if len(row) >= 6:  # Ensure we have all needed columns
                person = row[2] if len(row) > 2 else "Unknown"
                try:
                    amount = float(row[4]) if len(row) > 4 and row[4] else 0
                    curr = row[5] if len(row) > 5 and row[5] else currency
                    
                    if person not in totals:
                        totals[person] = {curr: amount}
                    else:
                        if curr in totals[person]:
                            totals[person][curr] += amount
                        else:
                            totals[person][curr] = amount
                            
                    # Keep track of the most common currency
                    if curr:
                        currency = curr
                except (ValueError, TypeError):
                    continue
        
        # Calculate grand total
        grand_total = sum(sum(amounts.values()) for amounts in totals.values())
        
        # Calculate fair share
        member_count = len(totals) or 1  # Avoid division by zero
        fair_share = grand_total / member_count
        
        # Prepare summary data
        summary_data = []
        for person, amounts in totals.items():
            person_total = sum(amounts.values())
            percentage = (person_total / grand_total * 100) if grand_total > 0 else 0
            balance = person_total - fair_share
            
            summary_data.append([
                person,
                person_total,
                currency,
                f"{percentage:.2f}%",
                balance
            ])
        
        # Clear existing summary data
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range='Summary!A2:E100'
        ).execute()
        
        # Update with new summary data
        if summary_data:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Summary!A2',
                valueInputOption='RAW',
                body={'values': summary_data}
            ).execute()
            
        # Add a row with the totals
        totals_row = [
            "TOTAL",
            grand_total,
            currency,
            "100.00%",
            0  # Balance should sum to zero
        ]
        
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f'Summary!A{len(summary_data) + 3}',  # Leave a blank row
            valueInputOption='RAW',
            body={'values': [totals_row]}
        ).execute()
        
        # Format summary sheet
        format_summary(service, spreadsheet_id, len(summary_data) + 3)
        
    except HttpError as e:
        logger.error(f"Error updating summary: {str(e)}")

def format_summary(service, spreadsheet_id, total_row):
    """Apply formatting to the summary sheet"""
    try:
        # Format the total row
        format_request = {
            'requests': [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': 1,  # Summary sheet
                            'startRowIndex': total_row - 1,
                            'endRowIndex': total_row
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {
                                    'bold': True
                                },
                                'backgroundColor': {
                                    'red': 0.95,
                                    'green': 0.95,
                                    'blue': 0.95
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                    }
                }
            ]
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=format_request
        ).execute()
        
    except HttpError as e:
        logger.error(f"Error formatting summary: {str(e)}")
