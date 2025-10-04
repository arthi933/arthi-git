# -*- coding: utf-8 -*-
import secrets
import string
from odoo import http, tools, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

class CustomeAutoSignupHome(AuthSignupHome):
    
    
    @http.route('/expense_management/custom_reset', type='http', auth='public', website=True, csrf=False)
    def custom_reset_password(self, **kwargs):
        qcontext = self.get_auth_signup_qcontext()
        # Example: send dynamic users to template
        users = request.env['res.users'].sudo().search([])
        qcontext['users'] = users
        if request.httprequest.method == 'POST':
            email = kwargs.get('email')
            user_id = kwargs.get('login_user')
            if not email or not user_id:
                qcontext['error'] = "Please select a user and provide an email."
            else:
                user = request.env['res.users'].sudo().browse(int(user_id))
                if not user or user.login != email:
                    qcontext['error'] = "User and email do not match!"
                else:
                    # Generate random password
                    alphabet = string.ascii_letters + string.digits
                    new_password = ''.join(secrets.choice(alphabet) for i in range(10))
                    print("new_password",new_password)
                    # Set new password for user
                    user.sudo().write({'password': new_password})

                    # Send email to user
                    mail_template = request.env['mail.mail'].sudo().create({
                        'subject': "Your New Password",
                        'body_html': f"""
                            <p>Hello {user.name},</p>
                            <p>Your new password is: <b>{new_password}</b></p>
                            <p>Please log in and change it after first use.</p>
                        """,
                        'email_to': email,
                        'email_from': request.env.user.email or "admin@example.com",
                    })
                    mail_template.send()
                    qcontext['message'] = f"A new password has been sent to {email}."
                    
                    return request.redirect('/web/login')
    
        return request.render('expense_management.custom_reset_template', qcontext)
    
    def get_auth_signup_qcontext(self):
        # get default qcontext
        qcontext = super().get_auth_signup_qcontext()

        # 🔹 Add countries list to qcontext
        qcontext['countries'] = request.env['res.country'].sudo().search([])

        # 🔹 Preserve selected country if coming from POST
        if request.params.get('signup_country_id'):
            qcontext['countries'] = int(request.params.get('signup_country_id'))
            user_country = request.env['res.country'].sudo().browse(qcontext['countries'])
            if user_country.currency_id:
                request.env.company.currency_id = user_country.currency_id.id

        return qcontext
    
    @http.route('/expense_management/send_password', type='http', auth='public', website=True, csrf=False)
    def send_password(self):
        self.get_auth_signup_qcontext()
        
