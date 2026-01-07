# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _


class TmsSatEmbalaje(models.Model):
    """
    Catálogo c_TipoEmbalaje del SAT.
    Contiene los tipos de embalaje para mercancías en Carta Porte 3.1.

    Ejemplos: Caja, Pallet, Contenedor, Granel, etc.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.embalaje'

    # Descripción del modelo
    _description = 'Catálogo SAT - Tipo de Embalaje (c_TipoEmbalaje)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código del tipo de embalaje (ej: "4A", "4B", "4C")
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código de tipo de embalaje según catálogo c_TipoEmbalaje del SAT'
    )

    # Descripción del embalaje
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción del tipo de embalaje'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'El código de embalaje SAT ya existe.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name')
    def _compute_display_name(self):
        """
        Muestra: "Código - Descripción"
        Ejemplo: "4A - Caja de madera"
        """
        for record in self:
            record.display_name = f"{record.code} - {record.name}"

    # Odoo 19: Búsqueda flexible en múltiples campos
    _rec_names_search = ['code', 'name']
