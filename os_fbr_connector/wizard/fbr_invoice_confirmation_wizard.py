from odoo import api, fields, models

class FbrInvoiceResultWizard(models.TransientModel):
    _name = 'fbr.invoice.result.wizard'
    _description = 'FBR Invoice Result Summary'

    message = fields.Text(string="Result Summary", readonly=True)
    fbr_numbers = fields.Text(string="Generated FBR Invoice Numbers", readonly=True)

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
