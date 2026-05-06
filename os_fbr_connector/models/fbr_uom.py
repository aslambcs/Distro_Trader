from odoo import models, fields

class FBRUOM(models.Model):
    _name = "fbr.uom"
    _description = "FBR Sale Type"

    sequence = fields.Integer(string="Sequence", default=1, help="Sequence number for ordering.")

    name = fields.Char(
        string='FBR UOM',
        required=True,
        help="FBR UOM"
        )
    