# -*- coding: utf-8 -*-
"""
Wizard de validación previa al timbrado de Carta Porte 3.1 (V2.2.2).

Ejecuta 14 checks antes de abrir el flujo de timbrado, mostrando al usuario
exactamente qué datos están correctos (✅) y cuáles necesita corregir (❌).

En ambiente PRUEBAS, los checks de RFC emisor/receptor/chofer y régimen fiscal
son informativos — el xml_builder los sustituye automáticamente por datos de
prueba del SAT. Solo los checks de CSD, mercancías, vehículo y ubicaciones
son bloqueantes en ambos ambientes.
"""
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TmsStampValidationWizard(models.TransientModel):
    """
    Wizard de pre-validación antes de timbrar una Carta Porte 3.1.
    Se crea con create_for_waybill() y se muestra en diálogo modal.
    El usuario revisa los resultados y confirma o cancela el timbrado.
    """
    _name = 'tms.stamp.validation.wizard'
    _description = 'Validación previa al timbrado de Carta Porte'

    waybill_id = fields.Many2one(
        'tms.waybill',
        string='Viaje',
        required=True,
        ondelete='cascade',
    )
    ambiente = fields.Char(
        string='Ambiente',
        readonly=True,
        help='PRUEBAS o PRODUCCION según la configuración del PAC en la empresa.',
    )

    # ── Sección: Empresa Emisora ──────────────────────────────────────
    val_emisor_rfc = fields.Boolean(
        string='RFC Emisor configurado',
        help='La empresa emisora tiene RFC (company.vat). '
             'En PRUEBAS se sustituye por el RFC del certificado de pruebas.',
    )
    val_emisor_regimen = fields.Boolean(
        string='Régimen Fiscal configurado',
        help='La empresa tiene régimen fiscal SAT (tms_regimen_fiscal_id). '
             'En PRUEBAS se usa "616 Sin obligaciones fiscales".',
    )
    val_emisor_cp = fields.Boolean(
        string='Código Postal emisor configurado',
        help='La empresa tiene CP (company.zip). '
             'En PRUEBAS se usa el CP del certificado dev33 (44970).',
    )
    val_emisor_cer = fields.Boolean(
        string='Certificado CSD (.cer) cargado',
        help='Se requiere el archivo .cer del CSD en Ajustes → TMS → Certificados.',
    )
    val_emisor_key = fields.Boolean(
        string='Llave privada CSD (.key) cargada',
        help='Se requiere el archivo .key del CSD en Ajustes → TMS → Certificados.',
    )

    # ── Sección: Receptor ────────────────────────────────────────────
    val_receptor_rfc = fields.Boolean(
        string='RFC Receptor configurado',
        help='El cliente de facturación tiene RFC (partner_invoice_id.vat). '
             'En PRUEBAS se sustituye por EKU9003173C9.',
    )
    val_receptor_cp = fields.Boolean(
        string='Código Postal receptor configurado',
        help='El cliente de facturación tiene CP (partner_invoice_id.zip).',
    )

    # ── Sección: Mercancías ──────────────────────────────────────────
    val_mercancias = fields.Boolean(
        string='Mercancías con Clave SAT',
        help='El waybill tiene al menos una línea y todas tienen Clave SAT asignada.',
    )
    val_mercancias_detalle = fields.Text(
        string='Detalle de mercancías sin clave SAT',
    )

    # ── Sección: Vehículo ────────────────────────────────────────────
    val_vehiculo_placa = fields.Boolean(
        string='Placa del vehículo configurada',
        help='El vehículo asignado tiene número de placa (license_plate).',
    )
    val_vehiculo_permiso = fields.Boolean(
        string='Permiso SCT del vehículo configurado',
        help='El vehículo tiene tipo y número de permiso SCT (sat_permiso_sct_id + permiso_sct_number).',
    )
    val_vehiculo_config = fields.Boolean(
        string='Configuración vehicular SAT asignada',
        help='El vehículo tiene configuración SAT de autotransporte (sat_config_id).',
    )

    # ── Sección: Chofer ──────────────────────────────────────────────
    val_chofer_rfc = fields.Boolean(
        string='RFC del chofer configurado',
        help='El chofer tiene RFC (tms_rfc). '
             'En PRUEBAS se sustituye por CACX7605101P8.',
    )
    val_chofer_licencia = fields.Boolean(
        string='Número de licencia del chofer configurado',
        help='El chofer tiene número de licencia federal (tms_driver_license).',
    )

    # ── Sección: Ubicaciones ─────────────────────────────────────────
    val_ubicaciones = fields.Boolean(
        string='Ubicaciones con CP y socio asignados',
        help='El viaje tiene CP y socio de origen y destino (origin_zip, dest_zip, '
             'partner_origin_id, partner_dest_id).',
    )
    val_ubicaciones_detalle = fields.Text(
        string='Detalle de ubicaciones incompletas',
    )

    # ── Estado general ───────────────────────────────────────────────
    puede_timbrar = fields.Boolean(
        string='¿Puede timbrar?',
        compute='_compute_puede_timbrar',
        store=False,
        help='True si todos los checks bloqueantes están en verde. '
             'En PRUEBAS, los checks de RFC y régimen son informativos, no bloqueantes.',
    )

    # ─────────────────────────────────────────────────────────────────
    # Cómputo del resultado final
    # ─────────────────────────────────────────────────────────────────

    @api.depends(
        'ambiente',
        'val_emisor_cer', 'val_emisor_key',
        'val_emisor_rfc', 'val_emisor_regimen', 'val_emisor_cp',
        'val_receptor_rfc', 'val_receptor_cp',
        'val_mercancias',
        'val_vehiculo_placa', 'val_vehiculo_permiso', 'val_vehiculo_config',
        'val_chofer_rfc', 'val_chofer_licencia',
        'val_ubicaciones',
    )
    def _compute_puede_timbrar(self):
        """
        Determina si el waybill puede timbrar según los checks realizados.

        Los checks de CSD, mercancías, vehículo, chofer-licencia y ubicaciones
        son siempre bloqueantes (no hay sustitución automática posible).

        En PRUEBAS, los checks de RFC y régimen fiscal son informativos:
        xml_builder los sustituye automáticamente, así que no bloquean el timbrado.

        En PRODUCCION, todos los checks son bloqueantes.
        """
        for rec in self:
            es_pruebas = (rec.ambiente == 'PRUEBAS')

            # Checks siempre bloqueantes (no hay sustitución posible en ningún ambiente)
            checks_criticos = [
                rec.val_emisor_cer,
                rec.val_emisor_key,
                rec.val_mercancias,
                rec.val_vehiculo_placa,
                rec.val_vehiculo_permiso,
                rec.val_vehiculo_config,
                rec.val_chofer_licencia,
                rec.val_ubicaciones,
            ]

            if not es_pruebas:
                # En producción, RFC y régimen también son bloqueantes
                checks_criticos += [
                    rec.val_emisor_rfc,
                    rec.val_emisor_regimen,
                    rec.val_emisor_cp,
                    rec.val_receptor_rfc,
                    rec.val_receptor_cp,
                    rec.val_chofer_rfc,
                ]

            rec.puede_timbrar = all(checks_criticos)

    # ─────────────────────────────────────────────────────────────────
    # Creación automática con todos los checks ejecutados
    # ─────────────────────────────────────────────────────────────────

    @api.model
    def create_for_waybill(self, waybill_id):
        """
        Crea el wizard y ejecuta todas las validaciones automáticamente.
        Llamado desde tms.waybill.action_stamp_cfdi() antes de timbrar.

        Verifica 14 puntos de datos agrupados en 6 secciones:
        Empresa Emisora, Receptor, Mercancías, Vehículo, Chofer, Ubicaciones.

        Args:
            waybill_id (int): ID del waybill a validar.

        Returns:
            TmsStampValidationWizard: registro del wizard con todos los campos calculados.
        """
        waybill = self.env['tms.waybill'].browse(waybill_id)
        company = waybill.company_id

        # Detectar ambiente: PRUEBAS o PRODUCCION
        fd_ambiente = (company.fd_ambiente or 'produccion').upper()

        # ── Empresa Emisora ───────────────────────────────────────────
        val_emisor_rfc     = bool(company.vat)
        val_emisor_regimen = bool(company.tms_regimen_fiscal_id)
        val_emisor_cp      = bool(company.zip)
        # CSD: verificar los campos Binary directamente en res.company
        val_emisor_cer = bool(company.tms_csd_cer)
        val_emisor_key = bool(company.tms_csd_key)

        # ── Receptor ─────────────────────────────────────────────────
        receptor      = waybill.partner_invoice_id
        val_receptor_rfc = bool(receptor and receptor.vat)
        val_receptor_cp  = bool(receptor and receptor.zip)

        # ── Mercancías ────────────────────────────────────────────────
        lineas_sin_clave = waybill.line_ids.filtered(lambda l: not l.product_sat_id)
        val_mercancias   = bool(waybill.line_ids) and not bool(lineas_sin_clave)
        detalle_mercancias = ''
        if lineas_sin_clave:
            nombres = ', '.join(
                l.description or (l.product_id.name if l.product_id else str(l.id))
                for l in lineas_sin_clave
            )
            detalle_mercancias = 'Sin Clave SAT: %s' % nombres
        elif not waybill.line_ids:
            detalle_mercancias = 'El waybill no tiene líneas de mercancía.'

        # ── Vehículo ──────────────────────────────────────────────────
        vehiculo = waybill.vehicle_id
        # sat_permiso_sct_id: tipo de permiso SAT; permiso_sct_number: número SCT
        val_vehiculo_placa   = bool(vehiculo and vehiculo.license_plate)
        val_vehiculo_permiso = bool(
            vehiculo and vehiculo.sat_permiso_sct_id and vehiculo.permiso_sct_number
        )
        # sat_config_id: configuración vehicular SAT (C2, T3-S2, etc.)
        val_vehiculo_config  = bool(vehiculo and vehiculo.sat_config_id)

        # ── Chofer ────────────────────────────────────────────────────
        chofer = waybill.driver_id
        # tms_rfc: RFC del chofer (campo en hr.employee)
        val_chofer_rfc      = bool(chofer and chofer.tms_rfc)
        # tms_driver_license: número de licencia federal (campo en hr.employee)
        val_chofer_licencia = bool(chofer and chofer.tms_driver_license)

        # ── Ubicaciones ───────────────────────────────────────────────
        # No hay modelo separado ubicacion_ids — el waybill usa campos directos
        falta_origen  = not (waybill.origin_zip and waybill.partner_origin_id)
        falta_destino = not (waybill.dest_zip and waybill.partner_dest_id)
        val_ubicaciones = not falta_origen and not falta_destino
        detalle_ubicaciones = ''
        if falta_origen:
            detalle_ubicaciones += 'Origen: falta CP o socio. '
        if falta_destino:
            detalle_ubicaciones += 'Destino: falta CP o socio.'

        vals = {
            'waybill_id':              waybill_id,
            'ambiente':                fd_ambiente,
            'val_emisor_rfc':          val_emisor_rfc,
            'val_emisor_regimen':      val_emisor_regimen,
            'val_emisor_cp':           val_emisor_cp,
            'val_emisor_cer':          val_emisor_cer,
            'val_emisor_key':          val_emisor_key,
            'val_receptor_rfc':        val_receptor_rfc,
            'val_receptor_cp':         val_receptor_cp,
            'val_mercancias':          val_mercancias,
            'val_mercancias_detalle':  detalle_mercancias,
            'val_vehiculo_placa':      val_vehiculo_placa,
            'val_vehiculo_permiso':    val_vehiculo_permiso,
            'val_vehiculo_config':     val_vehiculo_config,
            'val_chofer_rfc':          val_chofer_rfc,
            'val_chofer_licencia':     val_chofer_licencia,
            'val_ubicaciones':         val_ubicaciones,
            'val_ubicaciones_detalle': detalle_ubicaciones,
        }

        _logger.info(
            'Wizard validación timbrado creado para waybill %s — ambiente %s — puede_timbrar (pendiente compute)',
            waybill.name, fd_ambiente,
        )
        return self.create(vals)

    # ─────────────────────────────────────────────────────────────────
    # Acción: confirmar timbrado
    # ─────────────────────────────────────────────────────────────────

    def action_confirmar_timbrado(self):
        """
        El usuario revisó las validaciones y confirma el timbrado.
        Solo ejecutable si puede_timbrar=True (todos los checks críticos en verde).

        Delega al método real action_do_stamp_cfdi() del waybill.
        """
        self.ensure_one()
        if not self.puede_timbrar:
            raise UserError(
                'Corrige los datos marcados en rojo (❌) antes de timbrar.\n'
                'Guarda los cambios en la Empresa, Vehículo o Chofer y vuelve a intentarlo.'
            )
        return self.waybill_id.action_do_stamp_cfdi()
