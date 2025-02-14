from odoo import models, fields, api

class RepairSoftwareLine(models.Model):
    _name = 'tech.repair.software.line'
    _description = 'Riga Software per la commessa di riparazione'

    repair_order_id = fields.Many2one(
        'tech.repair.order', 
        string="Commessa di riparazione", 
        required=True, 
        ondelete='cascade'
    )
    software_id = fields.Many2one(
        'tech.repair.software', 
        string="Software", 
        required=True
    )
    add_to_sum = fields.Boolean(
        string="Aggiungi al totale", 
        default=True
    )


    # Campi correlati per visualizzare le informazioni del software
    software_price = fields.Float(
        related='software_id.price', 
        string="Prezzo", 
        readonly=True
    )
    software_renewal_required = fields.Boolean(
        related='software_id.renewal_required', 
        string="Rinnovo Richiesto", 
        readonly=True
    )
    software_duration = fields.Selection(
        related='software_id.duration', 
        string="Durata", 
        readonly=True
    )
