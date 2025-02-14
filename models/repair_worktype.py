from odoo import models, fields

# gestione Tipo Lavorazione
class RepairWorktype(models.Model):

    _name = 'tech.repair.worktype'
    _description = 'Lavoro da svolgere'

    name = fields.Char(string='Tipo Lavoro', required=True)
    description = fields.Html(
        string="Descrizione",
        translate=True,
        sanitize=False,  # Permette HTML senza restrizioni (può essere utile se vuoi pulsanti o formattazione speciale)
        sanitize_attributes=False,
        help="Inserisci una descrizione completa per la stampa e usa '/' per i comandi."
        )
    price = fields.Float(string='Prezzo', required=True, default=0.0)
    add_to_sum = fields.Boolean(string='Agg. a Tot.', default=False)
