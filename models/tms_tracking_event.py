from odoo import models, fields, api, _

class TmsTrackingEvent(models.Model):
    _name = 'tms.tracking.event'
    _description = 'Waybill Tracking Event'
    _order = 'date desc, id desc'

    waybill_id = fields.Many2one('tms.waybill', string='Waybill', required=True, ondelete='cascade')
    _waybill_date_idx = models.Index("(waybill_id, date)")
    name = fields.Selection([
        ('start', 'Inicio de Ruta'),
        ('arrival_origin', 'Llegada a Origen'),
        ('arrival_dest', 'Llegada a Destino'),
        ('loading', 'Cargando'),
        ('unloading', 'Descargando'),
        ('problem', 'Reporte de Problema'),
        ('tracking', 'Reporte de Ubicación (Ping)'),
        ('other', 'Otro')
    ], string='Tipo de Evento', required=True, default='start')

    date = fields.Datetime(string='Fecha y Hora', required=True, default=fields.Datetime.now)
    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))
    location_description = fields.Char(string='Ubicación / Dirección')
    notes = fields.Text(string='Notas')

    source = fields.Selection([
        ('manual', 'Manual'),
        ('app', 'App')
    ], string='Fuente', default='manual', readonly=True)
