from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class ConceptBankLoan(models.Model):
    _name = 'concept.bank.loan'
    _description = 'Bank Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    journal_id = fields.Many2one('account.journal', string='Bank', domain=[('type', '=', 'bank')], required=True)
    partner_id = fields.Many2one('res.partner', string='Vendor Name', help="Vendor Name")
    vendor_id = fields.Many2one('res.partner', string='Finance Company Name', help="Finance Company Name")
    
    loan_amount = fields.Float(string='Loan Amount', digits=(16, 3), required=True)
    total_interest_amount = fields.Float(string='Interest Amount', digits=(16, 3))
    gross_amount = fields.Float(string='Gross Amount', compute='_compute_gross_amount', store=True, digits=(16, 3))
    
    rate_type = fields.Selection([
        ('flat', 'Flat Rate'),
        ('effective', 'Indicative Effective Rate')
    ], string='Rate Type', default='flat', required=True)
    flat_rate = fields.Float(string='Flat Rate (%)', digits=(16, 2), help="Flat Interest Rate per Annum")
    indicative_effective_rate = fields.Float(string='Indicative Effective Rate (%)', digits=(16, 2)) 
    
    date = fields.Date(string='First Installment', default=fields.Date.context_today, required=True, help="Date of the first payment")
    disbursal_date = fields.Date(string='Disbursal Date', default=fields.Date.context_today, required=True, help="Date when loan was given")
    duration_months = fields.Integer(string='Duration (Months)', default=12, required=True)
    fixed_amount = fields.Boolean(string='Fixed Amount')
    fixed_amount_value = fields.Float(string='Fixed Amount Value', digits=(16, 3))
    account_id = fields.Many2one('account.account', string='Chart of Accounts', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('pdc', 'PDC')
    ], string='Status', default='draft', copy=False, tracking=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    
    line_ids = fields.One2many('concept.bank.loan.line', 'loan_id', string='Monthly Details')
    pdc_count = fields.Integer(compute='_compute_pdc_count', string='PDC Count')
    is_pdc_installed = fields.Boolean(compute='_compute_is_pdc_installed', string='Is PDC Installed')

    def _compute_is_pdc_installed(self):
        has_pdc = 'pdc.management' in self.env
        for loan in self:
            loan.is_pdc_installed = has_pdc

    def _compute_pdc_count(self):
        has_pdc = 'pdc.management' in self.env
        for loan in self:
            if has_pdc:
                # Count PDC records from pdc.management where notes contain this loan's name
                loan.pdc_count = self.env['pdc.management'].search_count([('notes', 'ilike', loan.name)])
            else:
                loan.pdc_count = 0

    @api.depends('loan_amount', 'total_interest_amount')
    def _compute_gross_amount(self):
        for loan in self:
            loan.gross_amount = loan.loan_amount + loan.total_interest_amount

    @api.onchange('loan_amount', 'flat_rate', 'duration_months')
    def _onchange_calculate_interest(self):
        for loan in self:
            if loan.loan_amount and loan.flat_rate and loan.duration_months:
                # Flat Rate Calculation: Interest = Principal * Rate * (Duration/12)
                # Rate is percentage.
                interest = loan.loan_amount * (loan.flat_rate / 100) * (loan.duration_months / 12)
                loan.total_interest_amount = interest

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('concept.bank.loan') or 'New'
        return super(ConceptBankLoan, self).create(vals)

    def action_compute_schedule(self):
        for loan in self:
            loan.line_ids.unlink()
            lines = []
            
            start_date = loan.date
            # For daily calculation, start from Disbursal Date + 1 day (Bank logic usually excludes disbursal day)
            prev_date = loan.disbursal_date + relativedelta(days=1) if loan.disbursal_date else start_date
            
            balance_principal = loan.loan_amount
            actual_total_interest = 0.0
            
            # Rate variables
            # For daily, we use the yearly rate directly in the formula: Balance * (Rate/100) * (Days/365)
            yearly_rate = 0.0
            if loan.rate_type == 'effective' and loan.indicative_effective_rate:
                yearly_rate = loan.indicative_effective_rate / 100
            
            # EMI Calculation for Effective Rate (if not fixed amount)
            # Standard EMI formula usually assumes equal intervals (monthly). 
            # If we want strict Daily Interest + Fixed EMI, we might still use the standard EMI as a distinct "Target Total"
            # Or usually, users provide a Fixed Amount for these types of loans.
            standard_emi = 0.0
            if loan.rate_type == 'effective' and not loan.fixed_amount and yearly_rate > 0 and loan.duration_months > 0:
                # Approximate EMI using monthly formula for estimation
                r = yearly_rate / 12
                n = loan.duration_months
                try:
                    standard_emi = loan.loan_amount * r * ((1 + r)**n) / (((1 + r)**n) - 1)
                except ZeroDivisionError:
                    standard_emi = 0.0
            
            # Helper for Flat Rate
            flat_monthly_interest = 0.0
            flat_monthly_principal = 0.0
            if loan.rate_type == 'flat':
                if loan.duration_months > 0:
                     # Re-calculate total interest based on flat rate field if available, else trust existing field
                    if loan.flat_rate:
                        total_int = loan.loan_amount * (loan.flat_rate / 100) * (loan.duration_months / 12)
                    else:
                        total_int = loan.total_interest_amount
                    
                    flat_monthly_interest = total_int / loan.duration_months
                    flat_monthly_principal = loan.loan_amount / loan.duration_months
            
            for i in range(loan.duration_months):
                date = start_date + relativedelta(months=i)
                current_interest = 0.0
                current_principal = 0.0
                current_total = 0.0

                # 1. Calculate Interest
                if loan.rate_type == 'effective':
                    # Daily Interest Calculation: Actual / 365
                    # Calculate days from previous date
                    # Note: We use 'date' which is the payment date.
                    # The first payment is roughly 1 month from start.
                    # Warning: relativedelta(months=i) keeps the day component (e.g. 25th to 25th).
                    # So days will vary (28, 30, 31).
                    
                    days = (date - prev_date).days
                    current_interest = balance_principal * yearly_rate * (days / 365.0)
                else:
                    current_interest = flat_monthly_interest
                
                # 2. Calculate Total (EMI) and Principal
                if loan.fixed_amount and loan.fixed_amount_value > 0:
                     current_total = loan.fixed_amount_value
                else:
                    if loan.rate_type == 'effective':
                        current_total = standard_emi
                    else:
                        # Flat Rate
                        current_principal = flat_monthly_principal
                        current_total = current_principal + current_interest
                
                # If Effective/Fixed, derive Principal from Total
                if loan.rate_type == 'effective' or loan.fixed_amount:
                    current_principal = current_total - current_interest
                
                # 3. Last Installment / rounding / Payoff Check
                is_last = (i == loan.duration_months - 1)
                
                if loan.rate_type == 'effective' or loan.fixed_amount:
                    # If principal ends up being more than balance (early payoff) or last month correction
                    if current_principal > balance_principal:
                         current_principal = balance_principal
                         current_total = current_principal + current_interest
                         
                    if is_last:
                        current_principal = balance_principal
                        
                        # Reconcile with Target Gross if User entered a specific Interest Amount
                        # Target Gross = Loan Amount + User Entered Interest
                        # If user didn't enter interest, we calculate naturally.
                        # Check: We know 'loan.total_interest_amount' is user entered/preserved.
                        
                        target_gross = loan.loan_amount + loan.total_interest_amount
                        accumulated_total_so_far = sum(line[2]['total_amount'] for line in lines)
                        
                        # The last total must cover the difference
                        # Warning: If user entered "0" interest pending calculation, this might break.
                        # Assumption: If total_interest_amount > 0, we match it.
                        if loan.total_interest_amount > 0:
                             required_last_total = target_gross - accumulated_total_so_far
                             
                             # Prioritize matching the Total
                             current_total = required_last_total
                             
                             # Adjust interest to match the total (balancing figure)
                             current_interest = current_total - current_principal
                             
                             # Sanity check: Interest shouldn't be negative unless numbers are weird.
                             if current_interest < 0:
                                 # Fallback: If balancing makes interest negative, we can't fully match Gross.
                                 # We just pay off principal plus calculated interest.
                                 # But User wants 120. 
                                 current_interest = balance_principal * yearly_rate * (days / 365.0) # Recalculate natural
                                 current_total = current_principal + current_interest
                        else:
                             # Natural calculation
                             current_total = current_principal + current_interest

                # Update trackers
                balance_principal -= current_principal
                actual_total_interest += current_interest
                prev_date = date # Update previous date for next iteration
                
                lines.append((0, 0, {
                    'month_date': date,
                    'amount': round(current_principal, 3),
                    'interest_amount': round(current_interest, 3),
                    'total_amount': round(current_total, 3),
                    'balance_amount': round(max(0.0, balance_principal), 3),
                }))
                
                if balance_principal <= 0.000001 and loan.fixed_amount:
                     # Stop if fully paid early
                     break
            
            loan.write({'line_ids': lines})
            
            # Update header totals to match schedule (especially for effective rate)
            # User Request: Do NOT update user-entered Total Interest Amount.
            # Only update Gross Amount if Total Interest changes (via compute dependency) or if needed.
            # loan.total_interest_amount = actual_total_interest
            # loan.gross_amount = loan.loan_amount + actual_total_interest

    def action_create_entry(self):
        for loan in self:
            if loan.state == 'posted':
                continue
            
            # Find Payable Account 201002
            payable_account = self.env['account.account'].search([
                ('code', '=', '201002'),
                ('company_id', '=', loan.company_id.id)
            ], limit=1)
            
            if not payable_account:
                 raise models.UserError("Could not find account with code '201002' Payable Account. Please ensure it exists.")

            move_vals = {
                'ref': loan.name,
                'date': loan.date,
                'journal_id': loan.journal_id.id,
                'move_type': 'entry',
                'line_ids': [
                    (0, 0, {
                        'account_id': payable_account.id,
                        'partner_id': loan.partner_id.id,
                        'name': 'Bank Loan - ' + loan.name,
                        'debit': loan.loan_amount,
                        'credit': 0.0,
                        'currency_id': loan.currency_id.id,
                    }),
                    (0, 0, {
                        'account_id': loan.account_id.id,
                        'partner_id': loan.vendor_id.id,
                        'name': 'Bank Loan - ' + loan.name,
                        'debit': 0.0,
                        'credit': loan.loan_amount,
                        'currency_id': loan.currency_id.id,
                    }),
                ]
            }

            # Add Deferred Interest Lines if applicable
            if loan.total_interest_amount > 0:
                deferred_interest_account = self.env['account.account'].search([
                    ('name', 'ilike', 'Deferred Interest Account'),
                    ('company_id', '=', loan.company_id.id)
                ], limit=1)
                
                deferred_outstanding_account = self.env['account.account'].search([
                    ('name', 'ilike', 'Deferred Interest Suspense Account'),
                    ('company_id', '=', loan.company_id.id)
                ], limit=1)

                if not deferred_interest_account:
                    raise models.UserError("Could not find account with name 'Deferred Interest Account'. Please create it in the Chart of Accounts.")
                if not deferred_outstanding_account:
                    raise models.UserError("Could not find account with name 'Deferred Interest Suspense Account'. Please create it in the Chart of Accounts.")

                move_vals['line_ids'].extend([
                    (0, 0, {
                        'account_id': deferred_outstanding_account.id,
                        'partner_id': loan.partner_id.id,
                        'name': 'Deferred Interest - ' + loan.name,
                        'debit': loan.total_interest_amount,
                        'credit': 0.0,
                        'currency_id': loan.currency_id.id,
                    }),
                    (0, 0, {
                        'account_id': deferred_interest_account.id,
                        'partner_id': loan.vendor_id.id,
                        'name': 'Deferred Interest - ' + loan.name,
                        'debit': 0.0,
                        'credit': loan.total_interest_amount,
                        'currency_id': loan.currency_id.id,
                    }),
                ])
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            loan.write({
                'state': 'posted',
                'move_id': move.id,
            })

    def action_view_journal_entry(self):
        self.ensure_one()
        return {
            'name': 'Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }

    def action_create_pdc(self):
        """Create PDC records in pdc.management for each loan line"""
        if 'pdc.management' not in self.env:
            raise models.UserError("The Post Dated Cheques (PDC) Management module is not installed. Please install it to use this feature.")
        for loan in self:
            pdc_vals_list = []
            for line in loan.line_ids:
                pdc_vals = {
                    'customer_type': 'vendor',  # Outgoing payments for vendor/bank
                    'partner_id': loan.vendor_id.id,
                    'journal_id': loan.journal_id.id,
                    'amount': line.total_amount,
                    'date': line.month_date,
                    'notes': f"Bank Loan: {loan.name} - Installment: {line.month_date}",
                    # 'state': 'draft',  # Default is draft
                }
                pdc_vals_list.append(pdc_vals)
            
            if pdc_vals_list:
                self.env['pdc.management'].create(pdc_vals_list)
                loan.state = 'pdc'  # Move to PDC stage after creation

    def action_view_pdc(self):
        """Open the PDCs created for this loan"""
        if 'pdc.management' not in self.env:
            raise models.UserError("The Post Dated Cheques (PDC) Management module is not installed. Please install it to use this feature.")
        self.ensure_one()
        # Find PDC records by notes containing loan name as a simple filter
        # A more robust solution would add a loan_id field to pdc.management, 
        # but for now we use notes as an identifier.
        return {
            'name': 'Post Dated Checks',
            'type': 'ir.actions.act_window',
            'res_model': 'pdc.management',
            'view_mode': 'tree,form',
            'domain': [('notes', 'ilike', self.name)],
            'context': {'default_customer_type': 'vendor'},
        }

class ConceptBankLoanLine(models.Model):
    _name = 'concept.bank.loan.line'
    _description = 'Bank Loan Line'

    loan_id = fields.Many2one('concept.bank.loan', string='Loan', ondelete='cascade')
    month_date = fields.Date(string='Month')
    amount = fields.Float(string='Principal Amount', digits=(16, 3))
    interest_amount = fields.Float(string='Interest Amount', digits=(16, 3))
    total_amount = fields.Float(string='Total Amount', digits=(16, 3))
    balance_amount = fields.Float(string='O/S Prin.', digits=(16, 3))
    currency_id = fields.Many2one('res.currency', related='loan_id.currency_id')
