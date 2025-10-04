# -*- coding: utf-8 -*-
{
    'name': 'Expense Management',
    'version': '1.0',
    'author': 'Srikesh Infotech',
    'license': "OPL-1",
    'website': 'http://www.srikeshinfotech.com',
    'depends': ['base','contacts', 'web', 'hr','hr_expense','mail'],
    'data': ['views/expense_claim_view.xml',
             'security/ir.model.access.csv'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
