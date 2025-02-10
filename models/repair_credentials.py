from odoo import models, fields

class RepairCredential(models.Model):
    _name = 'tech.repair.credential'
    _description = 'Credenziali per Riparazione'
    _order = 'open_date desc, username asc'

    tech_repair_order_id = fields.Many2one(
        'tech.repair.order', 
        string="Riparazione", 
        ondelete='cascade'
    )

    open_date = fields.Datetime(string='Inserita il', default=lambda self: fields.Datetime.now(), readonly=True)

    service_type = fields.Selection([
        ('icloud', 'iCloud'),
        ('gmail', 'Gmail'),
        ('mail', 'Mail'),
        ('other', 'Altro')
    ], string="Servizio", required=True, default='icloud')

    service_other = fields.Char(string="Altro")

    username = fields.Char(string="User", required=True)
    password = fields.Char(string="Password", required=True)

    
