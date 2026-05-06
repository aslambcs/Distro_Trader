from odoo import api, fields, models, _



# Consolidate the list to remove duplicates while preserving original case.
unique_units = [
    '1000 kWh', '40KG', 'Bag', 'Barrels', 'Bill of lading', 'Carat', 
    'Cubic Metre', 'Dozen', 'Foot', 'Gallon', 'Gram', 'KG', 'KWH', 
    'Kilogram', 'Liter', 'MMBTU', 'MT', 'Mega Watt', 'Meter', 'NO',
    'Numbers, pieces, units', 'Others', 'Packs', 'Pair', 'Pound', 'SET', 
    'SqY', 'Square Foot', 'Square Metre', 'Thousand Unit', 'Timber Logs'
]

# Generate the selection list where the key and value are the same.
# For example: ('Bill of lading', 'Bill of lading')
_UNIT_SELECTION = [(unit, unit) for unit in sorted(unique_units)]

# class ProductTemplate(models.Model):
#     _inherit = "product.template"


#     fbr_uom = fields.Selection(
#         selection=_UNIT_SELECTION,
#         string="FBR UoM",
#         help="Select the custom unit of measure for this product."
#     )

#     fbr_hs_code = fields.Char(
#         'FBR HS Code', compute='_compute_fbr_hs_code',
#         inverse='_set_fbr_hs_code', store=True)

#     @api.depends('product_variant_ids.fbr_hs_code')
#     def _compute_fbr_hs_code(self):
#         self._compute_template_field_from_variant_field('fbr_hs_code')

#     def _set_fbr_hs_code(self):
#         self._set_product_variant_field('fbr_hs_code')

#     @api.onchange('fbr_hs_code')
#     def _onchange_fbr_hs_code(self):
#         if not self.fbr_hs_code:
#             return

#         domain = [('fbr_hs_code', '=', self.fbr_hs_code)]
#         if self.id.origin:
#             domain.append(('id', '!=', self.id.origin))

#         if self.env['product.template'].search_count(domain, limit=1):
#             return {'warning': {
#                 'title': _("Note:"),
#                 'message': _("The FBR HS Code '%s' already exists.", self.fbr_hs_code),
#             }}

#     def _get_related_fields_variant_template(self):
#         """ Return a list of fields present on template and variants models and that are related"""
#         res = super()._get_related_fields_variant_template()
#         res.append('fbr_hs_code')
#         return res

class ProductProduct(models.Model):
    _inherit = "product.product"

    fbr_hs_code = fields.Char('FBR HS Code', index=True)


    fbr_uom_id = fields.Many2one(
        'fbr.uom',
        string='FBR UOM',
        help="Select the FBR unit of measure for this product.",
    )

    fbr_scenario_id = fields.Many2one(
        'fbr.scenario',
        string='FBR Sale Type',
        help="FBR Sale Type",
    )

    fbr_sro_item_serial_no_id = fields.Many2one(
        'fbr.sro.item.serial.no',
        string="FBR SRO Item SR No.",
        help="FBR SRO Item Serial No",  # <-- The required comma is added here
    )


    fbr_sro_schedule_no_id = fields.Many2one(
        'fbr.sro.schedule.no',
        string="FBR SRO Schedule No.",
        help="FBR SRO Schedule No",  # <-- The required comma is added here

    )


    fbr_hs_code = fields.Char(
        'FBR HS Code', 
        )


    fix_notified_val_retail_price = fields.Float(
        string='Default Fixed Notified Value or Retail Price',
    )




