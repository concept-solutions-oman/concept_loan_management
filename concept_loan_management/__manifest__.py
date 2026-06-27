{
    'name': 'Concept Loan Management',
    'version': '17.0.1.0.0',
    'summary': 'Bank Loan & Deposit Management with Automated Amortization Schedules, Flat/Effective Interest Rates, Ledger Postings, and PDC Payment Tracking',
    'description': """
        Concept Loan Management is a feature-rich accounting and finance module for Odoo 17. 
        It automates the tracking, calculation, and posting of Bank Loans and Deposits.
        
        Key Features & SEO Keywords:
        - Odoo Loan Management System & Odoo Deposit Tracker.
        - Automated Loan Amortization Schedule: split principal and interest.
        - Interest Calculation Support: Flat Rate, Indicative Effective Rate (reducing balance on daily elapsed days), and Fixed Installments.
        - Auto Ledger Posting: direct accounting entries to Odoo Chart of Accounts (CoA).
        - Post-Dated Cheques (PDC) Integration: auto-create PDCs via concept_pdc_management.
        - Odoo 17 Accounting Companion: simplifies bank reconciliation, loan schedules, interest liabilities.
    """,
    'category': 'Accounting/Accounting',
    'author': 'Concept Solutions LLC',
    'website': 'https://www.csloman.com',
    'license': 'LGPL-3',
    'price': 20.09,
    'currency': 'USD',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/bank_loan_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

