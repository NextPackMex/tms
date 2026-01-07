# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TmsSatMunicipio(models.Model):
    """
    Catálogo c_Municipio del SAT.
    Contiene los municipios por estado.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    IMPORTANTE: El código se repite por estado, por lo que la unicidad
    se garantiza con la combinación (code, estado).
    """

    _name = 'tms.sat.municipio'
    _description = 'Catálogo de Municipios SAT'
    _rec_name = 'name'  # Usamos name porque el código se repite
    _order = 'estado asc, name asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    code = fields.Char(
        string='Clave',
        required=True,
        index=True,
        help='Código de municipio según catálogo c_Municipio del SAT'
    )

    estado = fields.Char(
        string='Estado',
        required=True,
        index=True,
        help='Estado al que pertenece el municipio'
    )

    name = fields.Char(
        string='Descripción',
        required=True,
        help='Nombre del municipio'
    )

    # ============================================================
    # CONSTRAINTS - UNICIDAD COMPUESTA
    # ============================================================

    # REGLA DE UNICIDAD COMPUESTA: Clave + Estado
    _code_estado_uniq = models.Constraint(
        'unique(code, estado)',
        'La combinación de Clave Municipio y Estado debe ser única.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name', 'estado')
    def _compute_display_name(self):
        """
        Muestra: "[Código] Descripción (Estado)"
        Ejemplo: "[001] Aguascalientes (AGU)"
        """
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name} ({rec.estado})"
