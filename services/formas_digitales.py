# -*- coding: utf-8 -*-
"""
Wrapper SOAP para el PAC Formas Digitales (forsedi.facturacfdi.mx).

URLs por ambiente:
  Pruebas:    https://dev33.facturacfdi.mx
  Producción: https://v33.facturacfdi.mx

Protocolo: SOAP Document/Literal sobre HTTP.
  - Sin token:  /WSTimbradoCFDIService  → TimbrarCFDI(accesos, comprobante)
  - Con token:  /WSForcogsaService      → Autenticar + Timbrar/TimbrarV2

Timeout: 30 segundos en TODAS las llamadas HTTP.

IMPORTANTE: NUNCA registrar en _logger el XML completo ni las credenciales.
"""
import logging

import requests
from lxml import etree as ET

_logger = logging.getLogger(__name__)

BASE_URLS = {
    'pruebas':    'https://dev33.facturacfdi.mx',
    'produccion': 'https://v33.facturacfdi.mx',
}

# Namespaces SOAP y del servicio FD
_SOAP_NS = 'http://schemas.xmlsoap.org/soap/envelope/'
_WS_NS   = 'http://wservicios/'
# Namespace del TFD para extraer UUID/fecha de la respuesta
_TFD_NS  = 'http://www.sat.gob.mx/TimbreFiscalDigital'


