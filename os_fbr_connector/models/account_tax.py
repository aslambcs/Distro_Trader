from odoo import models, fields

class AccountTax(models.Model):
    _inherit = "account.tax"

    fbr_tax_label_id = fields.Many2one(
        "fbr.tax.label", 
        string="FBR Tax Label"
    )
    fbr_tax_type_id = fields.Many2one(
        "fbr.tax.type", 
        string="FBR Tax Type"
    )