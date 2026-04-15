# -*- coding: utf-8 -*-
"""
Construcción del XML CFDI 4.0 con Complemento Carta Porte 3.1.

Usa lxml para construir el árbol XML con los namespaces correctos del SAT.
NO depende de l10n_mx_edi — implementación propia completa.

Namespaces:
  cfdi:         http://www.sat.gob.mx/cfd/4
  cartaporte31: http://www.sat.gob.mx/CartaPorte31
  xsi:          http://www.w3.org/2001/XMLSchema-instance
"""
import base64
import logging
import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from lxml import etree

from odoo.exceptions import UserError

# Zona horaria oficial del SAT — CFDI debe usar hora del centro de México
_TZ_MEXICO = ZoneInfo('America/Mexico_City')

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de namespace y esquema
# ---------------------------------------------------------------------------
NS_CFDI = 'http://www.sat.gob.mx/cfd/4'
NS_CP31 = 'http://www.sat.gob.mx/CartaPorte31'
NS_XSI  = 'http://www.w3.org/2001/XMLSchema-instance'

SCHEMA_LOCATION = (
    'http://www.sat.gob.mx/cfd/4 '
    'http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd '
    'http://www.sat.gob.mx/CartaPorte31 '
    'http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd'
)

NSMAP = {
    'cfdi':         NS_CFDI,
    'cartaporte31': NS_CP31,
    'xsi':          NS_XSI,
}


# ---------------------------------------------------------------------------
# Helpers de normalización SAT (module-level — usables sin instanciar la clase)
# ---------------------------------------------------------------------------

def _normalize_placa(placa):
    """Normaliza placa vehicular para SAT.
    Quita guiones, espacios y caracteres no alfanuméricos; convierte a mayúsculas.
    SAT acepta entre 5 y 7 caracteres alfanuméricos en PlacaVM/Placa.
    """
    if not placa:
        return ''
    return re.sub(r'[^A-Za-z0-9]', '', placa).upper()[:7]


def _normalize_rfc(rfc):
    """Normaliza RFC para SAT.
    Quita espacios, guiones y caracteres no alfanuméricos; convierte a mayúsculas.
    Persona física: 13 chars, Persona moral: 12 chars.
    """
    if not rfc:
        return ''
    return re.sub(r'[^A-Za-z0-9]', '', rfc).upper()


def _normalize_date_iso(dt):
    """Asegura formato ISO 8601 sin microsegundos para SAT.
    Formato correcto: 2026-03-19T14:30:00
    Acepta datetime objects o strings; elimina fracción de segundos si existe.
    """
    if not dt:
        return ''
    if hasattr(dt, 'strftime'):
        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    # Si ya es string, eliminar microsegundos
    s = str(dt)
    if '.' in s:
        s = s.split('.')[0]
    return s


def _normalize_sat_code(code):
    """Limpia código de catálogo SAT (PermSCT, ConfigVehicular, ClaveUnidad, etc).
    Elimina espacios al inicio y final para evitar rechazos por whitespace.
    """
    if not code:
        return ''
    return str(code).strip()


def _normalize_id_ubicacion(tipo, numero):
    """Genera IDUbicacion con formato SAT.
    Origen: OR + 6 dígitos (OR000001)
    Destino: DE + 6 dígitos (DE000001)
    """
    prefix = 'OR' if tipo == 'Origen' else 'DE'
    return '%s%06d' % (prefix, numero)


