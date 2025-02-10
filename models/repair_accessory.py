from odoo import models, fields

class RepairAccessory(models.Model):
    _name = 'tech.repair.accessory'
    _description = 'Accessori Lasciati dal Cliente'
    _order = 'name asc'

    tech_repair_order_id = fields.Many2one(
        'tech.repair.order', 
        string="Riparazione", 
        ondelete='cascade'
    )

    aesthetic_condition = fields.Selection([
        ('new', 'Nuovo'),
        ('good', 'Buono'),
        ('used', 'Usato'),
        ('damaged', 'Danneggiato')
    ], string='Stato Estetico', default='good')

    name = fields.Selection([
        ('alimentatore', 'Alimentatore'),
        ('cover', 'Cover'),
        ('borsa', 'Borsa'),
        ('sim', 'SIM'),
        ('altro', 'Altro')
    ], string="Nome Accessorio", required=True, default='alimentatore')

    custom_name = fields.Char(string="Altro", help="Specificare il nome se 'Altro' è selezionato")
