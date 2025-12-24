import re
import logging
from category_detector import detect_category

# Configure logging
logger = logging.getLogger(__name__)

def parse_expense_message(message_text):
    """
    Parse a message containing expense information with more flexible formats
    Supports a variety of natural language patterns to extract what was spent and how much
    
    Returns:
        dict: Dictionary with parsed expense data or None if parsing failed
    """
    if not message_text:
        return None
    
    # Try to identify the key components: category, amount, and currency
    # Several regex patterns to handle different message formats
    
    # Pattern 1: "Category Amount Currency"
    pattern1 = r'([\w\s]+?)\s+(\d+(?:\.\d+)?)\s*(rupees?|rs\.?|inr|₹|dollars?|\$|euros?|€)'
    
    # Pattern 2: "Amount Currency for Category"  
    pattern2 = r'(\d+(?:\.\d+)?)\s*(rupees?|rs\.?|inr|₹|dollars?|\$|euros?|€)\s+(?:for|on|at)?\s+([\w\s]+)'
    
    # Pattern 3: Various spending verbs: "Spent/Paid/Gave Amount Currency on/for/to Category"
    pattern3 = r'(?:spent|paid|gave|bought|got|purchased|ordered)\s+(\d+(?:\.\d+)?)\s*(rupees?|rs\.?|inr|₹|dollars?|\$|euros?|€)\s+(?:for|on|at|to)?\s+([\w\s]+)'
    
    # Pattern 4: "Category cost/costs/was/is Amount Currency" 
    pattern4 = r'([\w\s]+?)(?:\s+(?:cost|costs|was|is|came to))\s+(\d+(?:\.\d+)?)\s*(rupees?|rs\.?|inr|₹|dollars?|\$|euros?|€)'
    
    # Pattern 5: Just try to extract any amount and nearby words for category
    pattern5 = r'(?:.*?)(\d+(?:\.\d+)?)\s*(rupees?|rs\.?|inr|₹|dollars?|\$|euros?|€)(?:[^a-zA-Z0-9]*)([\w\s]+)'
    
    # Pattern 6: Look for any verb + amount + currency + what it was for
    pattern6 = r'(?:.*?)\s+(\d+(?:\.\d+)?)\s*(rupees?|rs\.?|inr|₹|dollars?|\$|euros?|€)(?:.*?)(?: for | on | at )+([\w\s]+)'
    
    # Try each pattern
    match = re.search(pattern1, message_text, re.IGNORECASE)
    if match:
        category = match.group(1).strip()
        amount = float(match.group(2))
        currency = standardize_currency(match.group(3))
    else:
        match = re.search(pattern2, message_text, re.IGNORECASE)
        if match:
            amount = float(match.group(1))
            currency = standardize_currency(match.group(2))
            category = match.group(3).strip()
        else:
            match = re.search(pattern3, message_text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                currency = standardize_currency(match.group(2))
                category = match.group(3).strip()
            else:
                match = re.search(pattern4, message_text, re.IGNORECASE)
                if match:
                    category = match.group(1).strip()
                    amount = float(match.group(2))
                    currency = standardize_currency(match.group(3))
                else:
                    match = re.search(pattern5, message_text, re.IGNORECASE)
                    if match:
                        amount = float(match.group(1))
                        currency = standardize_currency(match.group(2))
                        category = match.group(3).strip()
                    else:
                        match = re.search(pattern6, message_text, re.IGNORECASE)
                        if match:
                            amount = float(match.group(1))
                            currency = standardize_currency(match.group(2))
                            category = match.group(3).strip()
                        else:
                            # Fallback pattern: just look for a number and some text
                            amount_pattern = r'(\d+(?:\.\d+)?)'
                            amount_match = re.search(amount_pattern, message_text)
                            if amount_match:
                                amount = float(amount_match.group(1))
                                # Try to extract category from words around the number
                                words = message_text.split()
                                amount_word_index = -1
                                for i, word in enumerate(words):
                                    if amount_match.group(1) in word:
                                        amount_word_index = i
                                        break
                                
                                if amount_word_index >= 0:
                                    # Try words after the amount first
                                    if amount_word_index + 1 < len(words) and not words[amount_word_index + 1].lower() in ['rupees', 'rupee', 'rs', 'rs.', 'inr', 'dollars', 'dollar', 'euros', 'euro']:
                                        category = ' '.join(words[amount_word_index + 1:])
                                    # Then try words before the amount
                                    elif amount_word_index > 0:
                                        category = ' '.join(words[:amount_word_index])
                                    else:
                                        category = "Miscellaneous"
                                else:
                                    category = "Miscellaneous"
                                
                                # Default to rupees if no currency found
                                currency = 'rupees'
                            else:
                                # Couldn't match any of the patterns
                                logger.warning(f"Could not parse expense from: {message_text}")
                                return None
    
    # Try to extract additional description
    description = ""
    if '-' in message_text:
        parts = message_text.split('-', 1)
        if len(parts) > 1:
            description = parts[1].strip()
    
    # Use the category detector to standardize the category
    detected_category = detect_category(category)
    
    # Build and return the expense data
    expense_data = {
        'category': detected_category,
        'amount': amount,
        'currency': currency,
        'description': description,
        'original_category': category  # Keep the original text for reference
    }
    
    logger.debug(f"Parsed expense: {expense_data}")
    return expense_data

def standardize_currency(currency_text):
    """Convert various currency formats to standard ones"""
    if not currency_text:
        return 'rupees'  # Default to rupees
        
    currency_text = currency_text.lower()
    
    if any(x in currency_text for x in ['rupee', 'rupees', 'rs.', 'rs', 'inr', '₹', 'r']):
        return 'rupees'
    elif any(x in currency_text for x in ['dollar', 'dollars', '$', 'usd', 'bucks']):
        return 'dollars'
    elif any(x in currency_text for x in ['euro', 'euros', '€', 'eur']):
        return 'euros'
    # Add more currencies as needed
    elif any(x in currency_text for x in ['pound', 'pounds', '£', 'gbp']):
        return 'pounds'
    elif any(x in currency_text for x in ['yen', '¥', 'jpy']):
        return 'yen'
    else:
        # If we can't determine the currency, default to rupees
        return 'rupees'
