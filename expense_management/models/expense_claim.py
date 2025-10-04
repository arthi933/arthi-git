# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

class ExpenseClaim(models.Model):
    _name = 'expense.claim'
    _description = 'Expense Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    user_id = fields.Many2one('res.users', string='Manager', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=False)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    original_currency = fields.Char(string='Original Currency', help='Currency used while submitting (if different)')
    category = fields.Selection([('travel','Travel'),('meals','Meals'),('office','Office'),('other','Other')], string='Category', default='other')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    description = fields.Text(string='Description')
    attachment_ids = fields.Many2many('ir.attachment', string='Receipts')
    state = fields.Selection([('draft','Draft'),('to_approve','To Approve'),('approved','Approved'),('rejected','Rejected')], default='draft', tracking=True)

    approver_line_ids = fields.One2many('expense.approver.line','expense_id', string='Approver Lines')
    approval_rule_id = fields.Many2one('expense.approval.rule', string='Approval Rule')

    approved_by = fields.Many2one('res.users', string='Approved By')
    is_manager_approver = fields.Boolean('Is manager an approver')
    is_approved_button = fields.Boolean(compute='_compute_approved_access', default=False)
    
    def _compute_approved_access(self):
        for rec in self:
            approved_user = rec.approver_line_ids.mapped('user_id')
            if rec.is_manager_approver and self.env.user.id == rec.user_id.id:
                approved_user = approved_user + rec.user_id
            if  self.env.user in approved_user:
                   rec.is_approved_button = True
            else:
                rec.is_approved_button = False

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            seq = self.env.ref('expense_management.seq_expense', raise_if_not_found=False)
            if seq:
                vals['name'] = seq.next_by_id() or 'EXP/0000'
        res = super().create(vals)
        return res

    def action_submit(self):
        for rec in self:
            # Prepare approver lines if rule exists or fallback to manager
            if not rec.approver_line_ids:
                rec._populate_approver_lines()
            rec.state = 'to_approve'
            rec.message_post(body=_('Submitted for approval'))
            # notify first approver
            first = rec.approver_line_ids.filtered(lambda l: l.sequence==1)
            if first and first.user_id:
                first.user_id.partner_id.message_post(body=_('Expense %s awaits your approval')%rec.name)

    def _populate_approver_lines(self):
        self.ensure_one()
        rule = self.approval_rule_id
        lines = []
        if rule:
            for i, ap in enumerate(rule.approver_ids, start=1):
                lines.append((0,0,{'sequence': i, 'user_id': ap.id}))
        else:
            # default: employee's manager chain
            if self.employee_id.parent_id and self.employee_id.parent_id.user_id:
                lines.append((0,0,{'sequence':1,'user_id':self.employee_id.parent_id.user_id.id}))
        if lines:
            self.approver_line_ids = lines

    def action_approve(self, comment=None, approver_user=None):
        # Called by an approver
        for rec in self:
            # find current pending approver
            pending = rec.approver_line_ids.sorted('sequence').filtered(lambda l: not l.approved)
            if not pending:
                raise exceptions.UserError(_('No pending approver'))
            
            user_ids = rec.approver_line_ids.filtered(lambda l: l.approved_state != 'approved').mapped('user_id')
            manager_approved_id = rec.approver_line_ids.filtered(lambda l: l.user_id.id == self.user_id.id).mapped('user_id')
            if rec.is_manager_approver and not manager_approved_id:
                next_sequence = max(rec.approver_line_ids.mapped('sequence'), default=0) + 1
                rec.write({
                    'approver_line_ids': [(0, 0, {
                        'sequence': next_sequence,
                        'user_id': rec.user_id.id,
                        'approved': True,
                        'approved_state': 'approved',
                        'approved_by': approver_user or self.env.user
                    })]
                })
                rec._finalize_approval()
            else:
                if self.env.user in user_ids:
                    current = pending[0]
                    current.approved = True
                    current.comment = comment
                    current.approved_state= 'approved'
                    current.approved_by = approver_user or self.env.user
                    rec.message_post(body=_('Approved by %s')% (current.approved_by.name))
                    # evaluate conditional rules
                    if rec._check_auto_approval():
                        rec._finalize_approval()
                        return True
                    # move to next approver
                    next_pending = rec.approver_line_ids.sorted('sequence').filtered(lambda l: not l.approved)
                    if not next_pending:
                        rec._finalize_approval()
                    else:
                        # notify next
                        np = next_pending[0]
                        if np.user_id:
                            np.user_id.partner_id.message_post(body=_('Expense %s awaits your approval')%rec.name)
        return True

    def action_reject(self, comment=None, approver_user=None):
        for rec in self:
            rec.state = 'rejected'
            user_id = rec.approver_line_ids.filtered(lambda l: l.user_id.id == self.env.user.id)
            user_id.update({'approved_state': 'rejected'})
            rec.message_post(body=_('Rejected: %s') % (comment or ''))

    def _check_auto_approval(self):
        # Check if approval_rule causes auto approval (percentage or specific approver)
        self.ensure_one()
        rule = self.approval_rule_id
        if not rule:
            return False
        # percentage
        if rule.percentage_threshold:
            total = len(self.approver_line_ids)
            approved = len(self.approver_line_ids.filtered(lambda l: l.approved))
            percent = (approved / total)*100 if total else 0
            if percent >= rule.percentage_threshold:
                return True
        # specific approver
        if rule.specific_approver_id:
            # if that approver approved
            line = self.approver_line_ids.filtered(lambda l: l.user_id == rule.specific_approver_id)
            if line and line.approved:
                return True
        # hybrid: either condition is enough
        return False

    def _finalize_approval(self):
        self.state = 'approved'
        self.approved_by = self.env.user
        self.message_post(body=_('Expense approved'))


class ExpenseApproverLine(models.Model):
    _name = 'expense.approver.line'
    _description = 'Expense Approver Line'

    expense_id = fields.Many2one('expense.claim', string='Expense')
    sequence = fields.Integer(default=1)
    user_id = fields.Many2one('res.users', string='Approver')
    approved_state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        string='Status',
        default='pending'
    )
    approved = fields.Boolean(default=False)
    comment = fields.Text()
    approved_by = fields.Many2one('res.users')