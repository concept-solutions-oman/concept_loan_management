# Concept Loan Management

Manage Bank Loans and Deposits with dynamic amortization schedules, automated ledger postings, and Post-Dated Cheque (PDC) integration in Odoo 17.

## Key Features

- **Flexible Interest Calculations**:
  - **Flat Rate**: Calculates fixed monthly interest based on total loan amount and duration.
  - **Indicative Effective Rate**: Computes interest on a daily basis using actual elapsed days.
  - **Fixed Amount**: Generates schedules matching a custom fixed installment value.
- **Automated Amortization Schedule**: Automatically divides monthly installments into Principal and Interest, detailing the remaining outstanding balance.
- **Chart of Accounts (CoA) Integration**: Directly posts loan allocations, looking up payable and deferred interest/suspense accounts under selected partners.
- **Optional PDC Integration**: Instantly generates Post Dated Cheques matching the computed installments in a single click if `concept_pdc_management` is installed, complete with a smart count dashboard.

## Module Structure

- `data/`: Sequence generator definitions for unique loan naming.
- `models/`: Custom business logic for `concept.bank.loan`, schedule lines, and PDC hooks.
- `security/`: Access controls for normal and manager profiles.
- `static/description/`: Store icons and custom app description landing pages.
- `views/`: Standard Odoo views, action menus, and form views.

## Installation

1. Place the `concept_loan_management` folder in your Odoo custom addons directory.
2. (Optional) Install the `concept_pdc_management` module if you want to enable automatic post-dated cheque generation.
3. Update your Odoo Apps list and install **Concept Loan Management**.

## License

This module is licensed under the **LGPL-3** license. Developed by [Concept Solutions](https://www.conceptsolutions.com).
