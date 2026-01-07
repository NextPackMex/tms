# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TmsSatColonia(models.Model):
    """
    Catálogo c_Colonia del SAT.
    Contiene las colonias asociadas a códigos postales para Carta Porte 3.1.

    USO: Al capturar origen/destino, se usa el código postal para encontrar
    la colonia correcta según el catálogo del SAT.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    IMPORTANTE: El código se repite por código postal, por lo que la unicidad
    se garantiza con la combinación (code, zip_code).
    """

    _name = 'tms.sat.colonia'
    _description = 'Catálogo de Colonias SAT'
    _rec_name = 'name'  # Usamos name porque el código se repite
    _order = 'zip_code asc, name asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    code = fields.Char(
        string='Clave',
        required=True,
        index=True,
        help='Código de colonia según catálogo c_Colonia del SAT'
    )

    zip_code = fields.Char(
        string='Código Postal',
        required=True,
        index=True,
        help='Código postal de 5 dígitos'
    )

    name = fields.Char(
        string='Nombre del Asentamiento',
        required=True,
        help='Nombre oficial de la colonia según el SAT'
    )

    # ============================================================
    # CONSTRAINTS - UNICIDAD COMPUESTA
    # ============================================================

    # REGLA DE UNICIDAD COMPUESTA: Clave + CP
    # CRÍTICO: Permite que el mismo código exista en diferentes CPs
    # Ejemplo: código '0001' puede existir en CP '20000' y en CP '45000' simultáneamente
    _code_zip_uniq = models.Constraint(
        'unique(code, zip_code)',
        'La combinación de Clave Colonia y CP debe ser única.',
    )

    # ============================================================
    # MÉTODOS
    # ============================================================

    @api.depends('code', 'name', 'zip_code')
    def _compute_display_name(self):
        """
        Muestra: "[Código] Nombre (CP XXXXX)"
        Ejemplo: "[0001] Centro (CP 64000)"
        """
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name} (CP {rec.zip_code})"

    @api.model
    def get_colonias_by_cp(self, zip_code):
        """
        Método de utilidad para obtener todas las colonias de un código postal.

        :param zip_code: código postal (string de 5 dígitos)
        :return: recordset de colonias
        """
        return self.search([('zip_code', '=', zip_code)], order='name asc')
