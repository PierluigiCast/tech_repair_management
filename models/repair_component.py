import logging
import json
from odoo import models, fields, api

class RepairComponent(models.Model):
    _name = 'tech.repair.component'
    _description = 'Componente utilizzati in riparazione'
    _logger = logging.getLogger(__name__)

    # Collegamento alla "commessa" (repair order)
    repair_order_id = fields.Many2one('tech.repair.order', string='Commessa')

    # Prodotto effettivo (product.product)
    product_id = fields.Many2one('product.product', string='Componente')

    supplier_domain = fields.Char(
        compute='_compute_supplier_domain',
        store=False  # Di solito è un dominio dinamico, quindi non si salva su DB
    )
    # Questi campi sono "locali" alla singola commessa
    supplier_id = fields.Many2one(
        'res.partner',
        string="Fornitore",
        domain=[('is_company', '=', True)]
    )
    purchase_date = fields.Date(string="Data di Acquisto")
    receipt_date = fields.Date(string="Data di Ricezione")
    serial_number = fields.Char(string="Seriale")
    pur_price = fields.Float(string='Costo Componente €', default=0.0)
    lst_price = fields.Float(string='Prezzo €', default=0.0)


    # Calcolo il dominio valido per supplier_id in base ai seller_ids del template e lo imposto nella vista
    @api.depends('product_id')
    def _compute_supplier_domain(self):
        
        for rec in self:
            if rec.product_id:
                partner_ids = rec.product_id.product_tmpl_id.seller_ids.mapped('partner_id').ids
                # Prepara la tupla di dominio
                domain = [('id', 'in', partner_ids)]
            else:
                domain = []  # Nessun fornitore permesso

            # Converti la lista di tuple in JSON
            rec.supplier_domain = json.dumps(domain)

    # Quando seleziono il Prodotto, restringo la lista dei fornitori in base ai 'seller_ids' del Product Template
    # @api.onchange('product_id')
    # def _onchange_product_id(self):
        
        # self._logger.info("entrato")
        # if self.product_id:
        #     # Ottieni la lista di partner (fornitori) dal Template
        #     template = self.product_id.product_tmpl_id
        #     partner_ids = template.seller_ids.mapped('partner_id').ids  # 'partner_id' su product.supplierinfo -> res.partner
        #     self._logger.info("valori: %s",partner_ids)
        #     return {
        #         'domain': {
        #             'supplier_id': [('id', 'in', partner_ids)]
        #         }
        #     }
        # else:
        #     # Se non ho un product_id, azzero il dominio
        #     return {
        #         'domain': {
        #             'supplier_id': []
        #         }
        #     }
        
        
        # domain = {'supplier_id': []}

        # if self.product_id:
        #     # Recuperiamo i partner id dai seller_ids del template
        #     partner_ids = self.product_id.product_tmpl_id.seller_ids.mapped('partner_id').ids

        #     # Se vuoi anche resettare la selezione del fornitore
        #     self.supplier_id = False

        #     # Impostiamo il dominio
        #     domain = {'supplier_id': [('id', 'in', partner_ids)]}

        # # Restituiamo il dominio come parte del return
        #     self._logger.info("dominio: %s",domain)
        # return {'domain': domain}