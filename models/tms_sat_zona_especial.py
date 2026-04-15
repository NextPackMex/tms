# -*- coding: utf-8 -*-
"""
Catálogo de Zonas Económicas Especiales (ZEDE) del SAT.

Las ZEDE son regiones con tratamiento fiscal diferenciado donde la tasa de IVA
es 0% en lugar del 16% estándar. Actualmente aplica al Istmo de Tehuantepec.

Referencia SAT:
  - Decreto por el que se establecen las Zonas Económicas Especiales (DOF 2016)
  - Decreto Istmo de Tehuantepec: CPs de Oaxaca y Veracruz que aplican tasa 0%

Regla en CFDI Ingreso:
  - Si receptor.zip ∈ rango cp_from..cp_to → TasaOCuota=0.000000
  - Si receptor.zip ∉ ningún rango → tasa normal 0.160000

Catálogo GLOBAL — SIN company_id (aplica a todas las empresas del SaaS).
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TmsSatZonaEspecial(models.Model):
    """
    Catálogo de rangos de CPs que pertenecen a Zonas Económicas Especiales.
    Cada registro define un rango de CPs con tasa de IVA especial (0% en ZEDE).
    """
    _name        = 'tms.sat.zona.especial'
    _description = 'Zonas Económicas Especiales SAT (ZEDE)'
    _order       = 'cp_from'
    _rec_name    = 'name'

    name = fields.Char(
        string='Nombre Zona',
        required=True,
        help='Nombre descriptivo de la zona especial (ej: Istmo de Tehuantepec - Oaxaca)'
    )
    cp_from = fields.Char(
        string='CP Inicio',
        size=5,
        required=True,
        help='Primer CP del rango de la zona especial'
    )
    cp_to = fields.Char(
        string='CP Fin',
        size=5,
        required=True,
        help='Último CP del rango de la zona especial'
    )
    tasa_iva = fields.Float(
        string='Tasa IVA',
        default=0.0,
        digits=(6, 6),
        help='Tasa IVA aplicable en esta zona. 0.0 para ZEDE. 0.16 para tasa normal.'
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Desactivar si el decreto fue derogado'
    )

    @api.constrains('cp_from', 'cp_to')
    def _check_cp_range(self):
        """Valida que el CP de inicio sea menor o igual al CP de fin."""
        for rec in self:
            if rec.cp_from and rec.cp_to:
                if rec.cp_from > rec.cp_to:
                    raise ValidationError(
                        'El CP de inicio (%s) debe ser menor o igual al CP de fin (%s).'
                        % (rec.cp_from, rec.cp_to)
                    )
            if rec.cp_from and len(rec.cp_from) != 5:
                raise ValidationError('El CP de inicio debe tener exactamente 5 dígitos.')
            if rec.cp_to and len(rec.cp_to) != 5:
                raise ValidationError('El CP de fin debe tener exactamente 5 dígitos.')

    @api.model
    def es_zona_especial(self, cp):
        """
        Verifica si un CP pertenece a alguna ZEDE activa.

        Uso en xml_builder:
            tasa = self.env['tms.sat.zona.especial'].es_zona_especial(partner.zip)

        Args:
            cp (str): Código Postal del receptor a verificar.

        Returns:
            bool: True si el CP cae dentro de algún rango ZEDE activo.
        """
        if not cp:
            return False
        zona = self.search([
            ('cp_from', '<=', cp),
            ('cp_to',   '>=', cp),
            ('active',  '=',  True),
        ], limit=1)
        return bool(zona)
