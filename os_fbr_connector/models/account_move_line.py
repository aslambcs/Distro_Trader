import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # FBR Fields
    fbr_hs_code = fields.Char(
        string='FBR HS Code',
        compute='_compute_fbr_fields',
        inverse='_inverse_fbr_fields',
        store=False
    )

    fbr_uom_id = fields.Many2one(
        'fbr.uom',
        string='FBR UOM',
        compute='_compute_fbr_fields',
        inverse='_inverse_fbr_fields',
        store=False
    )

    fbr_scenario_id = fields.Many2one(
        'fbr.scenario',
        string='FBR Sale Type',
        compute='_compute_fbr_fields',
        inverse='_inverse_fbr_fields',
        store=False
    )

    fbr_sro_item_serial_no_id = fields.Many2one(
        'fbr.sro.item.serial.no',
        string="FBR SRO Item SR No.",
        compute='_compute_fbr_fields',
        inverse='_inverse_fbr_fields',
        store=False
    )

    fbr_sro_schedule_no_id = fields.Many2one(
        'fbr.sro.schedule.no',
        string="FBR SRO Schedule No.",
        compute='_compute_fbr_fields',
        inverse='_inverse_fbr_fields',
        store=False
    )

    fix_notified_val_retail_price = fields.Float(
        string='Fixed Notified Value / Retail Price',
        compute='_compute_fbr_fields',
        inverse='_inverse_fbr_fields',
        store=False
    )

    # fed_payable = fields.Float(
    #     string='FBR Fed Payable',
    #     compute='_compute_fbr_fields',
    #     inverse='_inverse_fbr_fields',
    #     store=False
    # )

    fed_payable = fields.Float( string='FBR Fed Payable', 
                               help="This field is used to store the Federal Payable amount for the item. " "It is applicable for certain sale types as per FBR regulations." )

    # -----------------------------
    # Compute Method
    # -----------------------------
    @api.depends('product_id')
    def _compute_fbr_fields(self):
        """
        Auto-fill FBR fields from product defaults.
        Only populate if invoice line field is empty (preserve user edits).
        """
        for line in self:
            product = line.product_id
            line.fed_payable = 0.0  # Default value
            if product:
                if not line.fbr_hs_code:
                    line.fbr_hs_code = product.fbr_hs_code
                if not line.fbr_uom_id:
                    line.fbr_uom_id = product.fbr_uom_id
                if not line.fbr_scenario_id:
                    line.fbr_scenario_id = product.fbr_scenario_id
                if not line.fbr_sro_schedule_no_id:
                    line.fbr_sro_schedule_no_id = product.fbr_sro_schedule_no_id
                if not line.fbr_sro_item_serial_no_id:
                    line.fbr_sro_item_serial_no_id = product.fbr_sro_item_serial_no_id
                if not line.fix_notified_val_retail_price:
                    line.fix_notified_val_retail_price = product.fix_notified_val_retail_price
                
            else:
                # Clear fields if no product selected
                line.fbr_hs_code = False
                line.fbr_uom_id = False
                line.fbr_scenario_id = False
                line.fbr_sro_schedule_no_id = False
                line.fbr_sro_item_serial_no_id = False
                line.fix_notified_val_retail_price = 0.0
                line.fed_payable = 0.0

    # -----------------------------
    # Inverse Method
    # -----------------------------
    def _inverse_fbr_fields(self):
        """
        Allows the user to manually edit FBR fields.
        Inverse does nothing because we do not overwrite user input.
        """
        pass
