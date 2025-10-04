# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrExpense(models.Model):
    _inherit = "hr.expense.sheet"
    
    approver_line_ids = fields.One2many('expense.approver.line','expense_sheet_id', string='Approver Lines')
    approval_rule_id = fields.Many2one('expense.approval.rule', string='Approval Rule')
    is_approved_button = fields.Boolean(compute='_compute_approved_access', default=False)
    is_manager_approver = fields.Boolean('Is manager an approver')
    
    def _compute_approved_access(self):
        for rec in self:
            user_ids = rec.approver_line_ids.filtered(lambda l: l.approved_state != 'approved')
            approved_user = rec.approver_line_ids.mapped('user_id')
            if not user_ids and rec.state == 'submit':
                rec.state = 'approve'
            if rec.is_manager_approver and self.env.user.id == rec.user_id.id:
                approved_user = approved_user + rec.user_id
            if  self.env.user in approved_user:
                   rec.is_approved_button = True
            else:
                rec.is_approved_button = False
    
    def action_submit_sheet(self):
        res = super(HrExpense, self).action_submit_sheet()
        for rec in self:
            if not rec.approver_line_ids:
                rec._populate_approver_lines()
            # notify first approver
            first = rec.approver_line_ids.filtered(lambda l: l.sequence==1)
            if first and first.user_id:
                    first.user_id.partner_id.message_post(body=_('Expense %s awaits your approval')%rec.name)
        return res
    
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
            
    def action_approve_expense_sheets(self):
        for rec in self:
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
                    })]
                })
            else:
                if self.env.user in user_ids:
                    current = pending[0]
                    current.approved = True
                    current.comment = comment
                    current.approved_state= 'approved'
                    # evaluate conditional rules
                    if rec._check_auto_approval():
                        rec._finalize_approval()
                        return True                    
        return True
    

        
    def action_reject(self, comment=None, approver_user=None):
        for rec in self:
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
            
            
            
        