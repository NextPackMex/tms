# -*- coding: utf-8 -*-
from odoo import api, models, fields


class TmsSatTipoRelacion(models.Model):
    """Catálogo SAT c_TipoRelacion — Tipos de relación entre CFDI (CFDI 4.0).

    Modelo global: sin company_id, compartido entre todas las empresas.
    Utilizado en CfdiRelacionados cuando un CFDI sustituye o relaciona a otro.
    Requerido para el proceso de cancelación motivo 01 (sustitución).
    """

    _name = 'tms.sat.tipo.relacion'
    _description = 'Catálogo SAT — Tipo de Relación c_TipoRelacion'
    _order = 'code'
    # SIN company_id — catálogo global compartido entre empresas

    code = fields.Char(
        string='Código SAT',
        size=2,
        required=True,
        index=True,
        help='Código numérico del SAT (ej. 04 = Sustitución de CFDI previos)'
    )
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción oficial del SAT'
    )
    full_name = fields.Char(
        string='Tipo de Relación',
        compute='_compute_full_name',
        store=True,
        help='Código + descripción para mostrar en selectores'
    )

    _rec_name = 'full_name'
    _rec_names_search = ['code', 'name', 'full_name']

    @api.depends('code', 'name')
    def _compute_full_name(self):
        """Genera la etiqueta completa para los selectores.

        Formato: '04 - Sustitución de los CFDI previos'
        Permite identificar el tipo de relación por código y descripción.
        """
        for rec in self:
            rec.full_name = '%s - %s' % (rec.code, rec.name) if rec.code else rec.name
