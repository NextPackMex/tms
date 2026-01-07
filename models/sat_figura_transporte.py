# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TmsSatFiguraTransporte(models.Model):
    """
    Catálogo c_FiguraTransporte del SAT.
    Define las figuras que participan en el transporte.

    EJEMPLOS:
    - 01: Operador
    - 02: Propietario
    - 03: Arrendador
    - 04: Notificado

    USO: Se declara en Carta Porte el rol de cada participante en el transporte.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.figura.transporte'

    # Descripción del modelo
    _description = 'Catálogo SAT - Figura Transporte (c_FiguraTransporte)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código de la figura (ej: "01", "02", "03")
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código de figura de transporte según c_FiguraTransporte del SAT'
    )

    # Descripción de la figura
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción del tipo de figura en el transporte'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'El código de figura de transporte ya existe.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name')
    def _compute_display_name(self):
        """Muestra: "Código - Descripción" """
        for record in self:
            record.display_name = f"{record.code} - {record.name}"

