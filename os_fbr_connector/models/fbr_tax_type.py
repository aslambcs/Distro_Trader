from odoo import models, fields

class FbrTaxType(models.Model):
    _name = "fbr.tax.type"
    _description = "FBR Tax Type"

    name = fields.Char("Name", required=True)