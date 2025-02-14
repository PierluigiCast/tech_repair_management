from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    repair_order_id = fields.Many2one(
        'tech.repair.order',
        string="Commessa di Riparazione",
        help="Commessa di Riparazione associata al Lead"
    )
