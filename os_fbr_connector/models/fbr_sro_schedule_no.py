from odoo import models, fields

class FBRSROScheduleNo(models.Model):
    _name = "fbr.sro.schedule.no"
    _description = "FBR SRO Scheedule No"

    sequence = fields.Integer(string="Sequence", default=1, help="Sequence number for ordering")

    name = fields.Char(
        string='FBR SRO Scheedule No',
        required=True,
        help="FBR SRO Scheedule No"
        )
    