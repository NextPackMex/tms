from odoo import models, fields


class TmsEvidencePhoto(models.Model):
    """Modelo para almacenar evidencia fotográfica de viajes.

    Cada fotografía se asocia a un viaje (waybill) con metadatos
    de tipo, fecha, usuario y observaciones opcionales.
    """
    _name = 'tms.evidence.photo'
    _description = 'Evidencia Fotográfica de Viajes'
    _order = 'date desc'

    waybill_id = fields.Many2one(
        'tms.waybill',
        string='Viaje',
        required=True,
        ondelete='cascade',
        help='Viaje al que pertenece esta evidencia'
    )

    photo = fields.Binary(
        string='Foto',
        required=True,
        help='Imagen en formato base64'
    )

    photo_filename = fields.Char(
        string='Nombre del archivo',
        help='Nombre original del archivo de imagen'
    )

    photo_type = fields.Selection(
        selection=[
            ('salida_origen', 'Salida de Origen'),
            ('carga_origen', 'Carga en Origen'),
            ('entrega_destino', 'Entrega en Destino'),
            ('odometro', 'Odómetro'),
            ('incidente', 'Incidente'),
            ('otro', 'Otro'),
        ],
        string='Tipo de Evidencia',
        required=True,
        help='Clasificación de la fotografía'
    )

    date = fields.Datetime(
        string='Fecha/Hora',
        default=fields.Datetime.now,
        readonly=True,
        help='Fecha y hora de captura (automática)'
    )

    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        default=lambda self: self.env.user,
        readonly=True,
        help='Usuario que subió la fotografía'
    )

    notes = fields.Text(
        string='Notas',
        help='Observaciones opcionales sobre la fotografía'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        related='waybill_id.company_id',
        store=True,
        readonly=True,
        help='Empresa del viaje asociado'
    )
