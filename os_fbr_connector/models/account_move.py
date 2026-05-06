import json
import logging
import requests

from odoo import fields, models, api
from odoo.exceptions import UserError
from requests.exceptions import RequestException
import qrcode
import base64
import io

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'


    def unlink(self):
        for move in self:
            if move.fbr_production_status == 'sent':
                raise UserError("You cannot delete an invoice that has been successfully posted to FBR.")
        return super(AccountMove, self).unlink()

    def button_draft(self):
        for move in self:
            if move.fbr_production_status == 'sent':
                raise UserError("You cannot reset to draft an invoice that has been successfully posted to FBR.")
        return super(AccountMove, self).button_draft()

    def button_cancel(self):
        for move in self:
            if move.fbr_production_status == 'sent':
                raise UserError("You cannot cancel an invoice that has been successfully posted to FBR.")
        return super(AccountMove, self).button_cancel()

    def action_register_payment(self):
        for move in self:
            if move.fbr_production_status == 'sent':
                raise UserError("You cannot register payment for an invoice that has been successfully posted to FBR.")
        return super(AccountMove, self).action_register_payment()

    def action_download_fbr_invoice(self):
        """Download FBR standard invoice PDF"""
        self.ensure_one()
        
        if not self.fbr_invoice_number:
            raise UserError("FBR Invoice Number is not available for this invoice.")
        
        # fbr_config = self._get_fbr_config()
        current_company = self.env.company
        fbr_token = current_company.fbr_api_token_production
        
        
        # FBR PDF download API endpoint (document ke according)
        pdf_url = f"https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata/{self.fbr_invoice_number}"
        
        headers = {
            "Authorization": f'Bearer {fbr_token}',
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(pdf_url, headers=headers, timeout=30)
            
            # Check for PDF content type
            content_type = response.headers.get('content-type', '')
            
            if response.status_code == 200 and ('application/pdf' in content_type or 'octet-stream' in content_type):
                # Create PDF attachment and return download
                pdf_data = response.content
                
                # Save to temporary attachment
                attachment = self.env['ir.attachment'].create({
                    'name': f"FBR_Invoice_{self.fbr_invoice_number}.pdf",
                    'datas': base64.b64encode(pdf_data),
                    'res_model': 'account.move',
                    'res_id': self.id,
                    'type': 'binary',
                })
                
                # Return download URL
                download_url = f'/web/content/{attachment.id}?download=true'
                return {
                    'type': 'ir.actions.act_url',
                    'url': download_url,
                    'target': 'new',
                }
            else:
                # Log detailed error information
                _logger.error("FBR PDF Download Failed - Status: %s, Content-Type: %s, Response: %s", 
                            response.status_code, content_type, response.text[:200])
                
                if response.status_code == 404:
                    raise UserError("FBR invoice PDF not found. The invoice may not be available for download yet.")
                elif response.status_code == 401:
                    raise UserError("Authentication failed. Please check your FBR token.")
                else:
                    raise UserError(f"Failed to download FBR invoice. Status: {response.status_code}, Response: {response.text[:100]}")
                    
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error downloading FBR invoice: {str(e)}")
    
    

    # -------------------------------------------------------------------------
    # FIELDS DEFINITION
    # -------------------------------------------------------------------------

    fbr_production_status = fields.Selection(
        [('not_sent', 'Not Sent'), ('sent', 'Successfully Sent'), ('failed', 'Failed to Send')],
        string="FBR Post Status (Production)", default='not_sent', copy=False, tracking=True
    )
    fbr_sandbox_validation_status = fields.Selection(
        [('not_validated', 'Not Validated'), ('valid', 'Valid'), ('invalid', 'Invalid')],
        string="FBR Validation Status (Sandbox)", default='not_validated', copy=False, tracking=True
    )
    fbr_sandbox_post_status = fields.Selection(
        [('not_posted', 'Not Posted'), ('posted', 'Posted'), ('failed', 'Failed to Send')],
        string="FBR Post Status (Sandbox)", default='not_posted', copy=False, tracking=True
    )
    fbr_invoice_number = fields.Char(string="FBR Invoice Number", copy=False)
    fbr_response = fields.Text(string="Last FBR Response", copy=False, readonly=True)
    fbr_scenario_id = fields.Many2one('fbr.scenario', string="FBR Scenario")
    fbr_posted_invoice_number_id = fields.Many2one('account.move', string="FBR Posted Invoice Number", copy=False)
    qr_code_image = fields.Binary(
        string="QR Code",
        compute='_compute_qr_code',
        store=True,
    )

    fbr_reason_id = fields.Many2one(
        'fbr.reason', string="FBR Reason")
    


    # -------------------------------------------------------------------------
    # COMPUTE AND ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('fbr_posted_invoice_number_id')
    def _onchange_fbr_posted_invoice_number_id(self):
        if self.fbr_posted_invoice_number_id:
            self.fbr_invoice_number = self.fbr_posted_invoice_number_id.fbr_invoice_number
        else:
            self.fbr_invoice_number = False

    @api.depends('fbr_invoice_number')
    def _compute_qr_code(self):
        for move in self:
            if move.fbr_invoice_number:
                qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
                qr.add_data(move.fbr_invoice_number)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                stream = io.BytesIO()
                img.save(stream, format="PNG")
                move.qr_code_image = base64.b64encode(stream.getvalue())
            else:
                move.qr_code_image = False

    # -------------------------------------------------------------------------
    # ACTION BUTTONS (USER-FACING ACTIONS)
    # -------------------------------------------------------------------------

    def action_validate_invoice_fbr_sandbox(self):
        current_company = self.env.company
        already_done = self.filtered(lambda m: m.fbr_sandbox_validation_status == 'valid')
        to_process = self - already_done
        if already_done and not to_process:
            raise UserError(
                "All selected invoices are already validated with FBR Sandbox.\n"
                "Invoices: %s" % ', '.join(already_done.mapped('name'))
            )
        if already_done:
            _logger.warning("FBR Sandbox Validate: Skipping already-validated: %s", ', '.join(already_done.mapped('name')))
        # Reset invalid so they can be retried
        failed = to_process.filtered(lambda m: m.fbr_sandbox_validation_status == 'invalid')
        if failed:
            failed.write({'fbr_sandbox_validation_status': 'not_validated'})
        return to_process._send_to_fbr(
            endpoint_type='validate_sandbox',
            url_param=current_company.fbr_validate_invoice_sandbox_url,
            token_param=current_company.fbr_api_token_sandbox,
        )

    def action_post_invoice_to_fbr_sandbox(self):
        current_company = self.env.company
        already_done = self.filtered(lambda m: m.fbr_sandbox_post_status == 'posted')
        to_process = self - already_done
        if already_done and not to_process:
            raise UserError(
                "All selected invoices are already posted to FBR Sandbox.\n"
                "Invoices: %s" % ', '.join(already_done.mapped('name'))
            )
        if already_done:
            _logger.warning("FBR Sandbox Post: Skipping already-posted: %s", ', '.join(already_done.mapped('name')))
        # Reset failed so they can be retried
        failed = to_process.filtered(lambda m: m.fbr_sandbox_post_status == 'failed')
        if failed:
            failed.write({'fbr_sandbox_post_status': 'not_posted'})
        return to_process._send_to_fbr(
            endpoint_type='post_sandbox',
            url_param=current_company.fbr_post_invoice_sandbox_url,
            token_param=current_company.fbr_api_token_sandbox,
        )

    def action_post_invoice_to_fbr_production(self):
        current_company = self.env.company
        # HARD BLOCK — prevents duplicate FBR entries
        already_sent = self.filtered(lambda m: m.fbr_production_status == 'sent')
        to_process = self - already_sent
        if already_sent and not to_process:
            raise UserError(
                "All selected invoices are already posted to FBR Production.\n"
                "Re-submitting will create DUPLICATE entries on FBR portal.\n\n"
                "Already submitted:\n%s"
                % '\n'.join("• %s  (FBR No: %s)" % (m.name, m.fbr_invoice_number or 'N/A') for m in already_sent)
            )
        if already_sent:
            raise UserError(
                "%d invoice(s) already sent to FBR — blocked to prevent duplicates:\n%s\n\n"
                "Please deselect them and resubmit only the remaining %d invoice(s)."
                % (
                    len(already_sent),
                    '\n'.join("• %s  (FBR No: %s)" % (m.name, m.fbr_invoice_number or 'N/A') for m in already_sent),
                    len(to_process),
                )
            )
        # Reset 'failed' invoices to 'not_sent' so they can be retried
        failed = to_process.filtered(lambda m: m.fbr_production_status == 'failed')
        if failed:
            failed.write({'fbr_production_status': 'not_sent'})
        return to_process._send_to_fbr(
            endpoint_type='post_production',
            url_param=current_company.fbr_post_invoice_production_url,
            token_param=current_company.fbr_api_token_production,
        )

    # -------------------------------------------------------------------------
    # CORE LOGIC & HELPER METHODS
    # -------------------------------------------------------------------------

    def _send_to_fbr(self, endpoint_type, url_param, token_param):
        """Generic method to prepare and send a request to an FBR endpoint."""
        for invoice in self:
            try:
                # Lock the record in the database for this specific transaction.
                # If Nginx secretly retries the request, the second thread will wait here 
                # until this thread calls invoice.env.cr.commit() below.
                invoice.env.cr.execute(
                    "SELECT fbr_production_status, fbr_sandbox_post_status, fbr_sandbox_validation_status "
                    "FROM account_move WHERE id = %s FOR UPDATE", [invoice.id]
                )
                db_row = invoice.env.cr.fetchone()
                
                if db_row:
                    # Skip if ANY non-default status — blocks Nginx retries completely
                    # 'failed' = pre-marked (in flight), 'sent'/'posted'/'valid' = done
                    if endpoint_type == 'post_production' and db_row[0] != 'not_sent':
                        _logger.info("Skipping %s — production status: %s", invoice.name, db_row[0])
                        continue
                    if endpoint_type == 'post_sandbox' and db_row[1] != 'not_posted':
                        _logger.info("Skipping %s — sandbox post status: %s", invoice.name, db_row[1])
                        continue
                    if endpoint_type == 'validate_sandbox' and db_row[2] != 'not_validated':
                        _logger.info("Skipping %s — sandbox validation: %s", invoice.name, db_row[2])
                        continue

                if invoice.move_type not in ['out_invoice', 'out_refund']:
                    raise UserError("Only customer invoices and credit notes can be sent to FBR.")

                payload = invoice._prepare_fbr_payload()

                # ── Cross-invoice duplicate check ────────────────────────────
                if endpoint_type in ('post_sandbox', 'post_production'):
                    status_field = 'fbr_sandbox_post_status' if endpoint_type == 'post_sandbox' else 'fbr_production_status'
                    status_value = 'posted' if endpoint_type == 'post_sandbox' else 'sent'
                    duplicate = invoice.env['account.move'].search([
                        ('id', '!=', invoice.id),
                        ('partner_id', '=', invoice.partner_id.id),
                        ('invoice_date', '=', invoice.invoice_date),
                        ('amount_total', '=', invoice.amount_total),
                        ('move_type', '=', invoice.move_type),
                        (status_field, '=', status_value),
                    ], limit=1)
                    if duplicate:
                        raise UserError(
                            "Duplicate Invoice Blocked!\n\n"
                            "Invoice: %s\n"
                            "Customer: %s\n"
                            "Date: %s\n"
                            "Amount: %.2f\n\n"
                            "A matching invoice (%s) was already posted to FBR.\n"
                            "Please verify before resubmitting."
                            % (invoice.name, invoice.partner_id.name,
                               invoice.invoice_date, invoice.amount_total,
                               duplicate.name)
                        )

                current_company = invoice.env.company
                
                token = token_param
                if endpoint_type == 'post_production':
                    fbrurl = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata"
                elif endpoint_type == 'validate_sandbox':
                    fbrurl = "https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb"
                elif endpoint_type == 'post_sandbox':
                    fbrurl = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb"
                else:
                    raise UserError(f"Unknown FBR endpoint type: {endpoint_type}")

                if not token or not token.strip():
                    raise UserError(
                        "FBR API Token is not configured.\n"
                        "Please go to Accounting → Settings → FBR and enter your API Token."
                    )

                # ── Pre-mark BEFORE HTTP call ──────────────────────────────
                # Committed immediately — Nginx retries will see 'failed' and skip
                pre_vals = {}
                if endpoint_type == 'post_production':
                    pre_vals['fbr_production_status'] = 'failed'
                elif endpoint_type == 'post_sandbox':
                    pre_vals['fbr_sandbox_post_status'] = 'failed'
                elif endpoint_type == 'validate_sandbox':
                    pre_vals['fbr_sandbox_validation_status'] = 'invalid'
                if pre_vals:
                    invoice.write(pre_vals)
                    invoice.env.cr.commit()

                headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token.strip()}'}
                response = requests.post(fbrurl, headers=headers, json=payload, timeout=120)
                response.raise_for_status()
                json_response = response.json()
                invoice._handle_fbr_response(json_response, endpoint_type)
                
                # Commit after processing each invoice.
                # This releases the FOR UPDATE lock, allowing any waiting concurrent thread
                # to proceed, read the newly committed 'sent' status, and skip the invoice!
                invoice.env.cr.commit()

            except UserError as e:
                # UserError (e.g. config missing, wrong type) — log and continue to next invoice
                invoice._handle_fbr_error(str(e), endpoint_type)
                try:
                    invoice.env.cr.commit()
                except Exception:
                    pass
            except (RequestException, ValueError) as e:
                # Network/JSON errors — log and continue to next invoice
                invoice._handle_fbr_error(str(e), endpoint_type)
                try:
                    invoice.env.cr.commit()
                except Exception:
                    pass


    def _format_extra_tax_value(self, value, sale_type):
        """Return '' for certain sale types, otherwise numeric (or 0.00)."""
        empty_sale_types = (
            'Services (FED in ST Mode)',
            'Services',
            '3rd Schedule Goods',
            'Goods at Reduced Rate',
            'Goods at zero-rate',
            'Exempt goods',
            'Processing/Conversion of Goods',
            'Goods as per SRO.297(|)/2023',
        )
        if sale_type in empty_sale_types:
            return 0.00
        return round(value, 2) if value else 0.00
    def _prepare_fbr_payload(self):
        self.ensure_one()

        # --- NEW LOGIC for invoiceRefNo ---
        invoice_ref_no_value = ""
        if self.move_type == 'out_refund':
            # For a credit note, we MUST reference the original FBR invoice number.
            # First, check if the original invoice has been linked.
            # if not self.fbr_posted_invoice_number_id:
            #     raise UserError("To send a credit note to FBR, you must first select the original 'FBR Posted Invoice Number' in the 'FBR Info' tab.")
            
            # Now get the FBR number from that linked invoice.
            # Your onchange method already copies this to the local fbr_invoice_number field.
            if not self.fbr_invoice_number:
                 raise UserError("The selected original invoice does not have an FBR Invoice Number. Cannot post this credit note to FBR.")
            invoice_ref_no_value = self.fbr_invoice_number
        else:
            # For a standard sales invoice, use its own reference/name.
            invoice_ref_no_value = ""
        # --- END NEW LOGIC ---

        invoice_type = {
            'out_invoice': 'Sale Invoice',
            'out_refund': 'Debit Note'
        }.get(self.move_type, 'Sale Invoice')

        company = self.company_id
        customer = self.partner_id
        # journal_type = self.journal_id.type or 'other'

        # payment_mode = {
        #     'cash': 'Cash',
        #     'bank': 'Bank'
        # }.get(journal_type, 'Credit')

        if invoice_type == 'Debit Note':
            payload = {
            "invoiceType": invoice_type,
            "invoiceDate": self.invoice_date.strftime('%Y-%m-%d'),
            "invoiceRefNo": invoice_ref_no_value,
            "reason": self.fbr_reason_id.name if self.fbr_reason_id else "Others",
            "sellerBusinessName": company.name,
            "sellerProvince": company.state_id.name or "",
            "sellerAddress": company.city or "",
            "sellerNTNCNIC": company.vat or "",
            "buyerNTNCNIC": customer.vat or customer.partner_cnic_no or "",
            "buyerBusinessName": customer.name,
            "buyerProvince": customer.state_id.name or "",
            "buyerAddress": customer.city or "",
            "buyerRegistrationType": customer.fbr_registration_type or "Unregistered",
            # "paymentMode": payment_mode,
            "scenarioId": self.fbr_scenario_id.code or "SN001",
            # "totalInvoiceAmount": (self.amount_total + self.total_discount) if self.total_discount else self.amount_total,
            "totalSalesTax": sum(
            (line.price_subtotal * tax.amount) / 100.0
            for line in self.invoice_line_ids
            for tax in line.tax_ids
            if tax.fbr_tax_type_id and tax.fbr_tax_type_id.name == "salesTaxApplicable"
            ),
            "items": []
                }

            # for idx, line in enumerate(self.invoice_line_ids, start=1):
            # for idx, line in enumerate(self.invoice_line_ids, start=1):
            for idx, line in enumerate(self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'), start=1):

                fbr_tax_label = None
                sales_tax_applicable = 0.0
                sales_tax_withheld = 0.0
                extra_tax = 0.0
                further_tax = 0.0

                # Process each tax separately
                for tax in line.tax_ids:
                    tax_type = tax.fbr_tax_type_id.name if tax.fbr_tax_type_id else ""
                    tax_label = tax.fbr_tax_label_id.name if tax.fbr_tax_label_id else ""
                    tax_amount = (line.price_subtotal * tax.amount) / 100.0

                    if tax_type == "salesTaxApplicable":
                        sales_tax_applicable = round(tax_amount, 2)
                        fbr_tax_label = tax_label
                    elif tax_type == "salesTaxWithheldAtSource":
                        sales_tax_withheld = round(tax_amount, 2)
                    elif tax_type == "extraTax":
                        extra_tax = round(tax_amount, 2)
                    elif tax_type == "furtherTax":
                        further_tax = round(tax_amount, 2)

                if not fbr_tax_label:
                    # fallback if no applicable tax found
                    fbr_tax_label = "18%"

                # discount_value = round((line.price_unit * line.quantity) * (line.discount / 100.0), 2)
                # discount_value = round((line.price_unit * line.quantity) * (line.discount / 100.0), 2)
                discount_value = round(line.discount_fixed, 2)

                item = {
                    "itemSNo": idx,
                    "hsCode": line.fbr_hs_code or "",
                    "productDescription": line.name,
                    "unitPrice": line.price_unit,
                    "rate": fbr_tax_label,
                    "uoM": line.fbr_uom_id.name or line.product_id.fbr_uom_id.name,
                    "quantity": line.quantity,
                    "totalValues": line.price_subtotal + sales_tax_applicable,
                    "valueSalesExcludingST": line.price_subtotal,
                    "fixedNotifiedValueOrRetailPrice": line.fix_notified_val_retail_price or 0.00,
                    "salesTaxApplicable": sales_tax_applicable or 0.00,
                    "salesTaxWithheldAtSource": sales_tax_withheld or 0.00,
                    "extraTax": self._format_extra_tax_value(extra_tax, line.fbr_scenario_id.sal_pur_cotton_ginners),
                    "furtherTax": further_tax or 0.00,
                    "sroScheduleNo": line.fbr_sro_schedule_no_id.name or "",
                    "fedPayable": line.fed_payable or 0.00,
                    "discount": discount_value if discount_value else 0.00,
                    "saleType": line.fbr_scenario_id.sal_pur_cotton_ginners or "Goods at standard rate (default)",
                    "sroItemSerialNo": line.fbr_sro_item_serial_no_id.name or str(idx)
                }

                payload["items"].append(item)
        
        else:

            payload = {
                "invoiceType": invoice_type,
                "invoiceDate": self.invoice_date.strftime('%Y-%m-%d'),
                # "invoiceRefNo": invoice_ref_no_value,
                "sellerBusinessName": company.name,
                "sellerProvince": company.state_id.name or "",
                "sellerAddress": company.city or "",
                "sellerNTNCNIC": company.vat or "",
                "buyerNTNCNIC": customer.vat or customer.partner_cnic_no or "",
                "buyerBusinessName": customer.name,
                "buyerProvince": customer.state_id.name or "",
                "buyerAddress": customer.city or "",
                "buyerRegistrationType": customer.fbr_registration_type or "Unregistered",
                # "paymentMode": payment_mode,
                "scenarioId": self.fbr_scenario_id.code or "SN001",
                # "totalInvoiceAmount": (self.amount_total + self.total_discount) if self.total_discount else self.amount_total,
                # "totalSalesTax": sum(
                #     (line.price_subtotal * tax.amount) / 100.0
                #     for line in self.invoice_line_ids
                #     for tax in line.tax_ids
                #     if tax.fbr_tax_type_id and tax.fbr_tax_type_id.name == "salesTaxApplicable"
                #     ),
                "items": []
            }

            # for idx, line in enumerate(self.invoice_line_ids, start=1):
            # for idx, line in enumerate(self.invoice_line_ids, start=1):
            for idx, line in enumerate(self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'), start=1):

                fbr_tax_label = None
                sales_tax_applicable = 0.0
                sales_tax_withheld = 0.0
                extra_tax = 0.0
                further_tax = 0.0

                # Process each tax separately
                for tax in line.tax_ids:
                    tax_type = tax.fbr_tax_type_id.name if tax.fbr_tax_type_id else ""
                    tax_label = tax.fbr_tax_label_id.name if tax.fbr_tax_label_id else ""
                    tax_amount = (line.price_subtotal * tax.amount) / 100.0

                    if tax_type == "salesTaxApplicable":
                        sales_tax_applicable = round(tax_amount, 2)
                        fbr_tax_label = tax_label
                    elif tax_type == "salesTaxWithheldAtSource":
                        sales_tax_withheld = round(tax_amount, 2)
                    elif tax_type == "extraTax":
                        extra_tax = round(tax_amount, 2)
                    elif tax_type == "furtherTax":
                        further_tax = round(tax_amount, 2)

                if not fbr_tax_label:
                    # fallback if no applicable tax found
                    fbr_tax_label = "18%"

                # discount_value = round((line.price_unit * line.quantity) * (line.discount / 100.0), 2)
                discount_value = round(line.discount_fixed, 2)
                # item = {
                #     "itemSNo": idx,
                #     "hsCode": line.fbr_hs_code or "",
                #     "productDescription": line.product_id.name,
                #     "unitPrice": (line.price_unit - discount_value) if discount_value else line.price_unit,
                #     "rate": fbr_tax_label,
                #     "uoM": line.fbr_uom_id.name or line.product_id.fbr_uom_id.name,
                #     "quantity": line.quantity,
                #     "totalValues": line.price_subtotal + sales_tax_applicable,
                #     "valueSalesExcludingST": line.price_subtotal,
                #     "fixedNotifiedValueOrRetailPrice": line.fix_notified_val_retail_price or 0.00,
                #     "salesTaxApplicable": sales_tax_applicable or 0.00,
                #     "salesTaxWithheldAtSource": sales_tax_withheld or 0.00,
                #     "extraTax": self._format_extra_tax_value(extra_tax, line.fbr_scenario_id.sal_pur_cotton_ginners),
                #     "furtherTax": further_tax or 0.00,
                #     "sroScheduleNo": line.fbr_sro_schedule_no_id.name or "",
                #     "fedPayable": line.fed_payable or 0.00,
                #     "discount": 0.00,
                #     "saleType": line.fbr_scenario_id.sal_pur_cotton_ginners or "Goods at standard rate (default)",
                #     "sroItemSerialNo": line.fbr_sro_item_serial_no_id.name or str(idx)
                # }
                item = {
                    "itemSNo": idx,
                    "hsCode": line.fbr_hs_code or "",
                    "productDescription": line.product_id.name,
                    "unitPrice": round((line.price_unit - discount_value) if discount_value else line.price_unit, 2),
                    "rate": fbr_tax_label,
                    "uoM": line.fbr_uom_id.name or line.product_id.fbr_uom_id.name,
                    "quantity": round(line.quantity, 4),
                    "totalValues": round(line.price_subtotal + sales_tax_applicable, 2),
                    "valueSalesExcludingST": round(line.price_subtotal, 2),
                    "fixedNotifiedValueOrRetailPrice": round(line.fix_notified_val_retail_price or 0.00, 2),
                    "salesTaxApplicable": round(sales_tax_applicable or 0.00, 2),
                    "salesTaxWithheldAtSource": round(sales_tax_withheld or 0.00, 2),
                    "extraTax": self._format_extra_tax_value(extra_tax, line.fbr_scenario_id.sal_pur_cotton_ginners),
                    "furtherTax": round(further_tax or 0.00, 2),
                    "sroScheduleNo": line.fbr_sro_schedule_no_id.name or "",
                    "fedPayable": round(line.fed_payable or 0.00, 2),
                    "discount": 0.00,
                    "saleType": line.fbr_scenario_id.sal_pur_cotton_ginners or "Goods at standard rate (default)",
                    "sroItemSerialNo": line.fbr_sro_item_serial_no_id.name or str(idx)
                }

                payload["items"].append(item)

        return payload

    def _handle_fbr_response(self, data, endpoint_type):
        """
        UPDATED: Handles successful FBR responses and writes to the correct status fields.
        It now also captures the 'invoiceNumber' from the response in all cases, if present.
        """
        self.ensure_one()
        response_str = json.dumps(data, indent=2)
        validation_resp = data.get('validationResponse', {})
        status = validation_resp.get('status', '').lower()
        error = validation_resp.get('error', '')
        
        # NEW: Get the invoice number from the response, if it exists.
        fbr_inv_num = data.get('invoiceNumber')

        # Consolidate item-specific errors
        if not error and validation_resp.get('invoiceStatuses'):
            errors = [f"Item {item.get('itemSNo')}: {item.get('error')}"
                      for item in validation_resp.get('invoiceStatuses') if item.get('error')]
            if errors:
                error = "; ".join(errors)

        vals_to_write = {'fbr_response': response_str}
        is_success = (status == 'valid' and not error)
        friendly_name = ""

        # Add the FBR invoice number to the values to be written if it was returned.
        if fbr_inv_num:
            vals_to_write['fbr_invoice_number'] = fbr_inv_num

        if endpoint_type == 'validate_sandbox':
            vals_to_write['fbr_sandbox_validation_status'] = 'valid' if is_success else 'invalid'
            friendly_name = "FBR Sandbox Validation"
        
        elif endpoint_type == 'post_sandbox':
            vals_to_write['fbr_sandbox_post_status'] = 'posted' if is_success else 'failed'
            friendly_name = "FBR Sandbox Post"
        
        elif endpoint_type == 'post_production':
            # For production, success specifically requires an invoice number.
            is_prod_success = (is_success and fbr_inv_num)
            vals_to_write['fbr_production_status'] = 'sent' if is_prod_success else 'failed'
            # The fbr_invoice_number is already in vals_to_write if it exists
            friendly_name = "FBR Production Post"

        self.write(vals_to_write)

        # Prepare and post a clear message to the chatter
        message_body = f"<b>{friendly_name} Response:</b><br/>Status: {status.title()}"
        if error:
            message_body += f"<br/>Details: {error}"
        
        # If we received an invoice number, make sure it's in the message
        if fbr_inv_num:
            message_body += f"<br/>FBR Invoice Number: {fbr_inv_num}"

        self.message_post(body=message_body)

    def _handle_fbr_error(self, error_msg, endpoint_type):
        """
        UPDATED: Handles errors and writes a failure status to the correct field
        based on the specific endpoint_type.
        """
        self.ensure_one()
        _logger.error("FBR %s error for invoice %s: %s", endpoint_type, self.name, error_msg)
        
        vals_to_write = {'fbr_response': error_msg}
        friendly_name = "FBR Operation"

        if endpoint_type == 'validate_sandbox':
            vals_to_write['fbr_sandbox_validation_status'] = 'invalid'
            friendly_name = "FBR Sandbox Validation"
        elif endpoint_type == 'post_sandbox':
            vals_to_write['fbr_sandbox_post_status'] = 'failed'
            friendly_name = "FBR Sandbox Post"
        elif endpoint_type == 'post_production':
            vals_to_write['fbr_production_status'] = 'failed'
            friendly_name = "FBR Production Post"

        self.write(vals_to_write)
        self.message_post(body=f"<b>{friendly_name} Failed:</b> {error_msg}")