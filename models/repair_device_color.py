from odoo import models, fields

class RepairDeviceColor(models.Model):
    _name = 'tech.repair.device.color'
    _description = 'Colori Dispositivi'

    name = fields.Char(string="Colore", required=True)
