from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    supplier_id = fields.Many2one('res.partner', string="Fornitore", domain=[('is_company', '=', True)])
    purchase_date = fields.Date(string="Data di Acquisto")
    receipt_date = fields.Date(string="Data di Ricezione")
    serial_number = fields.Char(string="Seriale")