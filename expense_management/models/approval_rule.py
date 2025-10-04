# -*- coding: utf-8 -*-
from odoo import models, fields, _

class ExpenseApprovalRule(models.Model):
    _name = 'expense.approval.rule'
    _description = 'Expense Approval Rule'

    name = fields.Char(required=True)
    approver_ids = fields.Many2many('res.users', string='Approvers')
    sequence = fields.Integer(string='Sequence')
    percentage_threshold = fields.Float(string='Percentage Threshold', help='e.g., 60 for 60%')
    specific_approver_id = fields.Many2one('res.users', string='Specific Approver (if approves => auto approve)')
    active = fields.Boolean(default=True)