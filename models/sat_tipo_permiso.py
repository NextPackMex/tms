# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TmsSatTipoPermiso(models.Model):
    """
    Catálogo c_TipoPermiso del SAT.
    Define los tipos de permisos SCT para autotransporte federal.

    EJEMPLOS:
    - TPAF01: Autotransporte Federal de carga general
    - TPAF02: Transporte privado de carga
    - TPAF06: Transporte de sustancias peligrosas

    USO: Se declara en Carta Porte el tipo de permiso del transportista.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.tipo.permiso'

    # Descripción del modelo
    _description = 'Catálogo SAT - Tipo de Permiso SCT (c_TipoPermiso)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código del permiso (ej: "TPAF01", "TPAF02")
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código del tipo de permiso según c_TipoPermiso del SAT'
    )

    # Descripción del permiso
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción del tipo de permiso SCT'
    )

    # Clave de transporte asociada
    clave_transporte = fields.Char(
        string='Clave de Transporte',
        help='Clave adicional relacionada con el tipo de transporte'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'El código de permiso ya existe.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name')
    def _compute_display_name(self):
        """Muestra: "Código - Descripción" """
        for record in self:
            record.display_name = f"{record.code} - {record.name}"

