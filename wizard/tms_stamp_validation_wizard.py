# -*- coding: utf-8 -*-
"""
Wizard de validación previa al timbrado de Carta Porte 3.1 (V2.2.2 / Fix-3).

Ejecuta 20 checks antes de abrir el flujo de timbrado, mostrando al usuario
exactamente qué datos están correctos (✅) y cuáles necesita corregir (❌).

En ambiente PRUEBAS, los checks de RFC emisor/receptor/chofer y régimen fiscal
del emisor son informativos — el xml_builder los sustituye automáticamente por
datos de prueba del SAT. El resto de checks son bloqueantes en ambos ambientes.

Fix-3: Se migran aquí los 5 checks que estaban en action_approve_cp / action_confirm_order:
  - val_receptor_regimen: Régimen fiscal del receptor (cliente)
  - val_receptor_uso_cfdi: Uso CFDI del receptor
  - val_distancia: Ruta calculada (distance_km > 0)
  - val_uom_sat: Unidad de medida SAT por línea de mercancía
  - val_material_peligroso: Material peligroso con tipo y embalaje completos
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

    # ── Sección: Receptor extendido (Fix-3) ──────────────────────
    val_receptor_regimen = fields.Boolean(
        string='Régimen Fiscal receptor',
        help='El cliente de facturación tiene régimen fiscal SAT (l10n_mx_edi_fiscal_regime). '
             'Obligatorio para CFDI 4.0.',
    )
    val_receptor_uso_cfdi = fields.Boolean(
        string='Uso CFDI receptor',
        help='El cliente de facturación tiene uso de CFDI asignado (l10n_mx_edi_usage). '
             'Obligatorio para CFDI 4.0.',
    )

    # ── Sección: Ruta (Fix-3) ────────────────────────────────────
    val_distancia = fields.Boolean(
        string='Ruta calculada',
        help='El viaje tiene distancia calculada mayor a 0 km (distance_km > 0). '
             'Se calcula al ingresar los CPs en el wizard de cotización.',
    )

    # ── Sección: Mercancías ──────────────────────────────────────────
    val_mercancias = fields.Boolean(
        string='Mercancías con Clave SAT',
        help='El waybill tiene al menos una línea y todas tienen Clave SAT asignada.',
    )
    val_mercancias_detalle = fields.Text(
        string='Detalle de mercancías sin clave SAT',
    )
    val_uom_sat = fields.Boolean(
        string='Unidad de medida SAT',
        help='Todas las líneas de mercancía tienen Clave de Unidad SAT (uom_sat_id). '
             'Obligatorio para el nodo Mercancías del Complemento Carta Porte.',
    )
    val_material_peligroso = fields.Boolean(
        string='Material peligroso completo',
        help='Las líneas marcadas como material peligroso tienen tipo y embalaje asignados. '
             'Si no hay líneas peligrosas, este check es True automáticamente.',
    )
    val_material_peligroso_detalle = fields.Text(
        string='Detalle material peligroso incompleto',
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
        'val_receptor_regimen', 'val_receptor_uso_cfdi',
        'val_distancia',
        'val_mercancias', 'val_uom_sat', 'val_material_peligroso',
        'val_vehiculo_placa', 'val_vehiculo_permiso', 'val_vehiculo_config',
        'val_chofer_rfc', 'val_chofer_licencia',
        'val_ubicaciones',
    )
    def _compute_puede_timbrar(self):
        """
        Determina si el waybill puede timbrar según los 20 checks realizados.

        Los checks de CSD, mercancías, vehículo, chofer-licencia, ubicaciones,
        receptor extendido, distancia y material peligroso son SIEMPRE bloqueantes.

        En PRUEBAS, los checks de RFC emisor/receptor/chofer y régimen del emisor
        son informativos: xml_builder los sustituye automáticamente.

        En PRODUCCION, todos los checks son bloqueantes.

        Fix-3: Se agregan val_receptor_regimen, val_receptor_uso_cfdi, val_distancia,
        val_uom_sat y val_material_peligroso como checks siempre bloqueantes.
        """
        for rec in self:
            es_pruebas = (rec.ambiente == 'PRUEBAS')

            # Checks siempre bloqueantes (no hay sustitución posible en ningún ambiente)
            checks_criticos = [
                rec.val_emisor_cer,
                rec.val_emisor_key,
                rec.val_mercancias,
                rec.val_uom_sat,
                rec.val_material_peligroso,
                rec.val_vehiculo_placa,
                rec.val_vehiculo_permiso,
                rec.val_vehiculo_config,
                rec.val_chofer_licencia,
                rec.val_ubicaciones,
                rec.val_receptor_regimen,
                rec.val_receptor_uso_cfdi,
                rec.val_distancia,
            ]

            if not es_pruebas:
                # En producción, RFC y régimen emisor también son bloqueantes
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

        Verifica 20 puntos de datos agrupados en 7 secciones:
        Empresa Emisora, Receptor, Ruta, Mercancías, Vehículo, Chofer, Ubicaciones.

        Fix-3: Se agregan 5 checks migrados desde action_approve_cp /
        action_confirm_order: régimen y uso CFDI del receptor, distancia calculada,
        unidad de medida SAT y material peligroso completo.

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
        receptor         = waybill.partner_invoice_id
        val_receptor_rfc = bool(receptor and receptor.vat)
        val_receptor_cp  = bool(receptor and receptor.zip)

        # ── Receptor extendido (Fix-3) ────────────────────────────────
        # l10n_mx_edi_fiscal_regime: Régimen Fiscal SAT del cliente (obligatorio CFDI 4.0)
        val_receptor_regimen = bool(
            receptor and receptor.l10n_mx_edi_fiscal_regime
        )
        # l10n_mx_edi_usage: Uso CFDI asignado al cliente (obligatorio CFDI 4.0)
        val_receptor_uso_cfdi = bool(
            receptor and receptor.l10n_mx_edi_usage
        )

        # ── Ruta calculada (Fix-3) ────────────────────────────────────
        # distance_km se calcula desde TollGuru al confirmar los CPs en el wizard
        val_distancia = bool(waybill.distance_km and waybill.distance_km > 0)

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

        # ── Unidad de medida SAT por línea (Fix-3) ────────────────────
        # uom_sat_id: Clave Unidad SAT (c_ClaveUnidad), obligatoria en nodo Mercancías CP 3.1
        lineas_sin_uom = waybill.line_ids.filtered(lambda l: not l.uom_sat_id)
        val_uom_sat = not bool(lineas_sin_uom)

        # ── Material peligroso (Fix-3) ────────────────────────────────
        # Solo aplica a líneas marcadas is_dangerous=True.
        # Cada una debe tener material_peligroso_id (tipo) y embalaje_id.
        lineas_peligrosas = waybill.line_ids.filtered(lambda l: l.is_dangerous)
        lineas_peligrosas_incompletas = lineas_peligrosas.filtered(
            lambda l: not l.material_peligroso_id or not l.embalaje_id
        )
        val_material_peligroso = not bool(lineas_peligrosas_incompletas)
        detalle_material_peligroso = ''
        if lineas_peligrosas_incompletas:
            detalle_material_peligroso = (
                'Sin tipo/embalaje: ' +
                ', '.join(
                    l.description or (l.product_id.name if l.product_id else str(l.id))
                    for l in lineas_peligrosas_incompletas
                )
            )

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
            'waybill_id':                    waybill_id,
            'ambiente':                      fd_ambiente,
            'val_emisor_rfc':                val_emisor_rfc,
            'val_emisor_regimen':            val_emisor_regimen,
            'val_emisor_cp':                 val_emisor_cp,
            'val_emisor_cer':                val_emisor_cer,
            'val_emisor_key':                val_emisor_key,
            'val_receptor_rfc':              val_receptor_rfc,
            'val_receptor_cp':               val_receptor_cp,
            'val_receptor_regimen':          val_receptor_regimen,
            'val_receptor_uso_cfdi':         val_receptor_uso_cfdi,
            'val_distancia':                 val_distancia,
            'val_mercancias':                val_mercancias,
            'val_mercancias_detalle':        detalle_mercancias,
            'val_uom_sat':                   val_uom_sat,
            'val_material_peligroso':        val_material_peligroso,
            'val_material_peligroso_detalle': detalle_material_peligroso,
            'val_vehiculo_placa':            val_vehiculo_placa,
            'val_vehiculo_permiso':          val_vehiculo_permiso,
            'val_vehiculo_config':           val_vehiculo_config,
            'val_chofer_rfc':                val_chofer_rfc,
            'val_chofer_licencia':           val_chofer_licencia,
            'val_ubicaciones':               val_ubicaciones,
            'val_ubicaciones_detalle':       detalle_ubicaciones,
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
