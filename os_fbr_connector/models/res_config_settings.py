from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Add a company switcher to the settings
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # Use 'related' fields to link to the company settings
    fbr_api_mode = fields.Selection(
        related='company_id.fbr_api_mode',
        readonly=False
    )
    fbr_api_token_sandbox = fields.Char(
        related='company_id.fbr_api_token_sandbox',
        readonly=False
    )
    fbr_post_invoice_sandbox_url = fields.Char(
        related='company_id.fbr_post_invoice_sandbox_url',
        readonly=False
    )
    fbr_validate_invoice_sandbox_url = fields.Char(
        related='company_id.fbr_validate_invoice_sandbox_url',
        readonly=False
    )
    fbr_api_token_production = fields.Char(
        related='company_id.fbr_api_token_production',
        readonly=False
    )
    fbr_post_invoice_production_url = fields.Char(
        related='company_id.fbr_post_invoice_production_url',
        readonly=False
    )