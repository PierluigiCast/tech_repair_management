from odoo import models, fields

# gestione dispositivi da riparare
class RepairModel(models.Model):
    _name = 'tech.repair.model'
    _description = 'Modello Dispositivo'

    name = fields.Char(string='Modello', required=True)
    brand_id = fields.Many2one('tech.repair.brand', string='Marca')
    