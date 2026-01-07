# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _


class TmsSatClaveProd(models.Model):
    """
    Catálogo c_ClaveProdServCP del SAT.
    Contiene las claves de productos y servicios para Carta Porte 3.1.

    ARQUITECTURA SAAS: Este catálogo es GLOBAL (sin company_id).
    Los datos son estándares federales compartidos entre todas las empresas.
    """

    # Nombre técnico del modelo (tabla: tms_sat_clave_prod)
    _name = 'tms.sat.clave.prod'

    # Descripción del modelo
    _description = 'Catálogo SAT - Clave Producto/Servicio (c_ClaveProdServCP)'

    # Campo que se usa como nombre del registro en búsquedas
    # Cuando buscas un producto SAT, aparecerá el código (ej: "01010101")
    _rec_name = 'code'

    # Orden por defecto: alfabético por código
    _order = 'code asc'

    # ============================================================
    # CAMPOS DEL CATÁLOGO
    # ============================================================

    # Char: código de la clave SAT (ej: "01010101")
    # index=True: crea un índice en la BD para búsquedas rápidas
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código de producto o servicio según catálogo c_ClaveProdServCP del SAT'
    )

    # Char: descripción completa del producto/servicio
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción oficial del producto o servicio según el SAT'
    )

    # Selection: indica si es material peligroso
    # Valores según catálogo del SAT:
    # '0' = No es material peligroso
    # '1' = Sí es material peligroso (obligatorio declarar)
    # '0,1' = Puede ser peligroso o no (depende de características)
    material_peligroso = fields.Selection(
        string='Material Peligroso',
        selection=[
            ('0', 'No'),                    # No es material peligroso
            ('1', 'Sí'),                    # Sí es material peligroso
            ('0,1', 'Opcional'),            # Puede ser o no
        ],
        help='Indica si la clave corresponde a un material peligroso según el SAT'
    )

    # Char: palabras clave para facilitar búsquedas
    # Ejemplo: para "cemento" podría ser "construccion material gris portland"
    palabras_clave = fields.Char(
        string='Palabras Clave',
        help='Términos de búsqueda para facilitar la localización de la clave'
    )

    # ============================================================
    # CONSTRAINTS SQL
    # ============================================================

    # Constraint: el código debe ser único
    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'El código de producto SAT ya existe. No se pueden duplicar claves.',
    )

    # ============================================================
    # MÉTODOS OVERRIDE
    # ============================================================

    @api.depends('code', 'name')
    def _compute_display_name(self):
        """
        Sobrescribe cómo se muestra el nombre del registro.
        Ejemplo: "01010101 - Animales vivos de granja"
        """
        for record in self:
            record.display_name = f"{record.code} - {record.name[:100]}"

    # Odoo 19: Búsqueda flexible en múltiples campos
    _rec_names_search = ['code', 'name', 'palabras_clave']
