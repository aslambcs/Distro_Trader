# import json
# import logging
# import requests

# from odoo import fields, models, api
# from odoo.exceptions import UserError
# from requests.exceptions import RequestException
# import qrcode
# import base64
# import io

# _logger = logging.getLogger(__name__)


# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     fbr_production_status = fields.Selection(
#         [('not_sent', 'Not Sent'), ('sent', 'Successfully Sent'), ('failed', 'Failed to Send')],
#         string="FBR Post Status(Production)", default='not_sent', copy=False, tracking=True
#     )
#     fbr_sandbox_validation_status = fields.Selection(
#         [('not_validated', 'Not Validated'), ('valid', 'Valid'), ('invalid', 'Invalid')],
#         string="FBR Validation Status(Sandbox)", default='not_validated', copy=False, tracking=True
#     )

#     fbr_sandbox_post_status = fields.Selection(
#         [('not_posted', 'Not Posted'), ('posted', 'Posted'), ('failed', 'Failed to Send')],
#         string="FBR Post Status(Sandbox)", default='not_posted', copy=False, tracking=True
#     )
#     fbr_invoice_number = fields.Char(string="FBR Invoice Number", copy=False)
#     fbr_response = fields.Text(string="Last FBR Response", copy=False, readonly=True)
#     fbr_scenario_id = fields.Many2one('fbr.scenario', string="FBR Scenario")
#     fbr_posted_invoice_number_id = fields.Many2one('account.move', string="FBR Posted Invoice Number", copy=False)

#     @api.onchange('fbr_posted_invoice_number_id')
#     def _onchange_fbr_posted_invoice_number_id(self):
#         """
#         This method is triggered when the fbr_posted_invoice_number_id field is changed.
#         It updates the fbr_invoice_number field with the value from the selected invoice.
#         """
#         if self.fbr_posted_invoice_number_id:
#             self.fbr_invoice_number = self.fbr_posted_invoice_number_id.fbr_invoice_number
#         else:
#             self.fbr_invoice_number = False

#     # 2. The Binary field to store the generated QR code image
#     qr_code_image = fields.Binary(
#         string="QR Code", 
#         compute='_compute_qr_code',
#         store=True, # Storing the field is good for performance
#     )

#     @api.depends('fbr_invoice_number')
#     def _compute_qr_code(self):
#         """
#         This method generates a QR code from the fbr_invoice_number
#         and stores it in the qr_code_image field as a base64 encoded string.
#         """
#         for move in self:
#             # Only generate a QR code if there is an invoice number
#             if move.fbr_invoice_number:
#                 # Generate the QR code
#                 qr = qrcode.QRCode(
#                     version=1,
#                     error_correction=qrcode.constants.ERROR_CORRECT_L,
#                     box_size=10,
#                     border=4,
#                 )
#                 qr.add_data(move.fbr_invoice_number)
#                 qr.make(fit=True)

#                 # Create an image from the QR Code instance
#                 img = qr.make_image(fill_color="black", back_color="white")

#                 # Save the image to a memory buffer
#                 stream = io.BytesIO()
#                 img.save(stream, format="PNG")
                
#                 # Convert the buffer to a base64 string and assign it to the field
#                 move.qr_code_image = base64.b64encode(stream.getvalue())
#             else:
#                 # If there's no invoice number, clear the image field
#                 move.qr_code_image = False

#     def action_validate_invoice_fbr_sandbox(self):
#         return self._send_to_fbr(
#             endpoint_type='validate',
#             url_param='fbr.api.fbr_validate_invoice_sandbox_url',
#             token_param='fbr.api.fbr_api_token_sandbox'
#         )

#     def action_post_invoice_to_fbr_sandbox(self):
#         return self._send_to_fbr(
#             endpoint_type='post',
#             url_param='fbr.api.fbr_post_invoice_sandbox_url',
#             token_param='fbr.api.fbr_api_token_sandbox'
#         )

#     def action_post_invoice_to_fbr_production(self):
#         return self._send_to_fbr(
#             endpoint_type='post',
#             url_param='fbr.api.fbr_post_invoice_production_url',
#             token_param='fbr.api.fbr_api_token_production'
#         )

#     def _send_to_fbr(self, endpoint_type, url_param, token_param):
#         for invoice in self:
#             try:
#                 if invoice.move_type != 'out_invoice':
#                     raise UserError("Only customer invoices can be sent to FBR.")

#                 payload = invoice._prepare_fbr_payload()
#                 endpoint_url = self.env['ir.config_parameter'].sudo().get_param(url_param)
#                 token = self.env['ir.config_parameter'].sudo().get_param(token_param)

#                 headers = {
#                     'Content-Type': 'application/json',
#                     'Authorization': f'Bearer {token}',
#                 }

#                 response = requests.post(endpoint_url, headers=headers, json=payload, timeout=10)
#                 response.raise_for_status()

#                 json_response = response.json()
#                 invoice._handle_fbr_response(json_response, endpoint_type=endpoint_type)

#             except (RequestException, ValueError) as e:
#                 invoice._handle_fbr_error(str(e), endpoint_type=endpoint_type)

#     def _prepare_fbr_payload(self):
#         self.ensure_one()

#         invoice_type = {
#             'out_invoice': 'Sale Invoice',
#             'out_refund': 'Debit Note'
#         }.get(self.move_type, 'Sale Invoice')

#         company = self.company_id
#         customer = self.partner_id
#         journal_type = self.journal_id.type or 'other'

