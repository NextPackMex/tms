# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _


class TmsSatClaveUnidad(models.Model):
    """
    Catálogo c_ClaveUnidad del SAT.
    Contiene las claves de unidades de medida para Carta Porte 3.1.

    Ejemplos: KG (Kilogramo), LT (Litro), PZ (Pieza), etc.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.clave.unidad'

    # Descripción del modelo
    _description = 'Catálogo SAT - Clave Unidad (c_ClaveUnidad)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código de la unidad (ej: "KGM", "LTR", "H87")
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código de unidad de medida según catálogo c_ClaveUnidad del SAT'
    )

    # Descripción de la unidad (ej: "Kilogramo", "Litro", "Pieza")
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción de la unidad de medida'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'El código de unidad SAT ya existe.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name')
    def _compute_display_name(self):
        """
        Muestra: "Código - Descripción"
        Ejemplo: "KGM - Kilogramo"
        """
        for record in self:
            record.display_name = f"{record.code} - {record.name}"

    # Odoo 19: Búsqueda flexible en múltiples campos
    _rec_names_search = ['code', 'name']
