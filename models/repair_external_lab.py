from odoo import models, fields

class RepairExternalLab(models.Model):
    _name = 'tech.repair.external.lab'
    _description = 'Interventi di Laboratori Esterni'
    _order = 'send_date desc, lab_id asc'

    tech_repair_order_id = fields.Many2one(
        'tech.repair.order', string='Riparazione', ondelete='cascade'
    )  # Collegamento alla riparazione

    lab_id = fields.Many2one(
        'res.partner', string='Laboratorio',
        domain=[('is_company', '=', True)], required=True
    )  # Selezione del laboratorio esterno

    operation_description = fields.Text(string='Descrizione Operazione')
    external_cost = fields.Float(string='Costo a Noi', default=0.0)
    customer_cost = fields.Float(string='Costo al Cliente', default=0.0)
    add_to_sum = fields.Boolean(string='Agg. a Tot.', default=False)


     # Data invio merce
    send_date = fields.Datetime(string='Data Partito da TECH', readonly=False)

    # Data ritiro merce
    out_date = fields.Datetime(
        string='Data Rientrato',
        readonly=False,
    )