#         # payment_mode = {
#         #     'cash': 'Cash',
#         #     'bank': 'Bank'
#         # }.get(journal_type, 'Credit')

#         payload = {
#             "invoiceType": invoice_type,
#             "invoiceDate": self.invoice_date.strftime('%Y-%m-%d'),
#             "invoiceRefNo": self.name,
#             "sellerBusinessName": company.name,
#             "sellerProvince": company.state_id.name or "",
#             "sellerAddress": company.city or "",
#             "sellerNTNCNIC": company.vat or "",
#             "buyerNTNCNIC": customer.vat or customer.ref or "",
#             "buyerBusinessName": customer.name,
#             "buyerProvince": customer.state_id.name or "",
#             "buyerAddress": customer.city or "",
#             "buyerRegistrationType": customer.fbr_registration_type or "Unregistered",
#             # "paymentMode": payment_mode,
#             "scenarioId": self.fbr_scenario_id.code or "SN001",
#             # "totalInvoiceAmount": self.amount_total,
#             "totalSalesTax": sum(
#                     sum(
#                         ((line.price_subtotal * tax.amount) / 100.0)
#                         for tax in line.tax_ids
#                         if "further" not in tax.name.lower() and "extra" not in tax.name.lower()
#                     )
#                     for line in self.invoice_line_ids
#                 ),
#             "items": []
#         }

#         for idx, line in enumerate(self.invoice_line_ids, start=1):
#             tax_rate_label = ""
#             further_tax_amount = 0.0

#             for tax in line.tax_ids:
#                 tax_name = tax.name.lower()
#                 if "further" in tax_name:
#                     further_tax_amount += (line.price_subtotal * tax.amount) / 100
#                 elif "extra" not in tax_name and not tax_rate_label:
#                     tax_rate_label = tax.name

#             if not tax_rate_label:
#                 tax_rate_label = line.rate_fbr or "18%"

#             discount_value = round((line.price_unit * line.quantity) * (line.discount / 100.0), 2)

#             item = {
#                 "itemSNo": idx,
#                 "hsCode": line.product_id.fbr_hs_code or "",
#                 "productDescription": line.name,
#                 "unitPrice": line.price_unit,
#                 "rate": tax_rate_label,
#                 "uoM": line.fbr_uom or line.product_uom_id.name,
#                 "quantity": line.quantity,
#                 "totalValues": line.price_total,
#                 "valueSalesExcludingST": line.price_subtotal,
#                 "fixedNotifiedValueOrRetailPrice": line.fix_notified_val_retail_price or 0.00,
#                 "salesTaxApplicable": round(sum(
#                 ((line.price_subtotal * tax.amount) / 100.0)
#                 for tax in line.tax_ids
#                 if "further" not in tax.name.lower() and "extra" not in tax.name.lower()
#                         ), 2),
#                 "salesTaxWithheldAtSource": 0.00,
#                 "extraTax": 0.00,
#                 "furtherTax": round(further_tax_amount, 2),
#                 "sroScheduleNo": line.sro_schedule_no or "",
#                 "fedPayable": 0.00,
#                 "discount": discount_value if discount_value else 0.00,
#                 "saleType": line.sale_type or "Goods at standard rate (default)",
#                 "sroItemSerialNo": line.sro_item_serial_no or str(idx)
#             }

#             payload["items"].append(item)

#         return payload

#     def _handle_fbr_response(self, data, endpoint_type):
#         response_str = json.dumps(data, indent=2)
#         validation_resp = data.get('validationResponse', {})
#         status = validation_resp.get('status', '').lower()
#         error = validation_resp.get('error', '')

#         if not error and validation_resp.get('invoiceStatuses'):
#             errors = [f"Item {item.get('itemSNo')}: {item.get('error')}"
#                       for item in validation_resp.get('invoiceStatuses') if item.get('error')]
#             if errors:
#                 error = "; ".join(errors)

#         message_body = f"<b>FBR {endpoint_type.title()} Response:</b><br/>Status: {status.title()}<br/>"
#         if error:
#             message_body += f"Details: {error}"

#         if endpoint_type == 'validate':
#             is_valid = (status == 'valid')
#             self.write({
#                 'fbr_sandbox_validation_status': 'valid' if is_valid else 'invalid',
#                 'fbr_response': response_str,
#             })
#         elif endpoint_type == 'post':
#             fbr_inv_num = data.get('invoiceNumber')
#             is_success = (status == 'valid' and fbr_inv_num)
#             self.write({
#                 'fbr_production_status': 'sent' if is_success else 'failed',
#                 'fbr_invoice_number': fbr_inv_num if is_success else False,
#                 'fbr_response': response_str,
#             })
#             if is_success:
#                 message_body = f"<b>Successfully posted to FBR.</b><br/>FBR Invoice Number: {fbr_inv_num}"

#         self.message_post(body=message_body)

#     def _handle_fbr_error(self, error_msg, endpoint_type):
#         _logger.error("FBR %s error for invoice %s: %s", endpoint_type, self.name, error_msg)
#         if endpoint_type == 'validate':
#             self.write({'fbr_sandbox_validation_status': 'invalid', 'fbr_response': error_msg})
#         else:
#             self.write({'fbr_production_status': 'failed', 'fbr_response': error_msg})
#         self.message_post(body=f"<b>FBR {endpoint_type.title()} Failed:</b> {error_msg}")