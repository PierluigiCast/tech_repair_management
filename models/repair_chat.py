from odoo import models, fields, api

class RepairChatMessage(models.Model):
    _name = 'tech.repair.chat.message'
    _description = 'Messaggi Chat Riparazione'
    _order = 'create_date asc'

    tech_repair_order_id = fields.Many2one(
        'tech.repair.order', 
        string="Riparazione", 
        required=True, 
        ondelete='cascade'
    )

    sender = fields.Selection([
        ('customer', 'Cliente'),
        ('technician', 'Tecnico')
    ], string="Mittente", required=True, default='technician')

    message = fields.Text(string="Messaggio", required=True)
    create_date = fields.Datetime(string="Data", default=fields.Datetime.now, readonly=True)