class CartaPorteXmlBuilder:
    """
    Construye el XML CFDI 4.0 con Complemento Carta Porte 3.1.

    Soporta dos tipos de CFDI:
      - tipo='T' (Traslado): Carta Porte para circular en ruta. El origen es tms.waybill.
      - tipo='I' (Ingreso):  Factura de flete con CP 3.1. El origen es account.move con
                              tms_waybill_ids vinculados. SAT obliga complemento CP en
                              facturas de transportistas.

    Uso:
        builder = CartaPorteXmlBuilder()
        # Traslado (Carta Porte):
        xml_bytes = builder.build(waybill, tipo='T')
        # Ingreso (Factura de flete):
        xml_bytes = builder.build(account_move, tipo='I')
        # Pasar xml_bytes a CfdiSigner.sign()
    """

    def build(self, waybill_or_move, tipo='T'):
        """
        Punto de entrada principal. Despacha al builder correcto según tipo.

        Args:
            waybill_or_move: tms.waybill (tipo='T') o account.move (tipo='I')
            tipo (str): 'T' para Traslado, 'I' para Ingreso. Default='T'.

        Returns:
            bytes: XML serializado, listo para firmar con CfdiSigner.

        Mantiene compatibilidad hacia atrás — llamadas existentes sin tipo='T'
        siguen funcionando exactamente igual.
        """
        if tipo == 'T':
            return self._build_traslado(waybill_or_move)
        elif tipo == 'I':
            return self._build_ingreso(waybill_or_move)
        else:
            raise ValueError('tipo debe ser "T" (Traslado) o "I" (Ingreso). Recibido: %r' % tipo)

    # ------------------------------------------------------------------
    # CFDI Traslado (tipo='T') — lógica original sin cambios
    # ------------------------------------------------------------------

    def _build_traslado(self, waybill):
        """
        Construye el XML CFDI Traslado (Carta Porte) sin sellar.
        Lógica original — no modificar.

        Args:
            waybill: registro tms.waybill con todos los datos

        Returns:
            bytes: XML serializado, listo para firmar con CfdiSigner
        """
        _logger.info('Construyendo XML CFDI 4.0 Traslado para waybill %s', waybill.name)

        company = waybill.company_id
        # Validar campos requeridos antes de construir el XML
        # company se pasa para relajar validaciones que el PAC sustituye en pruebas
        self._validate_required_fields(waybill, company)

        # Resolver datos fiscales según ambiente (pruebas vs producción)
        datos = self._get_datos_fiscales(company, waybill)

        # Advertencia explícita cuando se sustituyen datos fiscales en pruebas
        if company.fd_ambiente == 'pruebas':
            _logger.warning(
                'AMBIENTE PRUEBAS — Sustituyendo datos fiscales genéricos para timbrado. '
                'RFC Emisor: %s → %s, RFC Receptor: %s → %s',
                (company.vat or ''), datos['rfc_emisor'],
                (company.partner_id.vat or ''), datos['rfc_receptor'],
            )

        # Nodo raíz con namespaces
        comprobante = self._build_comprobante(waybill, datos)

        # Subnodos obligatorios CFDI 4.0
        comprobante.append(self._build_emisor(company, datos))
        comprobante.append(self._build_receptor(waybill, datos))
        comprobante.append(self._build_conceptos(waybill))
        # cfdi:Impuestos está PROHIBIDO para TipoDeComprobante="T" (Traslado)
        # CFDI40201: "Cuando TipoDeComprobante sea T o P, Impuestos no debe existir"

        # Complemento Carta Porte 3.1
        complemento = etree.SubElement(
            comprobante, etree.QName(NS_CFDI, 'Complemento'))
        complemento.append(self._build_complemento_carta_porte(waybill, datos))

        xml_bytes = etree.tostring(
            comprobante,
            xml_declaration=True,
            encoding='UTF-8',
            pretty_print=False,
        )
        _logger.warning(
            'XML COMPLETO Traslado generado (sin sellar):\n%s',
            etree.tostring(comprobante, pretty_print=True, encoding='unicode'),
        )
        return xml_bytes

    # ------------------------------------------------------------------
    # CFDI Ingreso (tipo='I') — nuevo en V2.3
    # ------------------------------------------------------------------

    def _build_ingreso(self, move):
        """
        Construye el XML CFDI Ingreso con Complemento Carta Porte 3.1.

        El SAT obliga a los transportistas a incluir el complemento CP en facturas
        de flete (regla CP.R.1 del Apéndice 10 del instructivo SAT).

        Para facturas consolidadas (N viajes), genera:
          - N pares Ubicacion OR/DE (uno por waybill)
          - Todas las mercancías de todos los waybills
          - El Autotransporte del primer waybill (vehículo principal)
          - N Conceptos CFDI con el monto de cada viaje
          - Impuestos: IVA 16% + Retención 4% condicional

        Args:
            move: account.move con tms_waybill_ids vinculados

        Returns:
            bytes: XML serializado, listo para firmar con CfdiSigner
        """
        _logger.info('Construyendo XML CFDI 4.0 Ingreso para move %s', move.name)

        company = move.company_id
        waybills = move.tms_waybill_ids

        if not waybills:
            raise UserError('La factura %s no tiene viajes vinculados.' % move.name)

        datos = self._get_datos_fiscales_ingreso(company, move)

        if company.fd_ambiente == 'pruebas':
            _logger.warning(
                'AMBIENTE PRUEBAS — Datos fiscales Ingreso sustituidos. RFC Emisor: %s, RFC Receptor: %s',
                datos['rfc_emisor'], datos['rfc_receptor'],
            )

        # Nodo raíz Ingreso
        comprobante = self._build_comprobante_ingreso(move, datos)

        # CfdiRelacionados (solo motivo 01 — corrección de factura)
        uuid_original = getattr(move, 'tms_cfdi_uuid_sustituta', None)
        if uuid_original:
            comprobante.append(self._build_cfdi_relacionados(uuid_original))

        comprobante.append(self._build_emisor(company, datos))
        comprobante.append(self._build_receptor_ingreso(move, datos))
        comprobante.append(self._build_conceptos_ingreso(move, datos))
        comprobante.append(self._build_impuestos_ingreso(move, datos))

        # Complemento Carta Porte 3.1 — obligatorio para transportistas
        complemento = etree.SubElement(
            comprobante, etree.QName(NS_CFDI, 'Complemento'))
        complemento.append(self._build_complemento_carta_porte_ingreso(move, datos))

        xml_bytes = etree.tostring(
            comprobante,
            xml_declaration=True,
            encoding='UTF-8',
            pretty_print=False,
        )
        _logger.warning(
            'XML COMPLETO Ingreso generado (sin sellar):\n%s',
            etree.tostring(comprobante, pretty_print=True, encoding='unicode'),
        )
        return xml_bytes

    def _build_comprobante_ingreso(self, move, datos):
        """
        Construye el nodo raíz cfdi:Comprobante para tipo Ingreso.

        Diferencias vs Traslado:
          - TipoDeComprobante = 'I'
          - SubTotal = suma de amount_untaxed de todos los waybills
          - Total = suma de amount_total de todos los waybills
          - Moneda = 'MXN'
        """
        fecha = datetime.now(_TZ_MEXICO).strftime('%Y-%m-%dT%H:%M:%S')

        subtotal = sum(w.amount_untaxed for w in move.tms_waybill_ids)
        total    = sum(w.amount_total   for w in move.tms_waybill_ids)

        comp = etree.Element(
            etree.QName(NS_CFDI, 'Comprobante'),
            nsmap=NSMAP,
        )
        comp.set(etree.QName(NS_XSI, 'schemaLocation'), SCHEMA_LOCATION)
        comp.set('Version',           '4.0')
        comp.set('Fecha',             fecha)
        comp.set('Sello',             '')          # se rellena al firmar
        comp.set('NoCertificado',     '')          # se rellena al firmar
        comp.set('Certificado',       '')          # se rellena al firmar
        comp.set('SubTotal',          '{:.2f}'.format(subtotal))
        comp.set('Total',             '{:.2f}'.format(total))
        comp.set('Moneda',            'MXN')
        comp.set('TipoDeComprobante', 'I')         # I = Ingreso
        comp.set('MetodoPago',        'PPD')       # PPD = Pago en Parcialidades o Diferido
        comp.set('FormaPago',         '99')        # 99 = Por definir
        comp.set('Exportacion',       '01')        # 01 = No aplica
        comp.set('LugarExpedicion',   datos['lugar_expedicion'])

        return comp

    def _build_receptor_ingreso(self, move, datos):
        """
        Construye cfdi:Receptor para CFDI Ingreso.

        En Ingreso (TipoDeComprobante='I'), el Receptor es el CLIENTE del viaje
        (partner_id de la factura), no la empresa emisora como en el Traslado.
        UsoCFDI: G03 (Gastos en General) es el valor default para servicios de flete.
        """
        receptor = etree.Element(etree.QName(NS_CFDI, 'Receptor'))
        receptor.set('Rfc',                     datos['rfc_receptor'])
        receptor.set('Nombre',                  datos['nombre_receptor'])
        receptor.set('DomicilioFiscalReceptor', datos['domicilio_fiscal_receptor'])
        receptor.set('RegimenFiscalReceptor',   datos['regimen_receptor'])
        receptor.set('UsoCFDI',                 datos.get('uso_cfdi', 'G03'))
        return receptor

    def _build_conceptos_ingreso(self, move, datos):
        """
        Construye cfdi:Conceptos para CFDI Ingreso.

        Un Concepto por cada waybill vinculado, con el monto real del flete.
        ClaveProdServ: 78101800 (Servicios de transporte de carga por carretera)
        ClaveUnidad: E48 (Unidad de servicio)
        ObjetoImp: '02' (Sí objeto de impuesto) — a diferencia del Traslado que usa '01'
        """
        conceptos = etree.Element(etree.QName(NS_CFDI, 'Conceptos'))

        for waybill in move.tms_waybill_ids:
            concepto = etree.SubElement(conceptos, etree.QName(NS_CFDI, 'Concepto'))
            concepto.set('ClaveProdServ', '78101800')
            concepto.set('Cantidad',      '1')
            concepto.set('ClaveUnidad',   'E48')
            concepto.set('Descripcion',
                         ('SERVICIO DE FLETE — %s' % (waybill.name or waybill.route_name or 'VIAJE'))[:100])
            concepto.set('ValorUnitario', '{:.2f}'.format(waybill.amount_untaxed))
            concepto.set('Importe',       '{:.2f}'.format(waybill.amount_untaxed))
            concepto.set('ObjetoImp',     '02')  # 02 = Sí objeto de impuesto

        return conceptos

    def _build_impuestos_ingreso(self, move, datos):
        """
        Construye cfdi:Impuestos para CFDI Ingreso.

        Siempre incluye:
          - Traslados: IVA 16% (o 0% si receptor en zona ZEDE)

        Incluye condicionalmente (solo si receptor is_company=True):
          - Retenciones: IVA 4% (Art. 1-A LIVA + Art. 3 RLIVA)

        Estructura del nodo según reglas SAT CFDI 4.0:
          cfdi:Impuestos
            cfdi:Retenciones (solo PM)
              cfdi:Retencion Impuesto="002" Importe="..."
            cfdi:Traslados
              cfdi:Traslado Base="..." Impuesto="002" TipoFactor="Tasa"
                              TasaOCuota="0.160000|0.000000" Importe="..."
        """
        subtotal = sum(w.amount_untaxed for w in move.tms_waybill_ids)
        partner  = move.partner_id
        tasa_iva = self._get_tasa_iva(move)

        iva_importe = round(subtotal * tasa_iva, 2)
        ret_importe = round(subtotal * 0.04, 2) if (partner and partner.is_company) else 0.0

        impuestos = etree.Element(etree.QName(NS_CFDI, 'Impuestos'))

        # Total de impuestos trasladados y retenidos
        impuestos.set('TotalImpuestosRetenidos',  '{:.2f}'.format(ret_importe))
        impuestos.set('TotalImpuestosTrasladados', '{:.2f}'.format(iva_importe))

        # Retenciones (solo personas morales)
        if ret_importe > 0:
            retenciones = etree.SubElement(impuestos, etree.QName(NS_CFDI, 'Retenciones'))
            ret = etree.SubElement(retenciones, etree.QName(NS_CFDI, 'Retencion'))
            ret.set('Impuesto', '002')               # 002 = IVA
            ret.set('Importe',  '{:.2f}'.format(ret_importe))

        # Traslados — IVA
        traslados = etree.SubElement(impuestos, etree.QName(NS_CFDI, 'Traslados'))
        traslado  = etree.SubElement(traslados, etree.QName(NS_CFDI, 'Traslado'))
        traslado.set('Base',         '{:.2f}'.format(subtotal))
        traslado.set('Impuesto',     '002')          # 002 = IVA
        traslado.set('TipoFactor',   'Tasa')
        traslado.set('TasaOCuota',   '{:.6f}'.format(tasa_iva))
        traslado.set('Importe',      '{:.2f}'.format(iva_importe))

        return impuestos

    def _get_tasa_iva(self, move):
        """
        Determina la tasa de IVA para el receptor del account.move.

        Reglas:
          - Si partner.zip está en zona ZEDE activa → tasa 0.0 (IVA 0%)
          - Cualquier otro caso → tasa 0.16 (IVA 16%)

        La verificación ZEDE consulta el catálogo tms.sat.zona.especial
        que es global (sin company_id).

        Args:
            move: account.move con partner_id

        Returns:
            float: 0.0 (ZEDE) o 0.16 (estándar)
        """
        partner = move.partner_id
        if not partner or not partner.zip:
            return 0.16
        es_zede = move.env['tms.sat.zona.especial'].es_zona_especial(partner.zip)
        return 0.0 if es_zede else 0.16

    def _build_cfdi_relacionados(self, uuid_original):
        """
        Construye el nodo cfdi:CfdiRelacionados para sustitución de CFDI (motivo 01).

        SAT exige este nodo cuando se cancela una factura con motivo 01
        (errores con relación) y se emite una sustituta.
        TipoRelacion='04' = Sustitución de los CFDI previos.

        Args:
            uuid_original (str): UUID del CFDI que está siendo sustituido.

        Returns:
            lxml.etree.Element: nodo cfdi:CfdiRelacionados
        """
        cfdi_relacionados = etree.Element(etree.QName(NS_CFDI, 'CfdiRelacionados'))
        cfdi_relacionados.set('TipoRelacion', '04')  # 04 = Sustitución de CFDI previos
        cfdi_rel = etree.SubElement(cfdi_relacionados, etree.QName(NS_CFDI, 'CfdiRelacionado'))
        cfdi_rel.set('Uuid', uuid_original)
        return cfdi_relacionados

    def _build_complemento_carta_porte_ingreso(self, move, datos):
        """
        Construye cartaporte31:CartaPorte para el CFDI Ingreso.

        Para facturas consolidadas (N waybills):
          - Genera N pares Ubicacion OR/DE (uno por waybill)
          - Combina todas las mercancías de todos los waybills
          - Usa el vehículo del primer waybill en Autotransporte
          - Usa el chofer del primer waybill en FiguraTransporte

        IdCCP: tms_id_ccp_ingreso del account.move (generado en action_tms_stamp_ingreso).
        """
        waybills = move.tms_waybill_ids
        primer_waybill = waybills[0]

        # IdCCP del Ingreso — distinto al del Traslado
        id_ccp = move.tms_id_ccp_ingreso or self._generate_id_ccp()

        distancia_total = sum(w.distance_km or 0 for w in waybills)

        cp = etree.Element(etree.QName(NS_CP31, 'CartaPorte'))
        cp.set('Version',        '3.1')
        cp.set('IdCCP',          id_ccp)
        cp.set('TranspInternac', 'No')
        cp.set('TotalDistRec',   str(int(distancia_total)))

        # Ubicaciones: N pares OR/DE, uno por waybill
        cp.append(self._build_ubicaciones_ingreso(waybills, datos))

        # Mercancias: todas las mercancías de todos los waybills combinadas
        mercancias_node = self._build_mercancias_consolidadas(waybills)
        # Autotransporte del primer waybill (vehículo principal del tren vehicular)
        mercancias_node.append(self._build_autotransporte(primer_waybill))
        cp.append(mercancias_node)

        # FiguraTransporte del primer waybill (chofer principal)
        cp.append(self._build_figura_transporte(primer_waybill, datos))

        return cp

    def _build_ubicaciones_ingreso(self, waybills, datos):
        """
        Construye el nodo Ubicaciones para CFDI Ingreso con N waybills.

        Genera N pares OR/DE — uno por cada waybill incluido en la factura.
        IDUbicacion: OR000001/DE000001, OR000002/DE000002, etc.
        Regla CP107 NO aplica en Ingreso — el receptor es el cliente real.
        """
        es_pruebas = datos.get('es_pruebas', False)
        ubicaciones = etree.Element(etree.QName(NS_CP31, 'Ubicaciones'))

        for idx, waybill in enumerate(waybills, start=1):
            # Origen
            origen = etree.SubElement(ubicaciones, etree.QName(NS_CP31, 'Ubicacion'))
            origen.set('TipoUbicacion', 'Origen')
            origen.set('IDUbicacion',   'OR%06d' % idx)
            origen.set('RFCRemitenteDestinatario',
                       'EKU9003173C9' if es_pruebas else
                       (_normalize_rfc(waybill.partner_origin_id.vat) or 'XAXX010101000'))
            origen.set('NombreRemitenteDestinatario',
                       (waybill.partner_origin_id.name or '').upper()[:254])
            origen.set('FechaHoraSalidaLlegada',
                       datetime.now(_TZ_MEXICO).strftime('%Y-%m-%dT%H:%M:%S'))
            dom_o = etree.SubElement(origen, etree.QName(NS_CP31, 'Domicilio'))
            dom_o.set('CodigoPostal', waybill.origin_zip or '00000')
            dom_o.set('Estado',       self._get_estado_from_zip(waybill, waybill.origin_zip) or 'JAL')
            dom_o.set('Pais',         'MEX')

            # Destino
            destino = etree.SubElement(ubicaciones, etree.QName(NS_CP31, 'Ubicacion'))
            destino.set('TipoUbicacion',   'Destino')
            destino.set('IDUbicacion',     'DE%06d' % idx)
            destino.set('RFCRemitenteDestinatario',
                        'EKU9003173C9' if es_pruebas else
                        (_normalize_rfc(waybill.partner_dest_id.vat) or 'XAXX010101000'))
            destino.set('NombreRemitenteDestinatario',
                        (waybill.partner_dest_id.name or '').upper()[:254])
            destino.set('DistanciaRecorrida', str(int(waybill.distance_km or 0)))
            destino.set('FechaHoraSalidaLlegada',
                        datetime.now(_TZ_MEXICO).strftime('%Y-%m-%dT%H:%M:%S'))
            dom_d = etree.SubElement(destino, etree.QName(NS_CP31, 'Domicilio'))
            dom_d.set('CodigoPostal', waybill.dest_zip or '00000')
            dom_d.set('Estado',       self._get_estado_from_zip(waybill, waybill.dest_zip) or 'JAL')
            dom_d.set('Pais',         'MEX')

        return ubicaciones

    def _build_mercancias_consolidadas(self, waybills):
        """
        Construye el nodo Mercancias combinando todas las líneas de todos los waybills.
        Se usa en CFDI Ingreso consolidado (N viajes en una factura).
        El peso total es la suma de todas las mercancías de todos los viajes.
        """
        peso_total = sum(
            (line.weight_kg or 0) * (line.quantity or 1)
            for waybill in waybills
            for line in waybill.line_ids
        )
        total_mercancias = sum(len(w.line_ids) for w in waybills)

        mercancias = etree.Element(etree.QName(NS_CP31, 'Mercancias'))
        mercancias.set('PesoBrutoTotal',     '{:.3f}'.format(peso_total or 0))
        mercancias.set('UnidadPeso',         'KGM')
        mercancias.set('NumTotalMercancias', str(total_mercancias or 1))

        # Iterar todas las líneas de todos los waybills
        for waybill in waybills:
            for line in waybill.line_ids:
                merc = etree.SubElement(mercancias, etree.QName(NS_CP31, 'Mercancia'))
                merc.set('BienesTransp',
                         _normalize_sat_code(line.product_sat_id.code if line.product_sat_id else '47131500'))
                merc.set('Descripcion', (line.description or 'MERCANCIA GENERAL')[:100])
                merc.set('Cantidad',    '{:.3f}'.format(line.quantity or 1))
                merc.set('ClaveUnidad',
                         _normalize_sat_code(line.uom_sat_id.code if line.uom_sat_id else 'KGM'))
                merc.set('PesoEnKg',   '{:.3f}'.format((line.weight_kg or 0) * (line.quantity or 1)))
                merc.set('Dimensiones', line.dimensions or '000/000/000cm')

        return mercancias

    def _get_datos_fiscales_ingreso(self, company, move):
        """
        Retorna diccionario con datos fiscales para el CFDI Ingreso.

        Diferencia clave vs Traslado:
          En Ingreso, el Receptor es el CLIENTE (move.partner_id), no la empresa.
          El cliente puede ser persona moral (RFC 12 chars) o física (RFC 13 chars).

        En pruebas: RFC receptor → EKU9003173C9 (PM válida en dev33).
        En producción: RFC receptor → move.partner_id.vat.
        """
        es_pruebas = (company.fd_ambiente == 'pruebas')

        if es_pruebas:
            rfc_pruebas    = self._get_rfc_from_cer(company) or company.vat or 'EKU9003173C9'
            nombre_pruebas = (company.name or '').upper()[:254]
            cp_pruebas     = company.zip or '44970'
            return {
                'rfc_emisor':               rfc_pruebas,
                'nombre_emisor':            nombre_pruebas,
                'regimen_fiscal':           '616',
                # En pruebas el receptor también usa RFC de pruebas
                'rfc_receptor':             'EKU9003173C9',
                'nombre_receptor':          nombre_pruebas,
                'regimen_receptor':         '616',
                'uso_cfdi':                 'G03',
                'lugar_expedicion':         cp_pruebas,
                'domicilio_fiscal_receptor': cp_pruebas,
                'rfc_chofer':               'CACX7605101P8',
                'es_pruebas':               True,
            }
        else:
            rfc_real        = (company.vat or '').upper().strip()
            partner         = move.partner_id
            rfc_receptor    = (_normalize_rfc(partner.vat) if partner else '') or 'XAXX010101000'
            nombre_receptor = (partner.name or '').upper()[:254] if partner else ''
            cp_receptor     = (partner.zip or company.zip or '00000') if partner else company.zip or '00000'
            # Régimen fiscal del receptor: usar l10n_mx_edi_fiscal_regime si existe, sino '616'
            regimen_receptor = (
                getattr(partner, 'l10n_mx_edi_fiscal_regime', None) or '616'
            ) if partner else '616'
            return {
                'rfc_emisor':               rfc_real,
                'nombre_emisor':            (company.name or '').upper()[:254],
                'regimen_fiscal':           (company.tms_regimen_fiscal_id.code or '612'),
                'rfc_receptor':             rfc_receptor,
                'nombre_receptor':          nombre_receptor,
                'regimen_receptor':         regimen_receptor,
                'uso_cfdi':                 'G03',  # G03 = Gastos en General (default flete)
                'lugar_expedicion':         company.zip or '00000',
                'domicilio_fiscal_receptor': cp_receptor,
                'rfc_chofer':               '',
                'es_pruebas':               False,
            }

    # ------------------------------------------------------------------
    # Validación previa al build
    # ------------------------------------------------------------------

    def _validate_required_fields(self, waybill, company):
        """Valida campos requeridos antes de construir el XML.
        Lanza UserError con mensaje claro si falta algún dato SAT crítico.
        Previene timbrados fallidos por datos incompletos — mejor fallar aquí
        con mensaje legible que recibir un error críptico del PAC.

        En ambiente 'pruebas', las validaciones de RFC del chofer se relajan
        porque _get_datos_fiscales() las sustituye por valores de prueba.
        """
        es_pruebas = (company.fd_ambiente == 'pruebas')
        errors = []
        vehicle = waybill.vehicle_id
        if not vehicle:
            errors.append('No hay vehículo asignado al viaje')
        else:
            if not vehicle.license_plate:
                errors.append('El vehículo no tiene placa asignada')
            if not vehicle.sat_permiso_sct_id:
                errors.append('El vehículo no tiene tipo de permiso SCT')
            if not vehicle.permiso_sct_number:
                errors.append('El vehículo no tiene número de permiso SCT')
        driver = waybill.driver_id
        if not driver:
            errors.append('No hay chofer asignado al viaje')
        else:
            # En pruebas, _get_datos_fiscales sustituye el RFC del chofer por CACX7605101P8
            if not driver.tms_rfc and not es_pruebas:
                errors.append('El chofer no tiene RFC')
            licencia = getattr(driver, 'tms_driver_license', None)
            if not licencia:
                errors.append('El chofer no tiene número de licencia federal')
        if not waybill.line_ids:
            errors.append('No hay mercancías en el viaje')
        else:
            for line in waybill.line_ids:
                if not line.product_sat_id:
                    errors.append(
                        'La mercancía "%s" no tiene clave SAT' %
                        (line.description or str(line.id))
                    )
        if errors:
            raise UserError(
                'No se puede generar el XML. Corrige lo siguiente:\n• ' +
                '\n• '.join(errors)
            )

    # ------------------------------------------------------------------
    # Nodo raíz: cfdi:Comprobante
    # ------------------------------------------------------------------

    def _build_comprobante(self, waybill, datos):
        """
        Construye el nodo raíz cfdi:Comprobante con atributos CFDI 4.0.
        TipoDeComprobante='T' (Traslado) porque Carta Porte no es ingreso.
        LugarExpedicion viene de datos['lugar_expedicion'] — en pruebas usa
        el CP del certificado de pruebas en lugar del CP real de la empresa.
        """
        # SAT exige fecha en zona horaria del centro de México (sin offset)
        fecha = datetime.now(_TZ_MEXICO).strftime('%Y-%m-%dT%H:%M:%S')

        comp = etree.Element(
            etree.QName(NS_CFDI, 'Comprobante'),
            nsmap=NSMAP,
        )

        comp.set(etree.QName(NS_XSI, 'schemaLocation'), SCHEMA_LOCATION)
        comp.set('Version',             '4.0')
        comp.set('Fecha',               fecha)
        comp.set('Sello',               '')          # se rellena al firmar
        comp.set('NoCertificado',       '')          # se rellena al firmar
        comp.set('Certificado',         '')          # se rellena al firmar
        comp.set('SubTotal',            '0')
        comp.set('Total',               '0')
        comp.set('Moneda',              'XXX')       # XXX = no aplica (traslado)
        comp.set('TipoDeComprobante',   'T')         # T = Traslado
        comp.set('Exportacion',         '01')        # 01 = No aplica
        comp.set('LugarExpedicion',     datos['lugar_expedicion'])

        return comp

    # ------------------------------------------------------------------
    # cfdi:Emisor
    # ------------------------------------------------------------------

    def _build_emisor(self, company, datos):
        """
        Construye cfdi:Emisor con RFC, Nombre y RegimenFiscal.
        En pruebas usa el RFC del certificado de pruebas (datos['rfc_emisor']).
        En producción usa company.vat.
        """
        emisor = etree.Element(etree.QName(NS_CFDI, 'Emisor'))
        emisor.set('Rfc',           datos['rfc_emisor'])
        emisor.set('Nombre',        datos['nombre_emisor'])
        emisor.set('RegimenFiscal', datos['regimen_fiscal'])
        return emisor

    # ------------------------------------------------------------------
    # cfdi:Receptor
    # ------------------------------------------------------------------

    def _build_receptor(self, waybill, datos):
        """
        Construye cfdi:Receptor.

        Regla SAT CP107: en TipoDeComprobante='T' (Traslado), el Receptor
        DEBE ser el mismo que el Emisor — el transportista se emite la Carta
        Porte a sí mismo. El cliente real va en las Ubicaciones del complemento.

        En pruebas usa el RFC del certificado de pruebas (datos['rfc_receptor']).
        UsoCFDI = 'S01' (Sin efectos fiscales) es el correcto para traslado.
        """
        receptor = etree.Element(etree.QName(NS_CFDI, 'Receptor'))
        receptor.set('Rfc',                     datos['rfc_receptor'])
        receptor.set('Nombre',                  datos['nombre_receptor'])
        receptor.set('DomicilioFiscalReceptor', datos['domicilio_fiscal_receptor'])
        receptor.set('RegimenFiscalReceptor',   datos['regimen_receptor'])
        receptor.set('UsoCFDI',                 datos['uso_cfdi'])
        return receptor

    # ------------------------------------------------------------------
    # cfdi:Conceptos — servicio de autotransporte de carga
    # ------------------------------------------------------------------

    def _build_conceptos(self, waybill):
        """
        Construye cfdi:Conceptos.
        Para Carta Porte (TipoDeComprobante=T) se usa un concepto único
        que representa el servicio de autotransporte de carga.
        ClaveProdServ: 78101800 (Servicios de transporte de carga por carretera)
        ClaveUnidad:   E48 (Unidad de servicio)
        Importe: 0 porque en Traslado el valor fiscal es 0.
        """
        conceptos = etree.Element(etree.QName(NS_CFDI, 'Conceptos'))
        concepto  = etree.SubElement(conceptos, etree.QName(NS_CFDI, 'Concepto'))

        concepto.set('ClaveProdServ',  '78101800')
        concepto.set('Cantidad',       '1')
        concepto.set('ClaveUnidad',    'E48')
        concepto.set('Descripcion',    'SERVICIO DE AUTOTRANSPORTE DE CARGA')
        concepto.set('ValorUnitario',  '0')
        concepto.set('Importe',        '0')
        concepto.set('ObjetoImp',      '01')  # 01 = No objeto de impuesto (traslado)

        return conceptos

    # ------------------------------------------------------------------
    # cfdi:Impuestos — para Traslado son vacíos pero el nodo es requerido
    # ------------------------------------------------------------------

    def _build_impuestos(self, waybill):
        """
        Para TipoDeComprobante='T' (Traslado), Impuestos va vacío.
        El nodo es requerido por el esquema XSD pero sin subnodos.
        """
        impuestos = etree.Element(etree.QName(NS_CFDI, 'Impuestos'))
        impuestos.set('TotalImpuestosTrasladados', '0')
        return impuestos

    # ------------------------------------------------------------------
    # Complemento Carta Porte 3.1
    # ------------------------------------------------------------------

    def _build_complemento_carta_porte(self, waybill, datos):
        """
        Construye el nodo cartaporte31:CartaPorte Version='3.1'.

        Orden de nodos según XSD del SAT (CartaPorte31):
          1. Ubicaciones
          2. Mercancias  ← Autotransporte va DENTRO de Mercancias, no al mismo nivel
          3. FiguraTransporte
        """
        # Usar el IdCCP del waybill. Si llegó vacío por algún motivo inesperado,
        # generar uno temporal para este XML (la capa primaria ya persiste en action_stamp_cfdi).
        id_ccp = waybill.tms_id_ccp or self._generate_id_ccp()

        cp = etree.Element(etree.QName(NS_CP31, 'CartaPorte'))
        cp.set('Version',              '3.1')
        cp.set('IdCCP',                id_ccp)
        cp.set('TranspInternac',       'No')
        cp.set('TotalDistRec',         str(int(waybill.distance_km or 0)))

        cp.append(self._build_ubicaciones(waybill, datos))

        # Mercancias contiene Autotransporte como hijo (no al nivel de CartaPorte)
        mercancias_node = self._build_mercancias(waybill)
        mercancias_node.append(self._build_autotransporte(waybill))
        cp.append(mercancias_node)

        # datos se pasa para poder sustituir RFC del chofer en pruebas
        cp.append(self._build_figura_transporte(waybill, datos))

        return cp

    # ------------------------------------------------------------------
    # Ubicaciones
    # ------------------------------------------------------------------

    def _build_ubicaciones(self, waybill, datos=None):
        """
        Construye Ubicaciones con Origen y Destino.
        IDUbicacion: OR000001 (origen) / DE000001 (destino).
        Domicilio requiere: CodigoPostal + Estado + Pais='MEX'.

        En ambiente pruebas, si el partner no tiene RFC, usa EKU9003173C9
        (persona moral válida en dev33) en lugar de XAXX010101000 — el PAC
        dev33 rechaza XAXX010101000 en RFCRemitenteDestinatario (CP132).
        """
        # En pruebas SIEMPRE usar EKU9003173C9 — el PAC dev33 rechaza RFCs reales
        # que no están en su lista de pruebas (CP132), aunque el RFC exista en el SAT.
        # En producción: RFC real del partner, o XAXX010101000 si no tiene.
        es_pruebas = datos.get('es_pruebas', False) if datos else False

        ubicaciones = etree.Element(etree.QName(NS_CP31, 'Ubicaciones'))

        # Origen
        origen = etree.SubElement(ubicaciones, etree.QName(NS_CP31, 'Ubicacion'))
        origen.set('TipoUbicacion',    'Origen')
        origen.set('IDUbicacion',      'OR000001')
        origen.set('RFCRemitenteDestinatario',
                   'EKU9003173C9' if es_pruebas else
                   (_normalize_rfc(waybill.partner_origin_id.vat) or 'XAXX010101000'))
        origen.set('NombreRemitenteDestinatario',
                   (waybill.partner_origin_id.name or '').upper()[:254])
        origen.set('FechaHoraSalidaLlegada',
                   datetime.now(_TZ_MEXICO).strftime('%Y-%m-%dT%H:%M:%S'))

        dom_origen = etree.SubElement(origen, etree.QName(NS_CP31, 'Domicilio'))
        dom_origen.set('CodigoPostal', waybill.origin_zip or '00000')
        dom_origen.set('Estado',       self._get_estado_from_zip(waybill, waybill.origin_zip) or 'CDMX')
        dom_origen.set('Pais',         'MEX')

        # Destino
        destino = etree.SubElement(ubicaciones, etree.QName(NS_CP31, 'Ubicacion'))
        destino.set('TipoUbicacion',   'Destino')
        destino.set('IDUbicacion',     'DE000001')
        destino.set('RFCRemitenteDestinatario',
                    'EKU9003173C9' if es_pruebas else
                    (_normalize_rfc(waybill.partner_dest_id.vat) or 'XAXX010101000'))
        destino.set('NombreRemitenteDestinatario',
                    (waybill.partner_dest_id.name or '').upper()[:254])
        destino.set('DistanciaRecorrida', str(int(waybill.distance_km or 0)))
        destino.set('FechaHoraSalidaLlegada',
                    datetime.now(_TZ_MEXICO).strftime('%Y-%m-%dT%H:%M:%S'))

        dom_destino = etree.SubElement(destino, etree.QName(NS_CP31, 'Domicilio'))
        dom_destino.set('CodigoPostal', waybill.dest_zip or '00000')
        dom_destino.set('Estado',       self._get_estado_from_zip(waybill, waybill.dest_zip) or 'JAL')
        dom_destino.set('Pais',         'MEX')

        return ubicaciones

    # ------------------------------------------------------------------
    # Helper: estado SAT desde código postal
    # ------------------------------------------------------------------

    def _get_estado_from_zip(self, waybill, zip_code):
        """
        Obtiene el código de estado SAT a partir del CP via catálogo tms.sat.codigo.postal.
        Retorna '' si el CP no está en el catálogo — el caller aplica el default.
        origin_zip / dest_zip son fields.Char (no Many2one), así que hay que buscar.
        """
        if not zip_code:
            return ''
        sat_cp = waybill.env['tms.sat.codigo.postal'].search(
            [('code', '=', zip_code)], limit=1)
        return sat_cp.estado if sat_cp else ''

    # ------------------------------------------------------------------
    # Mercancias
    # ------------------------------------------------------------------

    def _build_mercancias(self, waybill):
        """
        Construye el nodo Mercancias con una Mercancia por cada línea del waybill.
        Campos requeridos por CP 3.1: BienesTransp, Descripcion, Cantidad,
        ClaveUnidad, PesoEnKg, Dimensiones.
        """
        peso_total = sum(
            (line.weight_kg or 0) * (line.quantity or 1)
            for line in waybill.line_ids
        )
        mercancias = etree.Element(etree.QName(NS_CP31, 'Mercancias'))
        mercancias.set('PesoBrutoTotal',  '{:.3f}'.format(peso_total or 0))
        mercancias.set('UnidadPeso',      'KGM')
        mercancias.set('NumTotalMercancias', str(len(waybill.line_ids) or 1))

        for line in waybill.line_ids:
            merc = etree.SubElement(mercancias, etree.QName(NS_CP31, 'Mercancia'))
            merc.set('BienesTransp',
                     _normalize_sat_code(line.product_sat_id.code if line.product_sat_id else '47131500'))
            merc.set('Descripcion',   (line.description or 'MERCANCIA GENERAL')[:100])
            merc.set('Cantidad',      '{:.3f}'.format(line.quantity or 1))
            merc.set('ClaveUnidad',
                     _normalize_sat_code(line.uom_sat_id.code if line.uom_sat_id else 'KGM'))
            merc.set('PesoEnKg',      '{:.3f}'.format((line.weight_kg or 0) * (line.quantity or 1)))
            merc.set('Dimensiones',   line.dimensions or '000/000/000cm')

            # MaterialPeligroso SOLO cuando is_dangerous=True Y el catálogo SAT lo permite.
            # Regla CP155: si la clave del catálogo c_ClaveProdServCP NO contiene '1'
            # en su columna MaterialPeligroso, el atributo NO DEBE existir en el XML.
            # Valores de catálogo: '0'=prohibido, '1'=obligatorio, '0,1'=opcional.
            # Si es_peligroso=True pero el catálogo dice '0', se omite el atributo
            # y se emite un WARNING para corregir los datos.
            clave_mp_catalogo = ''
            if line.product_sat_id:
                clave_mp_catalogo = (line.product_sat_id.material_peligroso or '').strip()
            catalogo_permite_peligroso = '1' in clave_mp_catalogo.split(',')

            if line.is_dangerous and catalogo_permite_peligroso:
                merc.set('MaterialPeligroso', 'Sí')
                mat_pel = getattr(line, 'material_peligroso_id', None)
                if mat_pel and getattr(mat_pel, 'code', None):
                    merc.set('CveMaterialPeligroso', mat_pel.code)
                embalaje = getattr(line, 'embalaje_id', None)
                if embalaje and getattr(embalaje, 'code', None):
                    merc.set('Embalaje', embalaje.code)
            elif line.is_dangerous and not catalogo_permite_peligroso:
                # Dato inconsistente: is_dangerous=True pero el catálogo lo prohíbe.
                # Se omite el atributo para evitar CP155 — corregir el waybill.
                _logger.warning(
                    'CP155 PREVENIDO — Línea %s: is_dangerous=True pero la clave SAT '
                    '"%s" tiene "%s" en catálogo (no permite MaterialPeligroso). '
                    'Atributo omitido del XML. Corrija is_dangerous en el waybill.',
                    line.id,
                    line.product_sat_id.code if line.product_sat_id else 'sin clave',
                    clave_mp_catalogo or 'vacío',
                )
            # Si is_dangerous=False → NO se agrega el atributo en ningún caso.

        _logger.warning(
            'Mercancias XML generado:\n%s',
            etree.tostring(mercancias, pretty_print=True).decode('utf-8'),
        )
        return mercancias

    # ------------------------------------------------------------------
    # Autotransporte
    # ------------------------------------------------------------------

    def _build_autotransporte(self, waybill):
        """
        Construye cartaporte31:Autotransporte con vehículo, seguros y remolques.
        PermSCT: tipo de permiso SCT del vehículo.
        NumPermisoSCT: número de permiso SCT.
        Seguros: RC obligatorio, Carga si hay mercancías, Ambiental si peligroso.
        """
        vehicle = waybill.vehicle_id
        company = waybill.company_id

        auto = etree.Element(etree.QName(NS_CP31, 'Autotransporte'))
        auto.set('PermSCT',
                 _normalize_sat_code(vehicle.sat_permiso_sct_id.code if (vehicle and vehicle.sat_permiso_sct_id) else 'TPAF10'))
        auto.set('NumPermisoSCT',
                 _normalize_sat_code(vehicle.permiso_sct_number or '000000'))

        # IdentificacionVehicular
        # PesoBrutoVehicular es REQUERIDO por el XSLT del SAT (en toneladas métricas)
        peso_bruto = round(
            (vehicle.tms_gross_vehicle_weight if vehicle else 0.0) or 20.0, 3
        )
        id_veh = etree.SubElement(auto, etree.QName(NS_CP31, 'IdentificacionVehicular'))
        id_veh.set('ConfigVehicular',
                   _normalize_sat_code(vehicle.sat_config_id.code if (vehicle and vehicle.sat_config_id) else 'C2'))
        id_veh.set('PesoBrutoVehicular', f'{peso_bruto:.3f}')
        # SAT exige PlacaVM sin guiones ni espacios, entre 5 y 7 caracteres alfanuméricos
        id_veh.set('PlacaVM', _normalize_placa(vehicle.license_plate if vehicle else '') or 'SINPLA')
        id_veh.set('AnioModeloVM', str(vehicle.model_year or '2020') if vehicle else '2020')

        # Seguros — mapeo correcto según XSLT SAT CP 3.1:
        #   RC      → AseguraRespCivil / PolizaRespCivil  (obligatorio)
        #   Carga   → AseguraCarga     / PolizaCarga       (opcional)
        #   Ambiental → AseguraMedAmbiente / PolizaMedAmbiente (opcional)
        seguros = etree.SubElement(auto, etree.QName(NS_CP31, 'Seguros'))
        seguros.set('AseguraRespCivil', company.tms_insurance_rc_company or 'NO INFORMADO')
        seguros.set('PolizaRespCivil',  company.tms_insurance_rc_policy  or '0000000')
        if company.tms_insurance_cargo_policy:
            seguros.set('AseguraCarga', company.tms_insurance_cargo_company or '')
            seguros.set('PolizaCarga',  company.tms_insurance_cargo_policy  or '')
        if company.tms_insurance_env_policy:
            seguros.set('AseguraMedAmbiente', company.tms_insurance_env_company or '')
            seguros.set('PolizaMedAmbiente',  company.tms_insurance_env_policy  or '')

        # Remolques (si aplica) — misma limpieza de placa que PlacaVM (sin guiones/espacios, máx 7)
        if waybill.trailer1_id:
            remolques_node = etree.SubElement(auto, etree.QName(NS_CP31, 'Remolques'))
            rem1 = etree.SubElement(remolques_node, etree.QName(NS_CP31, 'Remolque'))
            rem1.set('SubTipoRem', getattr(waybill.trailer1_id, 'tms_subtipo_remolque', None) or 'CTR007')
            rem1.set('Placa', _normalize_placa(waybill.trailer1_id.license_plate) or 'SINREM')

            if waybill.trailer2_id:
                rem2 = etree.SubElement(remolques_node, etree.QName(NS_CP31, 'Remolque'))
                rem2.set('SubTipoRem', getattr(waybill.trailer2_id, 'tms_subtipo_remolque', None) or 'CTR007')
                rem2.set('Placa', _normalize_placa(waybill.trailer2_id.license_plate) or 'SINREM')

        return auto

    # ------------------------------------------------------------------
    # FiguraTransporte
    # ------------------------------------------------------------------

    def _build_figura_transporte(self, waybill, datos):
        """
        Construye cartaporte31:FiguraTransporte con el operador (chofer).
        TipoFigura='01' (Operador).
        RFC, Nombre y NumLicencia son obligatorios.

        En ambiente pruebas, sustituye el RFC del chofer por el valor de
        datos['rfc_chofer'] para que el PAC no rechace con CP132.
        El nombre y la licencia se mantienen reales en ambos ambientes.
        """
        driver = waybill.driver_id
        figura_root = etree.Element(etree.QName(NS_CP31, 'FiguraTransporte'))

        if driver:
            # RFC: en pruebas se usa el RFC de pruebas; en producción el RFC real del chofer
            rfc_override  = datos.get('rfc_chofer', '')
            rfc_real      = (driver.tms_rfc or '').upper().strip()
            rfc_valor     = rfc_override if rfc_override else (rfc_real or 'XEXX010101000')
            nombre_valor  = (driver.name or '').upper()[:254]
            licencia_valor = driver.tms_driver_license or ''
            _logger.warning(
                'FiguraTransporte — RFC real: %r → RFC usado: %r, Nombre: %r, Licencia: %r',
                rfc_real,
                rfc_valor,
                nombre_valor,
                licencia_valor,
            )
            figura = etree.SubElement(figura_root, etree.QName(NS_CP31, 'TiposFigura'))
            figura.set('TipoFigura', '01')
            figura.set('RFCFigura',   rfc_valor)
            figura.set('NombreFigura', nombre_valor)
            figura.set('NumLicencia',  _normalize_sat_code(licencia_valor) or '000000000000')
        else:
            # Figura vacía de relleno para cumplir XSD
            figura = etree.SubElement(figura_root, etree.QName(NS_CP31, 'TiposFigura'))
            figura.set('TipoFigura', '01')
            figura.set('RFCFigura',   'XEXX010101000')
            figura.set('NombreFigura', 'OPERADOR NO ASIGNADO')
            figura.set('NumLicencia',  '000000000000')

        _logger.warning(
            'FiguraTransporte XML generado:\n%s',
            etree.tostring(figura_root, pretty_print=True).decode('utf-8'),
        )
        return figura_root

    # ------------------------------------------------------------------
    # Helpers de ambiente fiscal
    # ------------------------------------------------------------------

    def _generate_id_ccp(self):
        """
        Genera un IdCCP con el formato requerido por el SAT para Carta Porte 3.1.

        Patrón: CCC[5hex]-[4hex]-[4hex]-[4hex]-[12hex]
        Ejemplo: CCC1a2b3-4c5d-6e7f-8a9b-0c1d2e3f4a5b

        Este método es el fallback del builder. La capa primaria de generación
        es action_stamp_cfdi en tms_waybill.py, que persiste el IdCCP en BD
        antes de llamar a build(), garantizando consistencia entre timbrado y cancelación.
        """
        raw = uuid.uuid4().hex  # 32 chars hex sin guiones
        return f"CCC{raw[0:5]}-{raw[5:9]}-{raw[9:13]}-{raw[13:17]}-{raw[17:29]}"

    def _get_rfc_from_cer(self, company):
        """
        Extrae el RFC del certificado CSD (.cer) cargado en la empresa.

        El SAT almacena el RFC en el Subject del X.509 bajo OID 2.5.4.45
        (uniqueIdentifier). Algunos certificados lo incluyen también en el CN.

        Retorna el RFC en mayúsculas o None si no se puede extraer.
        """
        if not company.tms_csd_cer:
            return None
        try:
            cer_bytes = base64.b64decode(company.tms_csd_cer)
            cert = x509.load_der_x509_certificate(cer_bytes, default_backend())
            # OID 2.5.4.45 (uniqueIdentifier) — donde el SAT pone el RFC en sus CSD
            oid_uid = x509.ObjectIdentifier('2.5.4.45')
            attrs = cert.subject.get_attributes_for_oid(oid_uid)
            if attrs:
                rfc_raw = attrs[0].value
                # El SAT puede incluir formato "XXXXXXXXXXXXXXXX / CURP" — tomar solo RFC
                rfc = rfc_raw.split('/')[0].strip().upper()
                _logger.info('RFC extraído del .cer: %s', rfc)
                return rfc
        except Exception as exc:
            _logger.warning('No se pudo extraer RFC del .cer: %s', exc)
        return None

    def _get_datos_fiscales(self, company, waybill):
        """
        Retorna diccionario con datos fiscales para los nodos CFDI.

        En ambiente 'pruebas':
          - RFC emisor/receptor: del .cer cargado → company.vat → 'EKU9003173C9' (fallback)
          - Nombre emisor/receptor: company.name (debe coincidir con el padrón SAT dev33)
          - Régimen fiscal: '616' (Sin obligaciones fiscales)
          - LugarExpedicion: CP de la empresa (debe ser 44970 para dev33)
          - RFC chofer: 'CACX7605101P8' (RFC de persona física válido en pruebas)

        En ambiente 'produccion':
          - Todos los valores provienen de los registros reales de la empresa.
          - RFC chofer: vacío aquí — _build_figura_transporte usa driver.tms_rfc.

        NOTA: En Carta Porte (TipoDeComprobante='T'), el Receptor es la misma
        empresa emisora (regla CP107 del SAT), no el cliente del waybill.
        """
        es_pruebas = (company.fd_ambiente == 'pruebas')

        if es_pruebas:
            # RFC: del .cer cargado → company.vat → fallback EKU9003173C9
            # Nombre: company.name (ajustar en Ajustes → Empresa para que coincida con el padrón SAT dev33)
            rfc_pruebas    = self._get_rfc_from_cer(company) or company.vat or 'EKU9003173C9'
            nombre_pruebas = (company.name or '').upper()[:254]
            # CP de la empresa — debe coincidir con el del certificado (44970 para dev33)
            cp_pruebas  = company.zip or '44970'
            return {
                'rfc_emisor':               rfc_pruebas,
                'nombre_emisor':            nombre_pruebas,
                'regimen_fiscal':           '616',
                'rfc_receptor':             rfc_pruebas,    # receptor = emisor (CP107)
                'nombre_receptor':          nombre_pruebas,
                'regimen_receptor':         '616',
                'uso_cfdi':                 'S01',
                'lugar_expedicion':         cp_pruebas,
                'domicilio_fiscal_receptor': cp_pruebas,
                'rfc_chofer':               'CACX7605101P8',  # persona física válida en dev33
                'es_pruebas':               True,
            }
        else:
            # PRODUCCIÓN — datos reales, sin sustituciones
            rfc_real = (company.vat or '').upper().strip()
            return {
                'rfc_emisor':               rfc_real,
                'nombre_emisor':            (company.name or '').upper()[:254],
                'regimen_fiscal':           (company.tms_regimen_fiscal_id.code or '612'),
                'rfc_receptor':             (company.partner_id.vat or rfc_real).upper().strip(),
                'nombre_receptor':          (company.name or '').upper()[:254],
                'regimen_receptor':         (company.tms_regimen_fiscal_id.code or '612'),
                'uso_cfdi':                 'S01',
                'lugar_expedicion':         company.zip or '00000',
                'domicilio_fiscal_receptor': company.zip or '00000',
                'rfc_chofer':               '',  # vacío → _build_figura_transporte usa driver.tms_rfc
            }
