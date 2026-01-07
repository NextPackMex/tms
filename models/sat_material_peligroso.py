# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _


class TmsSatMaterialPeligroso(models.Model):
    """
    Catálogo c_MaterialPeligroso del SAT.
    Contiene las claves de materiales peligrosos para Carta Porte 3.1.

    Se usa cuando se transportan sustancias peligrosas que requieren
    documentación especial según normativa SCT (Secretaría de Comunicaciones).

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.material.peligroso'

    # Descripción del modelo
    _description = 'Catálogo SAT - Material Peligroso (c_MaterialPeligroso)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código del material peligroso (ej: "1203", "1170", etc.)
    # Este código corresponde al número UN (United Nations)
    code = fields.Char(
        string='Clave SAT / UN',
        required=True,
        index=True,
        help='Código de material peligroso según catálogo c_MaterialPeligroso del SAT'
    )

    # Descripción del material peligroso
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción del material peligroso'
    )

    # Clase del material peligroso (División según normativa)
    # Ejemplos: "3" (Líquidos inflamables), "2.1" (Gases inflamables), etc.
    clase = fields.Char(
        string='Clase',
        help='Clase o división del material peligroso según normativa SCT'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'El código de material peligroso SAT ya existe.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name', 'clase')
    def _compute_display_name(self):
        """
        Muestra: "Código - Descripción (Clase X)"
        Ejemplo: "1203 - Gasolina (Clase 3)"
        """
        for record in self:
            if record.clase:
                record.display_name = f"{record.code} - {record.name} (Clase {record.clase})"
            else:
                record.display_name = f"{record.code} - {record.name}"

    # Odoo 19: Búsqueda flexible en múltiples campos
    _rec_names_search = ['code', 'name', 'clase']