class ProductTemplate(models.Model):
    _inherit = "product.template"


    fbr_uom_id = fields.Many2one(
        'fbr.uom',
        string='FBR UOM',
        help="Select the FBR unit of measure for this product.",
        compute="_compute_fbr_fields_info",
        inverse="_inverse_fbr_fields_info",
        store=True,
    )

    fbr_scenario_id = fields.Many2one(
        'fbr.scenario',
        string='FBR Sale Type',
        help="FBR Sale Type",
        compute="_compute_fbr_fields_info",
        inverse="_inverse_fbr_fields_info",
        store=True,
    )

    fbr_sro_item_serial_no_id = fields.Many2one(
        'fbr.sro.item.serial.no',
        string="FBR SRO Item SR No.",
        help="FBR SRO Item Serial No",  # <-- The required comma is added here
        compute="_compute_fbr_fields_info",
        inverse="_inverse_fbr_fields_info",
        store=True,
    )


    fbr_sro_schedule_no_id = fields.Many2one(
        'fbr.sro.schedule.no',
        string="FBR SRO Schedule No.",
        help="FBR SRO Schedule No",  # <-- The required comma is added here
        compute="_compute_fbr_fields_info",
        inverse="_inverse_fbr_fields_info",
        store=True,
    )


    fbr_hs_code = fields.Char(
        'FBR HS Code', 
        compute="_compute_fbr_fields_info",
        inverse="_inverse_fbr_fields_info",
        store=True,
        )

    fix_notified_val_retail_price = fields.Float(
        string='Default Fixed Notified Value or Retail Price',
        compute="_compute_fbr_fields_info",
        inverse="_inverse_fbr_fields_info",
        store=True,
    )
    
    @api.depends(
        "product_variant_ids",
        "product_variant_ids.fbr_uom_id",
        "product_variant_ids.fbr_hs_code",
        "product_variant_ids.fbr_scenario_id",
        "product_variant_ids.fbr_sro_item_serial_no_id",
        "product_variant_ids.fbr_sro_schedule_no_id",
        "product_variant_ids.fix_notified_val_retail_price",
    )
    def _compute_fbr_fields_info(self):
        unique_variants = self.filtered(
            lambda template: len(template.product_variant_ids) == 1
        )
        for template in unique_variants:
            product_variant = template.product_variant_ids
            template.update(
                {
                    "fbr_uom_id": product_variant.fbr_uom_id.id,
                    "fbr_hs_code": product_variant.fbr_hs_code,
                    "fbr_scenario_id": product_variant.fbr_scenario_id.id,
                    "fbr_sro_item_serial_no_id": product_variant.fbr_sro_item_serial_no_id.id,
                    "fbr_sro_schedule_no_id": product_variant.fbr_sro_schedule_no_id.id,
                    "fix_notified_val_retail_price": product_variant.fix_notified_val_retail_price,
                }
            )
        (self - unique_variants).update(
            {
                "fbr_uom_id": False,
                "fbr_hs_code": False,
                "fbr_scenario_id": False,
                "fbr_sro_item_serial_no_id": False,
                "fbr_sro_schedule_no_id": False,
                "fix_notified_val_retail_price": False,
            }
        )

    def _inverse_fbr_fields_info(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.update(
                    {
                    "fbr_uom_id": template.fbr_uom_id.id,
                    "fbr_hs_code": template.fbr_hs_code,
                    "fbr_scenario_id": template.fbr_scenario_id.id,
                    "fbr_sro_item_serial_no_id": template.fbr_sro_item_serial_no_id.id,
                    "fbr_sro_schedule_no_id": template.fbr_sro_schedule_no_id.id,
                    "fix_notified_val_retail_price": template.fix_notified_val_retail_price,
                    }
                )

    def _get_related_fields_variant_template(self):
        """Adds fields related to manufacturer that are present on template and
        variants models"""
        res = super()._get_related_fields_variant_template()
        res.extend(
            [
                "fbr_uom_id",
                "fbr_hs_code",
                "fbr_scenario_id",
                "fbr_sro_item_serial_no_id",
                "fbr_sro_schedule_no_id",
                "fix_notified_val_retail_price",
            ]
        )
        return res
    

    @api.onchange('fbr_hs_code')
    def _onchange_fbr_hs_code(self):
        if not self.fbr_hs_code:
            return

        domain = [('fbr_hs_code', '=', self.fbr_hs_code)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))

        if self.env['product.template'].search_count(domain, limit=1):
            return {'warning': {
                'title': _("Note:"),
                'message': _("The FBR HS Code '%s' already exists.", self.fbr_hs_code),
            }}