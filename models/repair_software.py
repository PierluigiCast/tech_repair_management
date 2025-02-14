from odoo import models, fields, api
from datetime import timedelta

class RepairSoftware(models.Model):
    _name = 'tech.repair.software'
    _description = 'Software Installato'

    name = fields.Char(string='Software', required=True, index=True)
    price = fields.Float(string='Prezzo', required=True, default=0.0)
    renewal_required = fields.Boolean(string='Necessita Rinnovo', default=False)
    add_to_sum = fields.Boolean(string='Agg. a Tot.', default=False)

    
    duration = fields.Selection([
        ('1', '1 Mese'),
        ('3', '3 Mesi'),
        ('6', '6 Mesi'),
        ('12', '12 Mesi'),
        ('24', '24 Mesi')
    ], string="Durata Software", required=True, default='12')

    tech_repair_order_ids = fields.Many2many('tech.repair.order', string="Commesse Associate")
