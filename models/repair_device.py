from odoo import models, fields

class RepairDeviceCategory(models.Model):
    _name = 'tech.repair.device.category'
    _description = 'Categoria Dispositivi Riparazione'

    name = fields.Char(string='Categoria', required=True)


class RepairDeviceBrand(models.Model):
    _name = 'tech.repair.device.brand'
    _description = 'Marca Dispositivi Riparazione'

    name = fields.Char(string='Marca', required=True)
    category_id = fields.Many2one('tech.repair.device.category', string='Categoria', required=True)


class RepairDeviceModel(models.Model):
    _name = 'tech.repair.device.model'
    _description = 'Modello Dispositivi Riparazione'

    name = fields.Char(string='Modello', required=True)
    brand_id = fields.Many2one('tech.repair.device.brand', string='Marca', required=True)
