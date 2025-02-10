from odoo import models, fields

# gestione categorie
class RepairCategory(models.Model):

    _name = 'tech.repair.category'
    _description = 'Categoria Dispositivo'

    name = fields.Char(string='Categoria', required=True)