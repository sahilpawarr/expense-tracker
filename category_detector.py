"""
Category detection for expense tracking
Helps identify common expense categories based on the expense description
"""
import re

# Define common expense categories with related keywords
EXPENSE_CATEGORIES = {
    'Groceries': [
        'grocery', 'groceries', 'food', 'vegetable', 'fruit', 'bread', 'milk', 'cheese',
        'meat', 'snack', 'snacks', 'supermarket', 'market', 'store', 'shopping'
    ],
    'Dining': [
        'restaurant', 'dining', 'lunch', 'dinner', 'breakfast', 'cafe', 'coffee',
        'food delivery', 'takeout', 'take out', 'take-out', 'meal', 'pizza', 'burger'
    ],
    'Transportation': [
        'taxi', 'cab', 'uber', 'ola', 'lyft', 'auto', 'rickshaw', 'bus', 'train', 'metro',
        'subway', 'travel', 'transport', 'car', 'petrol', 'gas', 'fuel', 'diesel', 'fare'
    ],
    'Utilities': [
        'electricity', 'water', 'gas', 'bill', 'utility', 'power', 'internet', 'wifi',
        'broadband', 'phone', 'mobile', 'landline', 'recharge'
    ],
    'Entertainment': [
        'movie', 'theater', 'cinema', 'show', 'concert', 'event', 'ticket', 'game',
        'music', 'subscription', 'netflix', 'amazon', 'disney', 'streaming'
    ],
    'Shopping': [
        'clothes', 'clothing', 'shoes', 'dress', 'shirt', 'pants', 'jeans', 'accessory',
        'accessories', 'jewelry', 'fashion', 'mall', 'apparel', 'gift', 'purchase'
    ],
    'Healthcare': [
        'medicine', 'medical', 'doctor', 'hospital', 'clinic', 'health', 'pharmacy',
        'drug', 'prescription', 'vitamin', 'healthcare', 'treatment', 'therapy'
    ],
    'Education': [
        'school', 'college', 'university', 'course', 'class', 'tuition', 'book',
        'stationery', 'education', 'study', 'training', 'workshop', 'seminar'
    ],
    'Personal Care': [
        'haircut', 'salon', 'spa', 'beauty', 'cosmetic', 'cosmetics', 'skincare',
        'grooming', 'personal', 'hygiene', 'toiletries'
    ],
    'Household': [
        'rent', 'maintenance', 'repair', 'furniture', 'appliance', 'cleaning',
        'housekeeping', 'decor', 'bedding', 'kitchen', 'bathroom', 'garden', 'tool'
    ]
}

def detect_category(text):
    """
    Detect the most likely expense category based on the text
    
    Args:
        text (str): The expense description or category text
        
    Returns:
        str: The detected category or the original text if no match found
    """
    if not text:
        return "Miscellaneous"
        
    text = text.lower()
    
    # First check for exact matches with category names
    for category in EXPENSE_CATEGORIES:
        if category.lower() in text:
            return category
    
    # Then check for keyword matches
    matches = {}
    for category, keywords in EXPENSE_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in text:
                matches[category] = matches.get(category, 0) + 1
    
    if matches:
        # Return the category with the most keyword matches
        return max(matches.items(), key=lambda x: x[1])[0]
    
    # Special case for common expenses
    if re.search(r'\btaxi\b|\bcab\b|\bauto\b|\brickshaw\b|\buber\b|\bola\b', text):
        return 'Transportation'
    
    if re.search(r'\bgrocery\b|\bvegetable\b|\bfood\b', text):
        return 'Groceries'
        
    # Return the original text as category if no match found
    # But capitalize first letter of each word for nicer formatting
    return ' '.join(word.capitalize() for word in text.split())