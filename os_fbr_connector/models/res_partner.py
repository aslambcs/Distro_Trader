from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    fbr_registration_type = fields.Selection(
        [
            ('Registered', 'Registered'),
            ('Unregistered', 'Unregistered'),
        ],
        string="FBR Registration Type",
        default='Unregistered'
    )


    partner_cnic_no = fields.Char('CNIC Number')