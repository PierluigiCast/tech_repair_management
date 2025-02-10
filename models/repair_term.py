from odoo import models, fields, api

class RepairInformativa(models.Model):
    _name = 'tech.repair.term'
    _description = "Informativa per le Riparazioni"

    name = fields.Char(string="Titolo", required=True)
    contenuto = fields.Html(string="Testo Informativa", required=True)
    predefinita = fields.Boolean(string="Usa come Predefinita", default=False)

    @api.constrains('predefinita')
    def _check_unique_default(self):
        # Permette di avere una sola informativa predefinita attiva alla volta
        for record in self:
            if record.predefinita:
                other_defaults = self.search([('predefinita', '=', True), ('id', '!=', record.id)])
                if other_defaults:
                    raise models.ValidationError("Può esistere solo un'informativa predefinita alla volta!")