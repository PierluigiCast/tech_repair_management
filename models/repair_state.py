from odoo import models, fields

# Modello per gli stati delle riparazioni
class RepairState(models.Model):
    _name = 'tech.repair.state'
    _description = 'Stati Riparazione'

    # Nome dello stato (es. In attesa, In riparazione, Completato)
    name = fields.Char(string='Nome Stato', required=True)
    # Ordine di visualizzazione degli stati
    sequence = fields.Integer(string='Ordine', default=10)
    # Flag che imposta se chiudere o meno la commessa
    is_closed = fields.Boolean(string='È uno stato di chiusura?', default=False)  # Flag per definire gli stati chiusi
    # Flag per laboratori esterni
    is_external_lab = fields.Boolean(string='Operazione da Laboratorio Esterno?', default=False)  

    # Collegamento con lo stato visibile al cliente
    public_state_id = fields.Many2one(
        'tech.repair.state.public',
        string="Stato Visibile al Cliente",
        help="Quando questo stato è impostato, lo stato pubblico assegnato viene aggiornato automaticamente."
    )

