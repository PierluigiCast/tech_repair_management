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