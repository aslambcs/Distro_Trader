from odoo import models, fields, api

class FBRScenario(models.Model):
    _name = "fbr.scenario"
    _rec_name = "sal_pur_cotton_ginners"
    _description = "FBR Scenario"
    _rec_names_search = ['sal_pur_cotton_ginners', 'code']

    

    sequence = fields.Integer(string="Sequence", default=1, help="Sequence number for ordering scenarios.")

    code = fields.Char(
        string='Scenario Code',
        size=5,
        required=True,
        help="Enter FBR Scenario Code (e.g., SN001). Max 5 characters."
    )

    name = fields.Char(
        string='Description',
        help="Description"
        )
    sal_pur_cotton_ginners = fields.Text(
        string="Sale Type (Purchase type in case of Cotton Ginners)",
        help="Sale Type (Purchase type in case of Cotton Ginners")
    

    @api.depends('code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f'[{record.code}] {record.sal_pur_cotton_ginners}'