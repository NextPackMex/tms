# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TmsSatConfigAutotransporte(models.Model):
    """
    Catálogo c_ConfigAutotransporte del SAT.
    Define las configuraciones vehiculares permitidas para autotransporte.

    EJEMPLOS:
    - C2: Camión Unitario de 2 ejes
    - T3S2: Tractocamión con Semirremolque (3 ejes + 2 ejes)
    - C3R2: Camión con Remolque

    USO: Se usa en Carta Porte para especificar el tipo exacto de vehículo.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.config.autotransporte'

    # Descripción del modelo
    _description = 'Catálogo SAT - Configuración Autotransporte (c_ConfigAutotransporte)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código de configuración (ej: "C2", "T3S2", "C3R2")
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código de configuración vehicular según c_ConfigAutotransporte'
    )

    # Descripción de la configuración
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción de la configuración del autotransporte'
    )

    # Número de remolques que soporta esta configuración
    # 0 = Camión unitario (sin remolque)
    # 1 = Un remolque
    # 2 = Doble remolque
    numero_ejes_remolque = fields.Integer(
        string='Número de Ejes de Remolque',
        default=0,
        help='Cantidad de ejes del remolque o semirremolque (0 si no lleva)'
    )

    # NUEVO: Número de llantas
    total_tires = fields.Char(
        string='Número de Llantas',
        help='Número de llantas (ej. 04, 06, 18)'
    )

    # NUEVO: Indicador de Remolque (Char para soportar "0, 1")
    remolque = fields.Char(
        string='Remolque',
        help='Aplica remolque (0=No, 1=Si, 0,1=Opcional)'
    )

    # NUEVO: Vigencia Inicio
    vigencia_inicio = fields.Date(string='Fecha Inicio Vigencia')

    # NUEVO: Vigencia Fin
    vigencia_fin = fields.Date(string='Fecha Fin Vigencia')

    # Integer: Total de ejes de la configuración (Tractor + Remolque)
    # Se usa para cálculo de casetas en Google Maps API
    total_axles = fields.Integer(
        string='Total de Ejes',
        default=2,
        help='Número total de ejes de la configuración (incluyendo tractor y remolques). Usado para API de Mapas.'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'El código de configuración ya existe.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} - {record.name}"

