from odoo import models, fields

class FbrTaxLabel(models.Model):
    _name = "fbr.tax.label"
    _description = "FBR Tax Label"

    name = fields.Char("Name", required=True)