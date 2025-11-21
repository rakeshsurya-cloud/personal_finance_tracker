"""
training_data.py

This module defines a list of example transactions and their associated
categories.  The examples are intentionally broad and cover a range of
common merchants and payment descriptions so that the text classifier has
context during training.  When you build your own system you can extend
this list with additional rows (or load your own labelled CSV) to
improve accuracy.  Each entry is a two‑element tuple of the form
(`description`, `category`).

The categories used here follow a typical personal finance breakdown,
including Shopping, Groceries, Utilities, Transportation, Rent, Income,
Health, Travel, Fuel, Dining, Fitness, Insurance, Technology, Home
Improvement and Other.  Feel free to adjust the category names to suit
your own reporting preferences.
"""

TRAINING_DATA = [
    # Shopping / retail
    ("Amazon purchase", "Shopping"),
    ("Amazon Marketplace order", "Shopping"),
    ("Ebay purchase", "Shopping"),
    ("Walmart store", "Shopping"),
    ("Target – home goods", "Shopping"),
    ("Best Buy electronics", "Shopping"),
    ("Home Depot store", "Home Improvement"),
    ("Lowe’s home improvement", "Home Improvement"),

    # Groceries
    ("Whole Foods Market", "Groceries"),
    ("Trader Joe's groceries", "Groceries"),
    ("Safeway grocery store", "Groceries"),
    ("Kroger grocery", "Groceries"),
    ("Costco membership renewal", "Groceries"),
    ("Aldi supermarket", "Groceries"),

    # Subscriptions / media
    ("Netflix subscription", "Subscriptions"),
    ("Spotify monthly", "Subscriptions"),
    ("Hulu subscription", "Subscriptions"),
    ("Disney+ subscription", "Subscriptions"),
    ("Apple Music membership", "Subscriptions"),
    ("Amazon Prime Video", "Subscriptions"),
    ("Microsoft Office subscription", "Technology"),

    # Transportation / ride sharing
    ("Uber ride", "Transportation"),
    ("Uber trip", "Transportation"),
    ("Lyft ride", "Transportation"),
    ("Lyft trip", "Transportation"),
    ("Amtrak train ticket", "Transportation"),
    ("Caltrain ticket", "Transportation"),

    # Utilities
    ("PG&E utility bill", "Utilities"),
    ("Pacific Gas and Electric payment", "Utilities"),
    ("AT&T internet", "Utilities"),
    ("Comcast Xfinity", "Utilities"),
    ("Verizon wireless", "Utilities"),
    ("Water bill", "Utilities"),

    # Rent / housing
    ("Rent payment", "Rent"),
    ("Apartment rent", "Rent"),
    ("Mortgage payment", "Rent"),
    ("HOA dues", "Rent"),

    # Income
    ("Salary deposit", "Income"),
    ("Paycheck direct deposit", "Income"),
    ("Contractor payment", "Income"),
    ("Freelance income", "Income"),

    # Health / medical
    ("Kaiser Permanente hospital", "Health"),
    ("Doctor visit copay", "Health"),
    ("CVS Pharmacy", "Health"),
    ("Walgreens pharmacy", "Health"),
    ("Dental office", "Health"),
    ("Vision care center", "Health"),

    # Travel
    ("United Airlines flight", "Travel"),
    ("American Airlines ticket", "Travel"),
    ("Delta Air Lines", "Travel"),
    ("Southwest Airlines", "Travel"),
    ("Airbnb reservation", "Travel"),
    ("Booking.com hotel", "Travel"),
    ("Expedia travel booking", "Travel"),

    # Fuel / gas
    ("Shell gas", "Fuel"),
    ("Chevron gas station", "Fuel"),
    ("Exxon gas", "Fuel"),
    ("BP fuel", "Fuel"),
    ("Fuel purchase", "Fuel"),

    # Dining / restaurants
    ("Starbucks coffee", "Dining"),
    ("McDonald's meal", "Dining"),
    ("Subway sandwich", "Dining"),
    ("Chipotle Mexican Grill", "Dining"),
    ("Domino's pizza", "Dining"),
    ("Pizza Hut", "Dining"),

    # Fitness / recreation
    ("Gold's Gym membership", "Fitness"),
    ("24 Hour Fitness membership", "Fitness"),
    ("Planet Fitness", "Fitness"),
    ("Yoga studio", "Fitness"),
    ("Peloton subscription", "Fitness"),

    # Insurance
    ("State Farm insurance", "Insurance"),
    ("Geico auto insurance", "Insurance"),
    ("Allstate insurance", "Insurance"),
    ("Progressive insurance", "Insurance"),
    ("Nationwide insurance", "Insurance"),

    # Technology / electronics / software
    ("Apple App Store purchase", "Technology"),
    ("Google Play purchase", "Technology"),
    ("Adobe Creative Cloud", "Technology"),
    ("Dropbox subscription", "Technology"),
    ("GitHub subscription", "Technology"),

    # Home improvement / maintenance
    ("IKEA home furnishing", "Home Improvement"),
    ("Ace Hardware", "Home Improvement"),
    ("Gardening supplies", "Home Improvement"),
    ("Lawn mower purchase", "Home Improvement"),
    ("Home cleaning service", "Home Improvement"),

    # Other catch‑all
    ("Donation to charity", "Other"),
    ("Tax payment", "Other"),
    ("Miscellaneous expense", "Other"),
    ("Unknown transaction", "Other"),
]