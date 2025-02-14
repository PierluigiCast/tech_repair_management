from os import X_OK
from odoo import models, fields, api

class RepairExternalLabLine(models.Model):
    _name = 'tech.repair.external.lab.line'
    _description = 'Riga Lab Esterno per la commessa di riparazione'

    repair_order_id = fields.Many2one(
        'tech.repair.order', 
        string="Commessa di riparazione", 
        required=True, 
        ondelete='cascade'
    )
    lab_id = fields.Many2one(
        'tech.repair.external.lab', 
        string="Laboratorio", 
        required=True
    )

    add_to_sum = fields.Boolean(
        string="Aggiungi al totale", 
        default=True
    )

    # Campi correlati per visualizzare le informazioni del laboratorio

    operation_description = fields.Text(
        string='Descrizione Operazione'
        )
    external_cost = fields.Float(
        related='lab_id.external_cost', 
        string='Costo a Noi',
        default=0.0)

    customer_cost = fields.Float(
        related='lab_id.customer_cost', 
        string='Costo al Cliente',
        default=0.0)

    send_date = fields.Datetime(
        related='lab_id.send_date', 
        string='Data Partito da TECH',
        readonly=False)

    out_date = fields.Datetime(
        related='lab_id.out_date', 
        string='Data Rientrato',
        readonly=False,
    )
