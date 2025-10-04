# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class ExpensePortal(http.Controller):

    @http.route(['/my/expenses'], type='http', auth='user', website=True)
    def my_expenses(self, **kw):
        user = request.env.user
        employee = request.env['hr.employee'].search([('user_id','=',user.id)], limit=1)
        expenses = request.env['expense.claim'].sudo().search([('employee_id','=',employee.id)]) if employee else []
        return request.render('expense_management_hackathon.portal_my_expenses', {'expenses': expenses})

    @http.route(['/expense/submit'], type='http', auth='user', website=True, methods=['POST'])
    def portal_submit(self, **post):
        user = request.env.user
        employee = request.env['hr.employee'].search([('user_id','=',user.id)], limit=1)
        if not employee:
            return request.redirect('/my/expenses')
        vals = {
            'employee_id': employee.id,
            'company_id': employee.company_id.id,
            'amount': post.get('amount') or 0.0,
            'category': post.get('category') or 'other',
            'description': post.get('description'),
        }
        request.env['expense.claim'].sudo().create(vals)
        return request.redirect('/my/expenses')
    
    