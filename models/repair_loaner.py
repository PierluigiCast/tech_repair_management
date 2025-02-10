from odoo import models, fields

class RepairLoanerDevice(models.Model):
    _name = 'tech.repair.loaner_device'
    _description = 'Dispositivi Muletto'

    name = fields.Char(string='Nome Dispositivo', required=True)
    serial_number = fields.Char(string='Seriale / IMEI', required=True)
    aesthetic_condition = fields.Selection([
        ('new', 'Nuovo'),
        ('good', 'Buono'),
        ('used', 'Usato'),
        ('damaged', 'Danneggiato')
    ], string='Stato Estetico', default='good')
    description = fields.Text(string='Descrizione')
    tech_repair_order_id = fields.Many2one('tech.repair.order', string='Assegnato alla Riparazione', ondelete='set null')

    status = fields.Selection([
        ('available', 'Disponibile'),
        ('assigned', 'Assegnato'),
        ('maintenance', 'In Manutenzione')
    ], string='Stato', default='available')

    def name_get(self):
        # Personalizza la visualizzazione nei campi Many2one
        result = []
        for device in self:
            name = f"{device.name} ({device.serial_number})"
            result.append((device.id, name))
        return result
    
    def mark_as_available(self):
        # Metodo per liberare il muletto e renderlo di nuovo disponibile """
        for record in self:
            record.status = 'available'
            record.tech_repair_order_id = False
    