class FormasDigitalesPac:
    """
    Wrapper REST para el PAC Formas Digitales.

    Uso:
        pac = FormasDigitalesPac(company)
        result = pac.timbrar(xml_sellado_bytes)
        # result = {'uuid': ..., 'xml_timbrado': ..., 'fecha': ..., 'no_cert_sat': ...}
    """

    def __init__(self, company):
        """
        Args:
            company: res.company con campos fd_usuario, fd_password, fd_ambiente
        """
        self.company  = company
        self.base_url = self._get_base_url()

    def _get_base_url(self):
        """Retorna la URL base según fd_ambiente de la empresa."""
        ambiente = self.company.fd_ambiente or 'pruebas'
        return BASE_URLS.get(ambiente, BASE_URLS['pruebas'])

    # ------------------------------------------------------------------
    # Timbrado
    # ------------------------------------------------------------------

    def timbrar(self, xml_sellado_bytes):
        """
        Envía el XML sellado a Formas Digitales para timbrado vía SOAP.

        FD usa SOAP Document/Literal (no REST). El endpoint es:
          /WSTimbradoCFDIService  → operación TimbrarCFDI
        Parámetros: accesos.usuario, accesos.password, comprobante (XML string)

        Args:
            xml_sellado_bytes: XML firmado con CSD como bytes

        Returns:
            dict: {
                'uuid':         str,   # UUID / folio fiscal del TFD
                'xml_timbrado': bytes, # XML con TimbreFiscalDigital incrustado
                'fecha':        str,   # fecha de timbrado ISO
                'no_cert_sat':  str,   # NoCertificadoSAT del TFD
            }

        Raises:
            Exception: con mensaje descriptivo si el timbrado falla
        """
        url = f'{self.base_url}/WSTimbradoCFDIService'
        _logger.info(
            'Timbrado FD SOAP — empresa: %s, ambiente: %s',
            self.company.name, self.company.fd_ambiente
        )

        # Construir el envelope SOAP con lxml para escaping correcto
        xml_str  = xml_sellado_bytes.decode('utf-8')
        envelope = self._build_soap_envelope('TimbrarCFDI', xml_str)
        soap_bytes = ET.tostring(envelope, xml_declaration=True, encoding='UTF-8')

        try:
            resp = requests.post(
                url,
                data=soap_bytes,
                headers={
                    'Content-Type': 'text/xml; charset=UTF-8',
                    'SOAPAction':   '',
                },
                timeout=30,
            )
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise Exception(
                'Formas Digitales: tiempo de espera agotado (30s). '
                'Intenta de nuevo o contacta soporte.'
            )
        except requests.exceptions.HTTPError as e:
            raise Exception(
                f'Formas Digitales: error HTTP {e.response.status_code}. '
                f'Verifica credenciales y ambiente configurado.'
            )
        except Exception as e:
            raise Exception(
                f'Formas Digitales: error de conexión ({type(e).__name__}). '
                f'Verifica la URL y la conectividad.'
            )

        # Parsear respuesta SOAP → extraer acuseCFDI
        return_el = self._parse_soap_response(resp.content, 'TimbrarCFDIResponse')

        codigo_error = self._get_soap_text(return_el, 'codigoError')
        error_msg    = self._get_soap_text(return_el, 'error')
        xml_tim_str  = self._get_soap_text(return_el, 'xmlTimbrado')

        # codigoError vacío o '0' = éxito
        if codigo_error and codigo_error not in ('0', ''):
            raise Exception(
                f'Formas Digitales rechazó el CFDI. '
                f'Código: {codigo_error} — {error_msg}'
            )
        if not xml_tim_str:
            raise Exception(
                f'Formas Digitales: no retornó xmlTimbrado. Detalle: {error_msg}'
            )

        xml_timbrado_bytes = xml_tim_str.encode('utf-8')

        # Extraer UUID, fecha y NoCertSAT del TFD dentro del XML timbrado
        uuid = fecha = no_cert_sat = ''
        try:
            tfd_tree = ET.fromstring(xml_timbrado_bytes)
            tfd = tfd_tree.find(f'.//{{{_TFD_NS}}}TimbreFiscalDigital')
            if tfd is not None:
                uuid        = tfd.get('UUID', '')
                fecha       = tfd.get('FechaTimbrado', '')
                no_cert_sat = tfd.get('NoCertificadoSAT', '')
        except ET.XMLSyntaxError:
            _logger.warning('FD: no se pudo parsear xmlTimbrado para extraer UUID')

        _logger.info('Timbrado FD OK — UUID: %s', uuid)
        return {
            'uuid':         uuid,
            'xml_timbrado': xml_timbrado_bytes,
            'fecha':        fecha,
            'no_cert_sat':  no_cert_sat,
        }

    # ------------------------------------------------------------------
    # Cancelación
    # ------------------------------------------------------------------

    def cancelar(self, uuid, motivo, cer_b64, key_b64, password):
        """
        Cancela el CFDI vía SOAP en WSTimbradoCFDIService → Cancelacion_1.

        Args:
            uuid     : UUID del CFDI a cancelar
            motivo   : '01','02','03','04' según catálogo SAT
            cer_b64  : certificado .cer en base64
            key_b64  : llave privada .key en base64
            password : contraseña del .key

        Returns:
            dict: {'acuse': str, 'estatus': str}
        """
        # ⚠️ TODO V2.3: implementar SOAP Cancelacion_1/Cancelacion_2 en WSTimbradoCFDIService
        # El WSDL de FD define Cancelacion_1 y Cancelacion_2 — pendiente consultar parámetros exactos.
        _logger.warning('FD cancelar: implementación SOAP pendiente para V2.3')
        return {'acuse': '', 'estatus': 'pendiente'}

    # ------------------------------------------------------------------
    # Consulta de estatus
    # ------------------------------------------------------------------

    def consultar_estatus(self, uuid):
        """
        Consulta el estatus del CFDI en el SAT vía Formas Digitales.

        Returns:
            dict: {'estatus': str, 'cancelable': str}
        """
        # ⚠️ TODO V2.3: implementar SOAP consulta estatus en WSTimbradoCFDIService
        _logger.warning('FD consultar_estatus: implementación SOAP pendiente para V2.3')
        return {'estatus': 'Desconocido', 'cancelable': 'No'}

    # ------------------------------------------------------------------
    # Helpers SOAP internos
    # ------------------------------------------------------------------

    def _build_soap_envelope(self, operation, xml_comprobante):
        """
        Construye el envelope SOAP para la operación TimbrarCFDI.

        Args:
            operation       : nombre de la operación SOAP ('TimbrarCFDI')
            xml_comprobante : XML sellado como string (lxml escapa automáticamente)

        Returns:
            lxml.etree._Element: envelope SOAP listo para serializar
        """
        envelope = ET.Element(
            f'{{{_SOAP_NS}}}Envelope',
            nsmap={'soapenv': _SOAP_NS, 'wse': _WS_NS},
        )
        ET.SubElement(envelope, f'{{{_SOAP_NS}}}Header')
        body = ET.SubElement(envelope, f'{{{_SOAP_NS}}}Body')
        op   = ET.SubElement(body, f'{{{_WS_NS}}}{operation}')

        # Elemento accesos con usuario y password
        accesos  = ET.SubElement(op, 'accesos')
        usr_el   = ET.SubElement(accesos, 'usuario')
        usr_el.text = self.company.fd_usuario or ''
        pwd_el   = ET.SubElement(accesos, 'password')
        pwd_el.text = self.company.fd_password or ''

        # El XML del comprobante va como texto (lxml escapa los caracteres XML)
        comp_el  = ET.SubElement(op, 'comprobante')
        comp_el.text = xml_comprobante

        return envelope

    def _parse_soap_response(self, resp_bytes, response_tag):
        """
        Parsea la respuesta SOAP y retorna el elemento <acuseCFDI> del Body.

        La respuesta real de FD tiene esta estructura:
          <S:Body>
            <ns2:TimbrarCFDIResponse>
              <acuseCFDI>          ← aquí están codigoError y xmlTimbrado
                <codigoError>...</codigoError>
                <xmlTimbrado>...</xmlTimbrado>
              </acuseCFDI>

        Args:
            resp_bytes   : bytes del cuerpo HTTP de la respuesta
            response_tag : tag esperado en el Body, ej. 'TimbrarCFDIResponse'

        Returns:
            lxml.etree._Element: elemento <acuseCFDI> con los campos del acuse

        Raises:
            Exception: si la respuesta es un Fault o no tiene formato esperado
        """
        try:
            root = ET.fromstring(resp_bytes)
        except ET.XMLSyntaxError as e:
            raise Exception(
                f'Formas Digitales: respuesta SOAP no es XML válido: {e}'
            )

        # Detectar SOAP Fault
        fault = root.find(f'.//{{{_SOAP_NS}}}Fault')
        if fault is not None:
            fault_str = fault.findtext('faultstring') or 'Sin detalle'
            raise Exception(f'Formas Digitales SOAP Fault: {fault_str}')

        # Buscar <acuseCFDI> — con namespace del servicio FD o sin él
        acuse = root.find(f'.//{{{_WS_NS}}}acuseCFDI')
        if acuse is None:
            acuse = root.find('.//acuseCFDI')
        if acuse is None:
            raise Exception(
                'Formas Digitales: respuesta SOAP sin elemento <acuseCFDI>. '
                f'Respuesta cruda (primeros 300 chars): {resp_bytes[:300]}'
            )
        return acuse

    def _get_soap_text(self, parent, tag):
        """
        Extrae el texto de un elemento hijo, buscando con y sin namespace WS.

        Args:
            parent : elemento padre lxml
            tag    : nombre del tag hijo

        Returns:
            str: texto del elemento o '' si no existe
        """
        el = parent.find(f'{{{_WS_NS}}}{tag}')
        if el is None:
            el = parent.find(tag)
        return (el.text or '').strip() if el is not None else ''
