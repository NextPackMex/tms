# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TmsSatCodigoPostal(models.Model):
    """
    Catálogo c_CodigoPostal del SAT.
    Contiene los códigos postales con su información geográfica.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    IMPORTANTE: El código postal puede tener duplicados cuando se combina
    con diferentes estados/municipios, por lo que la unicidad se garantiza
    con la combinación (code, estado, municipio).
    """

    _name = 'tms.sat.codigo.postal'
    _description = 'Catálogo de Códigos Postales SAT'
    _rec_name = 'code'
    _order = 'code asc, estado asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    code = fields.Char(
        string='Código Postal',
        required=True,
        index=True,
        help='Código postal de 5 dígitos'
    )

    estado = fields.Char(
        string='Estado',
        index=True,
        help='Estado al que pertenece el código postal'
    )

    municipio = fields.Char(
        string='Municipio',
        help='Municipio al que pertenece el código postal'
    )

    localidad = fields.Char(
        string='Localidad',
        help='Localidad al que pertenece el código postal'
    )

    # ============================================================
    # CONSTRAINTS - UNICIDAD COMPUESTA
    # ============================================================

    # REGLA: La combinación CP + Estado + Municipio debe ser única
    # Esto previene el error si el mismo CP existe para diferentes zonas
    # (raro, pero posible en datos sucios o archivos con inconsistencias)
    _code_estado_muni_uniq = models.Constraint(
        'unique(code, estado, municipio)',
        'El Código Postal ya existe para este Estado/Municipio.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'municipio', 'estado')
    def _compute_display_name(self):
        """
        Muestra: "CP - Municipio (Estado)"
        Ejemplo: "64000 - Aguascalientes (AGU)"
        """
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.municipio or ''} ({rec.estado or ''})"
