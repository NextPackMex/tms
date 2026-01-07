# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ============================================================
    # CARTA PORTE 3.1 - OPERADOR (FiguraTransporte: 01)
    # ============================================================

    tms_is_driver = fields.Boolean(
        string='Es Chofer (Operador)',
        help='Marcar si este empleado es un operador para Carta Porte.',
        tracking=True
    )

    tms_driver_license = fields.Char(
        string='No. Licencia Federal',
        help='Número de Licencia para Carta Porte (NumLicencia).',
        tracking=True
    )

    tms_driver_license_type = fields.Selection(
        selection=[
            ('A', 'Tipo A - Pasajeros y Turismo'),
            ('B', 'Tipo B - Carga General y Privada'),
            ('C', 'Tipo C - Carga 2 o 3 Ejes'),
            ('D', 'Tipo D - Chofer Guía'),
            ('E', 'Tipo E - Materiales Peligrosos'),
            ('F', 'Tipo F - Aeropuertos y Puertos'),
        ],
        string='Tipo de Licencia',
        help='Tipo de Licencia Federal (SCT) para Carta Porte.',
        tracking=True
    )

    tms_driver_license_expiration = fields.Date(
        string='Vigencia Licencia',
        help='Fecha de vencimiento de la licencia.',
        tracking=True
    )

    # Requerido para Carta Porte 3.1 (Figura de Transporte)
    l10n_mx_edi_fiscal_regime = fields.Selection(
        selection=[
            ('601', 'General de Ley Personas Morales'),
            ('603', 'Personas Morales con Fines no Lucrativos'),
            ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
            ('606', 'Arrendamiento'),
            ('607', 'Régimen de Enajenación o Adquisición de Bienes'),
            ('608', 'Demás ingresos'),
            ('610', 'Residentes en el Extranjero sin Establecimiento Permanente en México'),
            ('611', 'Ingresos por Dividendos (socios y accionistas)'),
            ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
            ('614', 'Ingresos por intereses'),
            ('615', 'Régimen de los ingresos por obtención de premios'),
            ('616', 'Sin obligaciones fiscales'),
            ('620', 'Sociedades Cooperativas de Producción que optan por diferir sus ingresos'),
            ('621', 'Incorporación Fiscal'),
            ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
            ('623', 'Opcional para Grupos de Sociedades'),
            ('624', 'Coordinados'),
            ('625', 'Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas'),
            ('626', 'Régimen Simplificado de Confianza'),
        ],
        string='Régimen Fiscal (Chofer)',
        help='Régimen fiscal del operador según catálogo del SAT.'
    )

    # ============================================================
    # CAMPOS RELACIONADOS (RFC y Domicilio desde el Partner)
    # ============================================================
    # Carta Porte exige RFC y Domicilio Fiscal del Operador.
    # En Odoo 18, usamos "work_contact_id" (Partner vinculado).

    tms_driver_rfc = fields.Char(
        string='RFC Operador',
        related='work_contact_id.vat',
        readonly=True,
        help='RFC tomado del Contacto vinculado (work_contact_id).'
    )

    tms_driver_address = fields.Char(
        string='Domicilio Fiscal',
        compute='_compute_tms_driver_address',
        help='Domicilio formateado tomado del Contacto vinculado.'
    )

    @api.depends('work_contact_id', 'work_contact_id.street', 'work_contact_id.zip', 'work_contact_id.city')
    def _compute_tms_driver_address(self):
        for rec in self:
            if rec.work_contact_id:
                parts = [
                    rec.work_contact_id.street or '',
                    rec.work_contact_id.city or '',
                    rec.work_contact_id.state_id.code or '',
                    rec.work_contact_id.zip or ''
                ]
                rec.tms_driver_address = ", ".join(filter(None, parts))
            else:
                rec.tms_driver_address = False

    def validate_carta_porte_compliance(self):
        """
        Valida que el chofer (operador) cumpla con los requisitos para Carta Porte 3.1.
        Retorna una lista de errores (strings) si falta algo.
        """
        self.ensure_one()
        errors = []
        prefix = f"Chofer {self.name}:"

        if not self.work_contact_id:
            errors.append(f"{prefix} No tiene Contacto vinculado (work_contact_id). Es necesario para obtener RFC y domicilio fiscal.")
            return errors # No podemos seguir validando sin contact

        if not self.tms_driver_rfc:
            errors.append(f"{prefix} Falta el RFC (vat) en el contacto vinculado.")
        
        if not self.tms_driver_license:
            errors.append(f"{prefix} Falta el Número de Licencia (NumLicencia).")

        # Tipo de Licencia es teóricamente opcional en XSD si no se especifica, pero 
        # para Carta Porte SIEMPRE se pide permiso y licencia. Lo hacemos obligatorio para consistencia.
        if not self.tms_driver_license_type:
            errors.append(f"{prefix} Falta el Tipo de Licencia.")

        if not self.l10n_mx_edi_fiscal_regime:
             errors.append(f"{prefix} Falta el Régimen Fiscal de la figura de transporte.")

        # Domicilio Fiscal (CP)
        if not self.work_contact_id.zip:
             errors.append(f"{prefix} Falta el Código Postal (Domicilio) en el contacto vinculado.")

        return errors
