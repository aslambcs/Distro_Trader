import json
import requests
import logging
from odoo import models, _
from odoo.exceptions import UserError
# import requests
from dateutil.relativedelta import relativedelta
from requests.exceptions import RequestException, Timeout

_logger = logging.getLogger(__name__)

class FbrService(models.AbstractModel):
    _name = 'fbr.service'
    _description = 'FBR API Communication Service'

    def _get_fbr_config(self, environment):
        """
        Centralized method to retrieve FBR configuration for a specific environment.
        :param environment: 'sandbox' or 'production'
        """
        config = self.env['ir.config_parameter'].sudo()
        token = config.get_param(f'fbr.api.token_{environment}')
        url = config.get_param(f'fbr.api.post_url_{environment}')

        if not token or not url:
            raise UserError(_(
                "FBR configuration for the '%s' environment is incomplete. "
                "Please configure the Token and URL in Accounting -> Settings.",
                environment.title()
            ))
        return {'token': token, 'url': url}

    def _prepare_fbr_payload(self, invoice):
        """
        Constructs the detailed JSON payload from the invoice data,
        matching the production example.
        """
        invoice.ensure_one()

        if invoice.move_type == 'out_invoice':
            invoice_type = 'Sale Invoice'
        elif invoice.move_type == 'out_refund':
            invoice_type = 'Credit Note' # Correct term for customer refund
        else:
            # Fallback, though the action should prevent this
            invoice_type = 'Sale Invoice'

        seller = invoice.company_id
        buyer = invoice.partner_id
        journal_type = invoice.journal_id.type
        payment_mode = 'Cash' if journal_type == 'cash' else 'Bank' if journal_type == 'bank' else 'Credit'

        payload = {
            "invoiceType": invoice_type,
            "invoiceDate": invoice.invoice_date.strftime("%Y-%m-%d"),
            "invoiceRefNo": invoice.name, # Using invoice name as the primary reference
            "sellerBusinessName": seller.name,
            "sellerProvince": seller.state_id.name or "",
            "sellerAddress": seller.street or "",
            "sellerNTNCNIC": seller.vat or "",
            "buyerNTNCNIC": buyer.vat or buyer.ref or "",
            "buyerBusinessName": buyer.name,
            "buyerProvince": buyer.state_id.name or "",
            "buyerAddress": buyer.contact_address or buyer.street or "",
            "buyerRegistrationType": "Registered" if buyer.vat else "Unregistered",
            "paymentMode": payment_mode,
            "totalInvoiceAmount": invoice.amount_total,
            "totalSalesTax": invoice.amount_tax,
            "items": []
        }
        
        # Add scenarioId only if it's set on the invoice
        if invoice.fbr_scenario_id:
            payload["scenarioId"] = invoice.fbr_scenario_id.code

        for idx, line in enumerate(invoice.invoice_line_ids.filtered(lambda l: not l.display_type), start=1):
            if not line.product_id: continue # Skip lines without products

            payload["items"].append({
                "itemSNo": idx,
                "hsCode": line.product_id.fbr_hs_code or "",
                "productDescription": line.name,
                "unitPrice": line.price_unit,
                "rate": "18%", # Placeholder: You should add a field on account.move.line for this
                "uoM": line.product_uom_id.name or "each",
                "quantity": line.quantity,
                "valueSalesExcludingST": line.price_subtotal,
                "salesTaxApplicable": line.price_total - line.price_subtotal,
                "discount": (line.price_unit * line.quantity) * (line.discount / 100.0),
                "totalValues": line.price_total,
            })
            
        return payload

    def send_request(self, payload, environment):
        """
        Sends the request to the specified FBR endpoint and returns the JSON response.
        :param payload: The JSON payload to send.
        :param environment: 'sandbox' or 'production'.
        """
        config = self._get_fbr_config(environment)
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {config["token"]}'}
        
        _logger.info(
            "Sending FBR payload to %s (%s):\n%s",
            environment.upper(), config['url'], json.dumps(payload, indent=2)
        )
        
        try:
            response = requests.post(config['url'], headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            response_data = response.json()
            _logger.info(
                "Received FBR response from %s:\n%s",
                environment.upper(), json.dumps(response_data, indent=2)
            )
            return response_data
        except requests.exceptions.Timeout:
            _logger.error("FBR API request timed out (%s).", environment)
            raise UserError(_("The request to the FBR server timed out. Please try again later."))
        except requests.exceptions.RequestException as e:
            error_body = e.response.text if e.response else "No response from server"
            _logger.error("FBR API request failed (%s): %s\nResponse: %s", environment, e, error_body)
            raise UserError(_(f"A network error occurred while communicating with FBR: {error_body}"))