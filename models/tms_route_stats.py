# -*- coding: utf-8 -*-
"""
Modelo de Estadísticas de Rentabilidad por Ruta.

Acumula métricas de ingresos y operación por par de códigos postales
(origin_zip → dest_zip) por empresa. Se actualiza automáticamente
cada vez que un waybill cierra (state='closed').

Alimenta el módulo de KPIs y dashboard de rentabilidad (V2.6).
"""
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class TmsRouteStats(models.Model):
    """
    Estadísticas acumuladas de rentabilidad por ruta.

    Una ruta se identifica por el par (origin_zip, dest_zip, company_id).
    Los acumuladores se actualizan sin sobrescribir el histórico.
    """
    _name        = 'tms.route.stats'
    _description = 'Estadísticas de Rentabilidad por Ruta'
    _order       = 'total_viajes desc, ingreso_total desc'
    _rec_name    = 'route_name'

    # ============================================================
    # CAMPOS DE IDENTIFICACIÓN
    # ============================================================

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        check_company=True,
    )

    origin_zip = fields.Char(
        string='CP Origen',
        size=5,
    )

    dest_zip = fields.Char(
        string='CP Destino',
        size=5,
    )

    route_name = fields.Char(
        string='Ruta',
        help='Nombre de ruta con ciudades reales, actualizado desde el waybill al cerrar.',
    )

    route_display = fields.Char(
        string='Ruta (Display)',
        compute='_compute_route_display',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )

    # ============================================================
    # ACUMULADORES
    # ============================================================

    total_viajes = fields.Integer(
        string='Total Viajes',
        default=0,
    )

    ingreso_total = fields.Float(
        string='Ingreso Total',
        default=0.0,
        digits=(16, 2),
    )

    ingreso_promedio = fields.Float(
        string='Ingreso Promedio',
        compute='_compute_ingreso_promedio',
        store=True,
        digits=(16, 2),
    )

    # ============================================================
    # ÚLTIMO VIAJE
    # ============================================================

    last_price = fields.Float(
        string='Último Precio',
        digits=(16, 2),
        help='Monto total del último viaje cerrado en esta ruta.',
    )

    last_waybill_date = fields.Date(
        string='Última Fecha de Cierre',
        help='Fecha del último waybill cerrado en esta ruta.',
    )

    distance_km = fields.Float(
        string='Distancia Promedio (km)',
        digits=(10, 2),
        help='Distancia promedio calculada de los viajes registrados.',
    )

    # ============================================================
    # RESTRICCIÓN ÚNICA
    # ============================================================

    _unique_route_company = models.Constraint(
        'unique(origin_zip, dest_zip, company_id)',
        'Ya existe un registro de estadísticas para esta ruta y empresa.',
    )

    # ============================================================
    # MÉTODOS COMPUTE
    # ============================================================

    @api.depends('route_name', 'origin_zip', 'dest_zip')
    def _compute_route_display(self):
        """Muestra nombre de ciudad si está disponible, si no usa CPs."""
        for rec in self:
            rec.route_display = rec.route_name or f"{rec.origin_zip or '?????'} → {rec.dest_zip or '?????'}"

    @api.depends('ingreso_total', 'total_viajes')
    def _compute_ingreso_promedio(self):
        """Calcula el ingreso promedio por viaje. Retorna 0.0 si no hay viajes."""
        for rec in self:
            if rec.total_viajes > 0:
                rec.ingreso_promedio = rec.ingreso_total / rec.total_viajes
            else:
                rec.ingreso_promedio = 0.0

    # ============================================================
    # SEMILLA: HOOK DESDE tms.waybill
    # ============================================================

    @api.model
    def _update_from_waybill(self, waybill):
        """
        Actualiza o crea el registro de estadísticas cuando un waybill cierra.

        Busca por (origin_zip, dest_zip, company_id). Si el par ya existe,
        actualiza los acumuladores con los datos del viaje. Si no existe,
        crea un registro nuevo.

        Parámetros:
          waybill: instancia de tms.waybill en estado 'closed'

        Campos leídos del waybill:
          - origin_zip: CP de origen del viaje
          - dest_zip: CP de destino del viaje
          - company_id: empresa del viaje
          - amount_total: ingreso total del viaje (con impuestos)
          - distance_km: distancia de la ruta calculada
          - date_created: fecha de creación del viaje (proxy de fecha de cierre)
        """
        # Extraer datos relevantes del waybill
        origin_zip  = waybill.origin_zip or ''
        dest_zip    = waybill.dest_zip or ''
        company     = waybill.company_id
        ingreso     = waybill.amount_total or 0.0
        distancia   = waybill.distance_km or 0.0
        fecha       = waybill.date_created
        nombre_ruta = waybill.route_name or f"{origin_zip} → {dest_zip}"

        # Sin CPs no podemos identificar la ruta — omitir silenciosamente
        if not origin_zip or not dest_zip:
            _logger.warning(
                'TMS RouteStats: waybill %s sin origin_zip o dest_zip — omitido.',
                waybill.name,
            )
            return

        stats = self.search([
            ('origin_zip', '=', origin_zip),
            ('dest_zip',   '=', dest_zip),
            ('company_id', '=', company.id),
        ], limit=1)

        if stats:
            # Actualizar acumuladores del registro existente
            nuevo_total_viajes = stats.total_viajes + 1
            nuevo_ingreso_total = stats.ingreso_total + ingreso

            # Distancia promedio ponderada con el nuevo viaje
            if distancia:
                nueva_distancia = (
                    (stats.distance_km * stats.total_viajes + distancia)
                    / nuevo_total_viajes
                )
            else:
                nueva_distancia = stats.distance_km

            stats.write({
                'total_viajes':      nuevo_total_viajes,
                'ingreso_total':     nuevo_ingreso_total,
                'last_price':        ingreso,
                'last_waybill_date': fecha,
                'distance_km':       nueva_distancia,
                'route_name':        nombre_ruta,
            })
            _logger.info(
                'TMS RouteStats: actualizado %s → %s (viajes=%s, ingreso_total=%.2f)',
                origin_zip, dest_zip, nuevo_total_viajes, nuevo_ingreso_total,
            )
        else:
            # Crear registro nuevo para esta ruta
            self.create({
                'company_id':        company.id,
                'origin_zip':        origin_zip,
                'dest_zip':          dest_zip,
                'route_name':        nombre_ruta,
                'total_viajes':      1,
                'ingreso_total':     ingreso,
                'last_price':        ingreso,
                'last_waybill_date': fecha,
                'distance_km':       distancia,
            })
            _logger.info(
                'TMS RouteStats: creado nuevo registro %s → %s (ingreso=%.2f)',
                origin_zip, dest_zip, ingreso,
            )
