from odoo import models, fields

class RepairStatePublic(models.Model):
    _name = 'tech.repair.state.public'
    _description = 'Stati Visibili ai Clienti'
    _order = 'sequence asc'

    name = fields.Char(string="Nome Stato Cliente", required=True)
    description = fields.Text(string="Descrizione Stato")
    sequence = fields.Integer(string="Ordine", default=10)
