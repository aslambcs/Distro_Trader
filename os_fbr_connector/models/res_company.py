from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    fbr_api_mode = fields.Selection(
        [
            ('sandbox', 'Sandbox (Testing)'),
            ('production', 'Production (Live)'),
        ],
        string="FBR Environment",
        default='sandbox',
        help="Choose whether to connect to the FBR Sandbox or Production environment."
    )
    fbr_api_token_sandbox = fields.Char(
        string="FBR API Security Token (Sandbox)",
        help="Security token provided by PRAL/FBR. Valid for 5 years."
    )
    fbr_post_invoice_sandbox_url = fields.Char(
        string="Post Invoice URL (Sandbox)",
        default="https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata"
    )
    fbr_validate_invoice_sandbox_url = fields.Char(
        string="Validate Invoice URL (Sandbox)",
        default="https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb"
    )
    fbr_api_token_production = fields.Char(
        string="FBR API Security Token (Production)",
        help="Security token provided by PRAL/FBR. Valid for 5 years."
    )
    fbr_post_invoice_production_url = fields.Char(
        string="Post Invoice URL (Production)",
        default="https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata"
    )