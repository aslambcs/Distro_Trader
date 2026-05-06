from odoo import models, fields

class FBRSROScheduleNo(models.Model):
    _name = "fbr.sro.item.serial.no"
    _description = "FBR SRO Item Serial No"

    sequence = fields.Integer(string="Sequence", default=1, help="Sequence number for ordering")

    name = fields.Char(
        string='FBR SRO Item Serial No',
        required=True,
        help="FBR SRO Item Serial No"
        )
    