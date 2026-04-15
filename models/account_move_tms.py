# -*- coding: utf-8 -*-
"""
Extensión de account.move para el CFDI Ingreso del TMS.

Agrega los campos TMS a la factura nativa de Odoo para soportar:
  - Vínculo N:M con los viajes (tms.waybill) incluidos en la factura
  - Estado del CFDI Ingreso (borrador / timbrada / en_cancelacion / cancelada / sustituida)
  - UUID, XML timbrado, motivo de cancelación y UUID de sustituta
  - Botones de acción: timbrar, corregir (motivo 01), cancelar (motivo 02/03)
  - Liberación automática de waybills al confirmar cancelación SAT (motivos 02/03)

La factura nativa de Odoo sigue funcionando igual para cuentas/líneas contables.
Los campos TMS solo son visibles cuando la factura pertenece al diario TMS.
"""
import base64
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# Importaciones diferidas para evitar dependencia circular en el cargado de módulos
def _get_xml_builder():
    from ..services.xml_builder import CartaPorteXmlBuilder
    return CartaPorteXmlBuilder

def _get_xml_signer():
    from ..services.xml_signer import CfdiSigner
    return CfdiSigner

def _get_pac_manager():
    from ..services.pac_manager import PacManager
    return PacManager


class AccountMoveTms(models.Model):
    """
    Extiende account.move con los campos necesarios para el CFDI Ingreso TMS.
    Solo los campos cuyo nombre empieza con 'tms_' son nuevos — todo lo demás
    es comportamiento nativo de Odoo Contabilidad.
    """
    _inherit = 'account.move'

    # ============================================================
    # CAMPOS TMS — VÍNCULO CON VIAJES
    # ============================================================

    tms_waybill_ids = fields.Many2many(
        'tms.waybill',
        'account_move_tms_waybill_rel',
        'move_id',
        'waybill_id',
        string='Viajes incluidos',
        copy=False,
        help='Viajes (tms.waybill) incluidos en esta factura de flete'
    )

    tms_is_invoice = fields.Boolean(
        string='Es factura TMS',
        compute='_compute_tms_is_invoice',
        store=True,
        help='True cuando el diario de esta factura es el diario TMS configurado en Ajustes'
    )

    # ============================================================
    # CAMPOS TMS — ESTADO Y DATOS DEL CFDI INGRESO
    # ============================================================

    tms_cfdi_status = fields.Selection([
        ('borrador',       'Borrador'),
        ('timbrada',       'Timbrada'),
        ('en_cancelacion', 'En cancelación'),
        ('cancelada',      'Cancelada'),
        ('sustituida',     'Sustituida'),
    ],
        string='Estado CFDI',
        default='borrador',
        copy=False,
        tracking=True,
        help='Estado del CFDI Ingreso ante el SAT'
    )

    tms_cfdi_uuid = fields.Char(
        string='UUID CFDI Ingreso',
        size=36,
        copy=False,
        readonly=True,
        help='Folio fiscal (UUID) obtenido del PAC al timbrar'
    )

    tms_cfdi_xml = fields.Binary(
        string='XML Timbrado',
        copy=False,
        readonly=True,
        attachment=True,
        help='XML del CFDI Ingreso timbrado, firmado por el SAT'
    )

    tms_cfdi_xml_fname = fields.Char(
        string='Nombre XML',
        copy=False,
        help='Nombre del archivo XML para descarga'
    )

    tms_cfdi_fecha = fields.Datetime(
        string='Fecha Timbrado',
        copy=False,
        readonly=True,
        help='Fecha y hora en que el PAC devolvió el XML timbrado'
    )

    tms_cfdi_pac = fields.Char(
        string='PAC Usado',
        copy=False,
        readonly=True,
        help='PAC que timbró el CFDI (formas_digitales o sw_sapien)'
    )

    tms_cfdi_no_cert_sat = fields.Char(
        string='No. Certificado SAT',
        copy=False,
        readonly=True,
        help='Número de certificado SAT del timbre fiscal digital'
    )

    tms_cfdi_error_msg = fields.Text(
        string='Error CFDI',
        copy=False,
        help='Mensaje de error del último intento de timbrado/cancelación'
    )

    tms_cfdi_motivo = fields.Selection([
        ('01', '01 — Errores con relación (requiere sustituta)'),
        ('02', '02 — Errores sin relación'),
        ('03', '03 — Operación no realizada'),
    ],
        string='Motivo Cancelación',
        copy=False,
        help='Motivo SAT de cancelación del CFDI Ingreso'
    )

    tms_cfdi_uuid_sustituta = fields.Char(
        string='UUID Factura Sustituta',
        size=36,
        copy=False,
        readonly=True,
        help='UUID del CFDI que sustituye a este (motivo 01 — errores con relación)'
    )

    tms_id_ccp_ingreso = fields.Char(
        string='IdCCP Ingreso',
        copy=False,
        readonly=True,
        help='IdCCP generado al timbrar el CFDI Ingreso. '
             'Distinto al IdCCP del Traslado — cada tipo de CFDI tiene su propio IdCCP.'
    )

    # ============================================================
    # CÓMPUTOS
    # ============================================================

    @api.depends('journal_id', 'company_id', 'company_id.tms_sales_journal_id')
    def _compute_tms_is_invoice(self):
        """
        Determina si esta factura pertenece al flujo TMS comparando
        su diario con el diario TMS configurado en Ajustes → TMS → Facturación.
        Controla la visibilidad de todos los campos TMS en la vista.
        """
        for rec in self:
            journal_tms = rec.company_id.tms_sales_journal_id
            rec.tms_is_invoice = bool(
                journal_tms and rec.journal_id == journal_tms
            )

    # ============================================================
    # ACCIONES — TIMBRADO CFDI INGRESO
    # ============================================================

    def action_tms_stamp_ingreso(self):
        """
        Timbra el CFDI Ingreso para esta factura TMS.

        Flujo:
          1. Validar que sea factura TMS con viajes vinculados
          2. Validar RFC del receptor vs is_company
          3. Generar IdCCP Ingreso único
          4. Construir XML tipo 'I' con xml_builder
          5. Firmar con CfdiSigner
          6. Enviar al PAC vía pac_manager
          7. Persistir UUID, XML, fecha, estado → 'timbrada'
          8. Pasar waybills vinculados a estado 'closed'
        """
        self.ensure_one()

        # Validaciones previas
        if not self.tms_is_invoice:
            raise UserError(_('Esta factura no pertenece al diario TMS. Configure el diario en Ajustes → TMS.'))
        if not self.tms_waybill_ids:
            raise UserError(_('No hay viajes vinculados a esta factura.'))
        if self.tms_cfdi_status == 'timbrada':
            raise UserError(_('Esta factura ya fue timbrada (UUID: %s).') % self.tms_cfdi_uuid)

        # Validar RFC del receptor
        self._validate_rfc_receptor()

        try:
            # 1. Generar IdCCP fresco para el Ingreso
            from ..models.tms_waybill import _generate_id_ccp
            self.tms_id_ccp_ingreso = _generate_id_ccp()
            _logger.info('IdCCP Ingreso generado: %s (move %s)', self.tms_id_ccp_ingreso, self.name)

            # 2. Construir XML tipo Ingreso
            builder = _get_xml_builder()()
            xml_bytes = builder.build(self, tipo='I')

            # 3. Firmar
            signer = _get_xml_signer()()
            xml_sellado = signer.sign(xml_bytes, self.company_id)

            # 4. Timbrar
            manager = _get_pac_manager()(self.env)
            resultado = manager.timbrar(xml_sellado, self.company_id)

            # 5. Persistir resultado
            uuid         = resultado.get('uuid', '')
            xml_timbrado = resultado.get('xml_timbrado', b'')
            pac_usado    = resultado.get('pac_usado', '')
            fecha_raw    = resultado.get('fecha_timbrado') or resultado.get('fecha', '')
            no_cert_sat  = resultado.get('no_cert_sat', '')

            # Normalizar fecha (el PAC puede devolver formato ISO con T)
            fecha_dt = None
            if fecha_raw:
                fecha_str = str(fecha_raw).replace('T', ' ')
                try:
                    fecha_dt = fields.Datetime.from_string(fecha_str[:19])
                except Exception:
                    fecha_dt = None

            fname = 'CFDI_I_%s_%s.xml' % (self.name.replace('/', '_'), uuid[:8])
            self.write({
                'tms_cfdi_uuid':       uuid,
                'tms_cfdi_xml':        base64.b64encode(xml_timbrado) if xml_timbrado else False,
                'tms_cfdi_xml_fname':  fname,
                'tms_cfdi_fecha':      fecha_dt,
                'tms_cfdi_pac':        pac_usado,
                'tms_cfdi_no_cert_sat': no_cert_sat,
                'tms_cfdi_status':     'timbrada',
                'tms_cfdi_error_msg':  False,
            })

            # 6. Confirmar factura en Odoo (pasar de draft a posted)
            if self.state == 'draft':
                self.action_post()

            # 7. Cerrar waybills vinculados
            self.tms_waybill_ids.write({'state': 'closed'})

            # 8. Log en chatter
            self.message_post(
                body=_(
                    '<b>CFDI Ingreso timbrado</b><br/>'
                    'UUID: %s<br/>PAC: %s<br/>NoCertSAT: %s'
                ) % (uuid, pac_usado, no_cert_sat)
            )
            _logger.info('CFDI Ingreso timbrado exitosamente — UUID: %s (move %s)', uuid, self.name)

        except UserError:
            raise
        except Exception as exc:
            msg = str(exc)
            self.write({
                'tms_cfdi_error_msg': msg,
                'tms_cfdi_status':    'borrador',
            })
            _logger.error('Error timbrando CFDI Ingreso para move %s: %s', self.name, msg)
            raise UserError(
                _('Error al timbrar el CFDI Ingreso:\n%s') % msg
            )

    # ============================================================
    # ACCIONES — CANCELACIÓN CFDI INGRESO
    # ============================================================

    def action_tms_open_cancel_wizard(self):
        """
        Abre el wizard de cancelación de CFDI Ingreso.
        El wizard permite seleccionar el motivo y, en motivo 01, validar que
        exista una factura sustituta timbrada antes de proceder.
        """
        self.ensure_one()
        if self.tms_cfdi_status != 'timbrada':
            raise UserError(_('Solo se puede cancelar una factura con estado "Timbrada".'))
        return {
            'type':      'ir.actions.act_window',
            'name':      _('Cancelar CFDI Ingreso'),
            'res_model': 'tms.cancel.invoice.wizard',
            'view_mode': 'form',
            'target':    'new',
            'context':   {'default_move_id': self.id},
        }

    def action_tms_confirm_cancellation(self, motivo, uuid_sustituta=None):
        """
        Confirma la cancelación del CFDI Ingreso ante el SAT.
        Llamado desde el wizard de cancelación tras la respuesta del PAC.

        Reglas de liberación de waybills:
          - Motivo 01: waybills SIGUEN en 'closed' (la sustituta cubre el cobro)
          - Motivo 02/03: waybills regresan a 'arrived' con invoice_status='no_invoice'

        Args:
            motivo (str): '01', '02' o '03'
            uuid_sustituta (str|None): UUID de la factura sustituta (solo motivo 01)
        """
        self.ensure_one()

        vals = {
            'tms_cfdi_motivo':  motivo,
            'tms_cfdi_status':  'cancelada',
        }
        if motivo == '01' and uuid_sustituta:
            vals['tms_cfdi_uuid_sustituta'] = uuid_sustituta
            vals['tms_cfdi_status'] = 'sustituida'

        self.write(vals)

        # Liberar waybills solo en motivos 02 y 03
        if motivo in ('02', '03'):
            self.tms_waybill_ids.action_release_from_invoice()

        self.message_post(
            body=_(
                '<b>CFDI Ingreso cancelado</b><br/>'
                'Motivo: %s<br/>'
                '%s'
            ) % (
                motivo,
                ('UUID sustituta: %s' % uuid_sustituta) if uuid_sustituta else 'Sin sustituta'
            )
        )
        _logger.info(
            'CFDI Ingreso cancelado — move %s, motivo %s, sustituta %s',
            self.name, motivo, uuid_sustituta or 'N/A'
        )

    def action_tms_reopen_invoice_wizard(self):
        """
        Botón "Volver a facturar" en facturas canceladas con motivo 02/03.
        Abre el wizard de facturación pre-llenado con los mismos viajes.
        Solo disponible cuando tms_cfdi_status='cancelada' (no 'sustituida').
        """
        self.ensure_one()
        if self.tms_cfdi_status not in ('cancelada',):
            raise UserError(_('Solo facturas canceladas (motivo 02/03) pueden refacturarse.'))
        waybill_ids = self.tms_waybill_ids.ids
        return {
            'type':      'ir.actions.act_window',
            'name':      _('Nueva Factura — Mismos Viajes'),
            'res_model': 'tms.invoice.wizard',
            'view_mode': 'form',
            'target':    'new',
            'context':   {
                'default_partner_id':   self.partner_id.id,
                'default_waybill_ids':  [(6, 0, waybill_ids)],
                'default_modo':         'consolidado' if len(waybill_ids) > 1 else 'simple',
            },
        }

    # ============================================================
    # VALIDACIONES
    # ============================================================

    def _validate_rfc_receptor(self):
        """
        Valida que la longitud del RFC del receptor sea consistente con is_company.
        Persona Moral (is_company=True): RFC de 12 caracteres
        Persona Física (is_company=False): RFC de 13 caracteres

        Lanza UserError antes de llamar al PAC para dar un mensaje claro al usuario.
        """
        partner = self.partner_id
        if not partner:
            raise UserError(_('La factura no tiene cliente asignado.'))
        rfc = (partner.vat or '').strip().upper()
        if not rfc:
            raise UserError(
                _('El cliente %s no tiene RFC configurado.') % partner.name
            )
        if partner.is_company and len(rfc) != 12:
            raise UserError(
                _('El RFC "%s" del cliente "%s" tiene %d caracteres. '
                  'Las Personas Morales deben tener RFC de 12 caracteres.')
                % (rfc, partner.name, len(rfc))
            )
        if not partner.is_company and len(rfc) != 13:
            raise UserError(
                _('El RFC "%s" del cliente "%s" tiene %d caracteres. '
                  'Las Personas Físicas deben tener RFC de 13 caracteres.')
                % (rfc, partner.name, len(rfc))
            )

    # ============================================================
    # HELPERS PARA REPORTE PDF — CFDI INGRESO
    # ============================================================

    def _parse_tms_cfdi_xml(self):
        """
        Parsea el XML timbrado del CFDI Ingreso y retorna un diccionario con
        los campos del Timbre Fiscal Digital para usar en la plantilla QWeb.
        Incluye la cadena original del SAT y los sellos digitales.
        Retorna dict vacío si no hay XML o si ocurre cualquier error.
        """
        self.ensure_one()
        result = {}
        if not self.tms_cfdi_xml:
            return result
        try:
            from lxml import etree
            xml_bytes = base64.b64decode(self.tms_cfdi_xml)
            root = etree.fromstring(xml_bytes)

            ns_cfdi = 'http://www.sat.gob.mx/cfd/4'
            ns_tfd  = 'http://www.sat.gob.mx/TimbreFiscalDigital'

            # Datos del Timbre Fiscal Digital (TFD)
            tfd = root.find('.//{%s}TimbreFiscalDigital' % ns_tfd)
            if tfd is not None:
                result['uuid']            = tfd.get('UUID', '')
                result['fecha_timbrado']  = tfd.get('FechaTimbrado', '')
                result['no_cert_sat']     = tfd.get('NoCertificadoSAT', '')
                result['sello_sat']       = tfd.get('SelloSAT', '')
                result['sello_cfd']       = tfd.get('SelloCFD', '')
                result['rfc_prov_certif'] = tfd.get('RfcProvCertif', '')
                result['no_cert_emisor']  = root.get('NoCertificado', '')
                # Cadena original del TFD (formato SAT)
                result['cadena_original'] = (
                    '||%s|%s|%s|%s|%s||' % (
                        tfd.get('Version', '1.1'),
                        tfd.get('UUID', ''),
                        tfd.get('FechaTimbrado', ''),
                        tfd.get('RfcProvCertif', ''),
                        tfd.get('NoCertificadoSAT', ''),
                    )
                )

            # Datos del Emisor
            emisor = root.find('{%s}Emisor' % ns_cfdi)
            if emisor is not None:
                result['rfc_emisor']     = emisor.get('Rfc', '')
                result['nombre_emisor']  = emisor.get('Nombre', '')
                result['regimen_emisor'] = emisor.get('RegimenFiscal', '')

            # Datos del Receptor
            receptor = root.find('{%s}Receptor' % ns_cfdi)
            if receptor is not None:
                result['rfc_receptor']     = receptor.get('Rfc', '')
                result['nombre_receptor']  = receptor.get('Nombre', '')
                result['uso_cfdi']         = receptor.get('UsoCFDI', '')
                result['dom_fiscal_rec']   = receptor.get('DomicilioFiscalReceptor', '')
                result['regimen_receptor'] = receptor.get('RegimenFiscalReceptor', '')

        except Exception as exc:
            _logger.warning(
                'Error parseando CFDI XML de factura TMS %s: %s', self.name, exc
            )
        return result

    def _get_tms_invoice_qr_image(self):
        """
        Genera la imagen QR del CFDI Ingreso en base64 para incrustar en el PDF.
        La URL apunta al verificador oficial del SAT.
        Retorna cadena vacía si no se puede generar (sin UUID o sin qrcode).
        """
        self.ensure_one()
        if not self.tms_cfdi_uuid:
            return ''
        try:
            import qrcode
            import io

            uuid         = self.tms_cfdi_uuid
            rfc_emisor   = (self.company_id.vat or '').upper()
            rfc_receptor = (self.partner_id.vat or '').upper()
            total        = float(self.amount_total or 0.0)

            # Extraer los últimos 8 caracteres del sello SAT desde el TFD
            sello_fe = ''
            if self.tms_cfdi_xml:
                try:
                    from lxml import etree
                    xml_bytes = base64.b64decode(self.tms_cfdi_xml)
                    root = etree.fromstring(xml_bytes)
                    ns_tfd = 'http://www.sat.gob.mx/TimbreFiscalDigital'
                    tfd_elem = root.find('.//{%s}TimbreFiscalDigital' % ns_tfd)
                    if tfd_elem is not None:
                        sello_fe = (tfd_elem.get('SelloSAT') or '')[-8:]
                except Exception:
                    pass

            # URL verificador SAT — formato oficial (tt con 6 decimales, 17 dígitos totales)
            sat_url = (
                'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx'
                '?id=%s&re=%s&rr=%s&tt=%017.6f&fe=%s'
            ) % (uuid, rfc_emisor, rfc_receptor, total, sello_fe)

            qr = qrcode.QRCode(version=1, box_size=3, border=2)
            qr.add_data(sat_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')

            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')

        except Exception as exc:
            _logger.warning(
                'No se pudo generar QR para factura TMS %s: %s', self.name, exc
            )
            return ''

    def action_print_tms_invoice(self):
        """
        Acción para imprimir el PDF de la Factura TMS (CFDI Ingreso).
        Llamado desde el botón "Imprimir Factura" en la vista de account.move.
        Solo disponible cuando la factura está timbrada.
        """
        self.ensure_one()
        return self.env.ref('tms.action_report_tms_invoice').report_action(self)
