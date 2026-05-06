from odoo import models, fields, api

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    # 1. Add the FBR reason field to the wizard model
    fbr_reason_id = fields.Many2one(
        'fbr.reason',
        string="FBR Reason",
        help="Select the official reason for this credit note as per FBR requirements."
    )

    # 2. Inherit the refund method to pass the value
    def _prepare_default_reversal(self, move):
        vals = super()._prepare_default_reversal(move)
        if self.fbr_reason_id:
            vals['fbr_reason_id'] = self.fbr_reason_id.id
        return vals