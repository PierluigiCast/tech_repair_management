from odoo import models, fields

#modulo gestione brand
class RepairBrand(models.Model):
    _name = 'tech.repair.brand'
    _description = 'Marca Dispositivo'

    name = fields.Char(string='Marca', required=True)
    
