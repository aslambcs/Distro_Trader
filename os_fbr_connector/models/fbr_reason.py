from odoo import models, fields

class FBRSaleType(models.Model):
    _name = "fbr.reason"
    _description = "FBR Reason"

    sequence = fields.Integer(string="Sequence", default=1, help="Sequence number for ordering.")

    name = fields.Char(
        string='FBR Reason',
        required=True,
        help="FBR Reason"
        )
    


    # Cancellation of supply
    # Return of goods
    # Change in nature of supply
    # change in value of supply
    # Change in amount of tax
    # Others
    # Adjustment given to Steel Melters