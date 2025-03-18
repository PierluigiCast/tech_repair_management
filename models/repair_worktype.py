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
    price = fields.Float(string='Prezzo €', required=True, default=0.0)
    stimated_time = fields.Integer(string='Durata (gg)', default=1)
    extra_workflow = fields.Boolean(string='Ha lavorazioni Aggiuntive', default=False)
    extra_workflow_name = fields.Char(string='Lavorazione')
    extra_workflow_time = fields.Integer(string='Extra Durata(gg)', default=0)
    extra_workflow_price = fields.Float(string='Extra Prezzo €', default=0.0)
