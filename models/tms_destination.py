# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TmsDestination(models.Model):
    """
    Modelo para gestionar Rutas Comerciales (Punto A -> Punto B).

    CONCEPTO: Representa rutas frecuentes que la empresa maneja.
    Ejemplo: "GDL-CDMX", "Monterrey-Tijuana"

    USO: Pre-llenar datos en cotizaciones (origen, destino, distancia, tiempo, casetas).

    =========================================================
    ARQUITECTURA SAAS (CRÍTICO):
    =========================================================
    Este modelo es PRIVADO por empresa.

    ¿POR QUÉ?
    - La Empresa A tiene sus propias rutas comerciales
    - La Empresa B NO debe ver las rutas de la Empresa A
    - Cada empresa maneja diferentes orígenes/destinos

    SOLUCIÓN:
    - company_id es OBLIGATORIO (required=True)
    - Record Rule filtra por company_id (ver security/tms_security.xml)
    - Domain en búsquedas incluye company_id
    """

    # Nombre técnico del modelo (tabla: tms_destination)
    _name = 'tms.destination'

    # Descripción del modelo
    _description = 'Ruta Comercial (Punto A -> Punto B)'

    # Orden por defecto
    _order = 'name asc'

    # ============================================================
    # CAMPO CRÍTICO SAAS: company_id
    # ============================================================

    # Many2one: compañía propietaria de la ruta
    # OBLIGATORIO: Cada ruta debe pertenecer a una empresa
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,                              # ← OBLIGATORIO para SaaS
        default=lambda self: self.env.company,      # ← Compañía actual por defecto
        index=True,                                  # ← Índice para Record Rules rápidas
        help='Compañía a la que pertenece esta ruta (CRÍTICO para multi-empresa)'
    )

    # ============================================================
    # CAMPOS ESENCIALES DE RUTA (Punto A -> Punto B)
    # ============================================================

    # Many2one: moneda (relacionada a la compañía)
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
    )

    # ============================================================
    # CAMPOS ESENCIALES DE RUTA (ZIP A -> ZIP B)
    # ============================================================

    origin_zip = fields.Char(string='CP Origen', required=True, index=True)
    dest_zip = fields.Char(string='CP Destino', required=True, index=True)

    vehicle_type_id = fields.Many2one('tms.vehicle.type', string="Tipo de Vehículo")

    # Identificación básica (Computado)
    name = fields.Char(string='Nombre de la Ruta', compute='_compute_name', store=True)

    @api.depends('origin_zip', 'dest_zip', 'vehicle_type_id')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.origin_zip} -> {record.dest_zip} ({record.vehicle_type_id.name or 'N/A'})"


    active = fields.Boolean(default=True, string="Activa")

    distance_km = fields.Float(string='Distancia (km)', digits=(10, 2))
    duration_hours = fields.Float(string='Duración (hrs)', digits=(10, 2))
    notes = fields.Text(string='Notas')

    # Float: costo de casetas para esta ruta
    cost_tolls = fields.Float(
        string='Costo de Casetas',
        digits=(10, 2),
        help='Costo calculado de casetas'
    )

    last_update = fields.Date(string="Última Actualización", default=fields.Date.context_today)

    _unique_route = models.Constraint(
        'unique(company_id, origin_zip, dest_zip, vehicle_type_id)',
        'Ya existe una ruta guardada para este origen, destino y tipo de vehículo.',
    )
