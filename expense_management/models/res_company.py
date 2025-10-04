# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    # On creation, an install-time hook could set currency based on signup country.
    default_country_code = fields.Char(string='Signup Country Code')

    @api.model_create_multi
    def create(self, vals_list):
        # keep default behaviour but placeholder for currency auto-set
        companies = super().create(vals_list)
        return companies