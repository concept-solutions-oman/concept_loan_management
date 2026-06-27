{
    'name': 'Concept Loan Management',
    'version': '17.0.1.0.0',
    'summary': 'Manage Bank Loans and Deposits with Amortization Schedule',
    'description': """
        Manage Bank Loans/Deposits with amortization schedule and PDC payment tracking.
    """,
    'category': 'Accounting/Accounting',
    'author': 'Concept Solutions',
    'website': 'https://www.csloman.com',
    'license': 'LGPL-3',
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
