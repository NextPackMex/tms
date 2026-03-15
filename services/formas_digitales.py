# -*- coding: utf-8 -*-
"""
Wrapper para la API REST de Formas Digitales (forsedi.facturacfdi.mx).

URLs por ambiente:
  Pruebas:    https://dev33.facturacfdi.mx
  Producción: https://v33.facturacfdi.mx

Autenticación: usuario + password en cada request (query params o form data).
Timeout: 30 segundos en TODAS las llamadas HTTP.

IMPORTANTE: NUNCA registrar en _logger el XML completo ni las credenciales.
"""
import base64
import logging

import requests

_logger = logging.getLogger(__name__)

BASE_URLS = {
    'pruebas':    'https://dev33.facturacfdi.mx',
    'produccion': 'https://v33.facturacfdi.mx',
}


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
        Envía el XML sellado a Formas Digitales para timbrado.

        Args:
            xml_sellado_bytes: XML firmado con CSD como bytes

        Returns:
            dict: {
                'uuid':         str,  # UUID / folio fiscal
                'xml_timbrado': bytes, # XML con TFD incrustado
                'fecha':        str,  # fecha de timbrado ISO
                'no_cert_sat':  str,  # número certificado SAT
            }

        Raises:
            Exception: con mensaje descriptivo si el timbrado falla
        """
        url = f'{self.base_url}/stamp'
        _logger.info(
            'Timbrado FD — empresa: %s, ambiente: %s',
            self.company.name, self.company.fd_ambiente
        )

        try:
            # Enviar XML en base64 como form data
            xml_b64 = base64.b64encode(xml_sellado_bytes).decode('ascii')
            payload = {
                'Usuario':   self.company.fd_usuario or '',
                'Password':  self.company.fd_password or '',
                'xml':       xml_b64,
            }
            resp = requests.post(url, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
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

        # Interpretar respuesta — estructura ejemplo FD
        if not data.get('uuid') and not data.get('UUID'):
            codigo  = data.get('codigo', data.get('error', 'SIN_CODIGO'))
            mensaje = data.get('mensaje', data.get('message', 'Sin detalle'))
            raise Exception(
                f'Formas Digitales rechazó el CFDI. '
                f'Código: {codigo} — {mensaje}'
            )

        uuid        = data.get('uuid') or data.get('UUID', '')
        xml_tim_b64 = data.get('xml')  or data.get('xmlTimbrado', '')
        fecha       = data.get('fecha') or data.get('fechaTimbrado', '')
        no_cert_sat = data.get('noCertificadoSAT') or data.get('noCertSAT', '')

        xml_timbrado = base64.b64decode(xml_tim_b64) if xml_tim_b64 else xml_sellado_bytes

        _logger.info('Timbrado FD OK — UUID: %s', uuid)
        return {
            'uuid':         uuid,
            'xml_timbrado': xml_timbrado,
            'fecha':        fecha,
            'no_cert_sat':  no_cert_sat,
        }

    # ------------------------------------------------------------------
    # Cancelación
    # ------------------------------------------------------------------

    def cancelar(self, uuid, motivo, cer_b64, key_b64, password):
        """
        Cancela el CFDI usando el CSD (método 1 SAT).

        Args:
            uuid     : UUID del CFDI a cancelar
            motivo   : '01','02','03','04' según catálogo SAT
            cer_b64  : certificado .cer en base64
            key_b64  : llave privada .key en base64
            password : contraseña del .key

        Returns:
            dict: {'acuse': str, 'estatus': str}
        """
        url = f'{self.base_url}/cancel'
        _logger.info('Cancelación FD — UUID: %s, motivo: %s', uuid, motivo)

        try:
            payload = {
                'Usuario':   self.company.fd_usuario or '',
                'Password':  self.company.fd_password or '',
                'uuid':      uuid,
                'motivo':    motivo,
                'cer':       cer_b64,
                'key':       key_b64,
                'password':  password,
            }
            resp = requests.post(url, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise Exception('Formas Digitales: tiempo de espera agotado al cancelar.')
        except Exception as e:
            raise Exception(
                f'Formas Digitales: error al cancelar ({type(e).__name__}).'
            )

        if data.get('error'):
            raise Exception(
                f'Formas Digitales cancelación rechazada: {data.get("error")}'
            )

        return {
            'acuse':   data.get('acuse', ''),
            'estatus': data.get('estatus', 'cancelado'),
        }

    # ------------------------------------------------------------------
    # Consulta de estatus
    # ------------------------------------------------------------------

    def consultar_estatus(self, uuid):
        """
        Consulta el estatus del CFDI en el SAT vía Formas Digitales.

        Returns:
            dict: {'estatus': str, 'cancelable': str}
        """
        url = f'{self.base_url}/status'
        _logger.info('Consulta estatus FD — UUID: %s', uuid)

        try:
            params = {
                'Usuario':  self.company.fd_usuario or '',
                'Password': self.company.fd_password or '',
                'uuid':     uuid,
            }
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise Exception(
                f'Formas Digitales: error al consultar estatus ({type(e).__name__}).'
            )

        return {
            'estatus':    data.get('estatus', 'Desconocido'),
            'cancelable': data.get('cancelable', 'No'),
        }
