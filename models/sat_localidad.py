# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TmsSatLocalidad(models.Model):
    """
    Catálogo c_Localidad del SAT.
    Contiene las localidades (poblaciones) por estado.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    IMPORTANTE: El código se repite por estado, por lo que la unicidad
    se garantiza con la combinación (code, estado).
    """

    _name = 'tms.sat.localidad'
    _description = 'Catálogo de Localidades SAT'
    _rec_name = 'name'  # Usamos name porque el código se repite
    _order = 'estado asc, name asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    code = fields.Char(
        string='Clave',
        required=True,
        index=True,
        help='Código de localidad según catálogo c_Localidad del SAT'
    )

    estado = fields.Char(
        string='Estado',
        required=True,
        index=True,
        help='Estado al que pertenece la localidad'
    )

    name = fields.Char(
        string='Descripción',
        required=True,
        help='Nombre de la localidad'
    )

    # ============================================================
    # CONSTRAINTS - UNICIDAD COMPUESTA
    # ============================================================

    # REGLA DE UNICIDAD COMPUESTA: Clave + Estado
    # CRÍTICO: Permite que el mismo código exista en diferentes estados
    # Ejemplo: código '0001' puede existir en 'AGU' y en 'BCN' simultáneamente
    _code_estado_uniq = models.Constraint(
        'unique(code, estado)',
        'La combinación de Clave Localidad y Estado debe ser única.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name', 'estado')
    def _compute_display_name(self):
        """
        Muestra: "[Código] Descripción (Estado)"
        Ejemplo: "[0001] Aguascalientes (AGU)"
        """
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name} ({rec.estado})"
