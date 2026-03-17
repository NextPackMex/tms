# -*- coding: utf-8 -*-
"""
Wrapper para la API REST de SW Sapien (sw.com.mx / smarterweb.com.mx).

URLs por ambiente:
  Pruebas:    https://services.test.sw.com.mx
  Producción: https://services.sw.com.mx

Autenticación: Bearer token JWT obtenido con usuario/password.
El token tiene vigencia de ~2 horas. Se cachea en ir.config_parameter
por 90 minutos para evitar re-autenticación en cada timbrado.

Endpoints (path dice cfdi33 pero acepta CFDI 4.0):
  POST /cfdi33/stamp/v4   → timbrar XML sellado
  POST /cfdi33/cancel     → cancelar CFDI
  GET  /cfdi33/status     → consultar estatus

IMPORTANTE: NUNCA registrar en _logger el token, credenciales o XML.
"""
import base64
import logging
from datetime import datetime, timedelta

import requests

_logger = logging.getLogger(__name__)

BASE_URLS = {
    'pruebas':    'https://services.test.sw.com.mx',
    'produccion': 'https://services.sw.com.mx',
}

# Prefijos para las claves en ir.config_parameter
TOKEN_CACHE_KEY  = 'tms.sw_sapien.token.{company_id}'
TOKEN_EXPIRY_KEY = 'tms.sw_sapien.token.expiry.{company_id}'
TOKEN_TTL_MINUTES = 90  # renovar antes de las 2h para seguridad


class SwSapienPac:
    """
    Wrapper REST para el PAC SW Sapien con caché de token JWT.

    Uso:
        pac = SwSapienPac(company, env)
        result = pac.timbrar(xml_sellado_bytes)
    """

    def __init__(self, company, env):
        """
        Args:
            company : res.company con campos sw_usuario, sw_password, sw_ambiente
            env     : entorno Odoo (para acceder a ir.config_parameter)
        """
        self.company  = company
        self.env      = env
        self.base_url = self._get_base_url()

    def _get_base_url(self):
        """Retorna la URL base según sw_ambiente de la empresa."""
        ambiente = self.company.sw_ambiente or 'pruebas'
        return BASE_URLS.get(ambiente, BASE_URLS['pruebas'])

    # ------------------------------------------------------------------
    # Gestión del token JWT
    # ------------------------------------------------------------------

    def _get_token(self):
        """
        Obtiene el Bearer token JWT.
        Primero intenta recuperarlo del caché en ir.config_parameter.
        Si no existe o está expirado, autentica con usuario/password.

        Returns:
            str: Bearer token válido

        Raises:
            Exception: si la autenticación falla
        """
        IrConfig = self.env['ir.config_parameter'].sudo()
        token_key  = TOKEN_CACHE_KEY.format(company_id=self.company.id)
        expiry_key = TOKEN_EXPIRY_KEY.format(company_id=self.company.id)

        token  = IrConfig.get_param(token_key)
        expiry = IrConfig.get_param(expiry_key)

        # Verificar si el token cacheado aún es válido
        if token and expiry:
            try:
                expiry_dt = datetime.fromisoformat(expiry)
                if datetime.now() < expiry_dt:
                    return token
            except ValueError:
                pass  # caché corrupto → re-autenticar

        # Autenticar para obtener nuevo token
        token = self._authenticate()

        # Guardar en caché con TTL de 90 minutos
        nueva_expiry = (datetime.now() + timedelta(minutes=TOKEN_TTL_MINUTES)).isoformat()
        IrConfig.set_param(token_key,  token)
        IrConfig.set_param(expiry_key, nueva_expiry)

        _logger.info(
            'Token SW Sapien renovado para empresa %s (expira en %d min)',
            self.company.name, TOKEN_TTL_MINUTES
        )
        return token

    def _authenticate(self):
        """
        Autentica con SW Sapien y retorna el Bearer token.

        SW Sapien requiere las credenciales como HEADERS HTTP en un GET:
          GET /security/authenticate
          Headers: user: <usuario>
                   password: <contraseña>

        NO registrar usuario/password en logs.
        """
        url = f'{self.base_url}/security/authenticate'
        try:
            resp = requests.get(
                url,
                headers={
                    'user':     self.company.sw_usuario or '',
                    'password': self.company.sw_password or '',
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise Exception(
                'SW Sapien: tiempo de espera agotado al autenticar (30s).'
            )
        except Exception as e:
            raise Exception(
                f'SW Sapien: error al autenticar ({type(e).__name__}). '
                f'Verifica usuario y contraseña en Ajustes → TMS → PAC SW Sapien.'
            )

        token = data.get('data', {}).get('token') or data.get('token')
        if not token:
            status = data.get('status', '')
            msg    = data.get('message', 'Sin detalle')
            raise Exception(
                f'SW Sapien: autenticación rechazada. Status: {status} — {msg}'
            )

        return token

    # ------------------------------------------------------------------
    # Timbrado
    # ------------------------------------------------------------------

    def timbrar(self, xml_sellado_bytes):
        """
        Envía el XML sellado a SW Sapien para timbrado.

        Args:
            xml_sellado_bytes: XML firmado con CSD como bytes

        Returns:
            dict: {
                'uuid':         str,
                'xml_timbrado': bytes,
                'fecha':        str,
                'no_cert_sat':  str,
            }
        """
        token = self._get_token()
        url   = f'{self.base_url}/cfdi33/stamp/v4'

        _logger.info(
            'Timbrado SW Sapien — empresa: %s, ambiente: %s',
            self.company.name, self.company.sw_ambiente
        )

        try:
            xml_b64 = base64.b64encode(xml_sellado_bytes).decode('ascii')
            resp = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type':  'application/json',
                },
                json={'xml': xml_b64},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise Exception(
                'SW Sapien: tiempo de espera agotado al timbrar (30s).'
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Token expirado — limpiar caché y reintentar una vez
                self._clear_token_cache()
                return self.timbrar(xml_sellado_bytes)
            raise Exception(
                f'SW Sapien: error HTTP {e.response.status_code} al timbrar.'
            )
        except Exception as e:
            raise Exception(
                f'SW Sapien: error de conexión al timbrar ({type(e).__name__}).'
            )

        # data.status puede ser '200' o 200
        status = str(data.get('status', ''))
        if status != '200' and not data.get('data', {}).get('uuid'):
            msg = data.get('message', data.get('messageDetail', 'Sin detalle'))
            raise Exception(f'SW Sapien rechazó el CFDI: {msg}')

        result_data = data.get('data', {})
        uuid        = result_data.get('uuid', '')
        xml_tim_b64 = result_data.get('xml', '')
        fecha       = result_data.get('fechaTimbrado', '')
        no_cert_sat = result_data.get('noCertificadoSAT', '')

        xml_timbrado = base64.b64decode(xml_tim_b64) if xml_tim_b64 else xml_sellado_bytes

        _logger.info('Timbrado SW Sapien OK — UUID: %s', uuid)
        return {
            'uuid':         uuid,
            'xml_timbrado': xml_timbrado,
            'fecha':        fecha,
            'no_cert_sat':  no_cert_sat,
        }

    # ------------------------------------------------------------------
    # Cancelación
    # ------------------------------------------------------------------

    def cancelar(self, uuid, motivo):
        """
        Cancela el CFDI vía SW Sapien.

        Args:
            uuid   : UUID del CFDI a cancelar
            motivo : '01','02','03','04' según catálogo SAT

        Returns:
            dict: {'acuse': str, 'estatus': str}
        """
        token = self._get_token()
        url   = f'{self.base_url}/cfdi33/cancel'
        _logger.info('Cancelación SW Sapien — UUID: %s, motivo: %s', uuid, motivo)

        try:
            resp = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type':  'application/json',
                },
                json={
                    'uuid':   uuid,
                    'motivo': motivo,
                    'rfc':    (self.company.vat or '').upper(),
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise Exception(
                f'SW Sapien: error al cancelar ({type(e).__name__}).'
            )

        result_data = data.get('data', {})
        if not result_data and data.get('message'):
            raise Exception(f'SW Sapien cancelación rechazada: {data.get("message")}')

        return {
            'acuse':   result_data.get('acuse', ''),
            'estatus': result_data.get('status', 'cancelado'),
        }

    # ------------------------------------------------------------------
    # Consulta de estatus
    # ------------------------------------------------------------------

    def consultar_estatus(self, uuid):
        """
        Consulta el estatus del CFDI en el SAT vía SW Sapien.

        Returns:
            dict: {'estatus': str, 'cancelable': str}
        """
        token = self._get_token()
        url   = f'{self.base_url}/cfdi33/status'
        _logger.info('Consulta estatus SW Sapien — UUID: %s', uuid)

        try:
            resp = requests.get(
                url,
                headers={'Authorization': f'Bearer {token}'},
                params={'uuid': uuid, 'rfc': (self.company.vat or '').upper()},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise Exception(
                f'SW Sapien: error al consultar estatus ({type(e).__name__}).'
            )

        result_data = data.get('data', {})
        return {
            'estatus':    result_data.get('estado', 'Desconocido'),
            'cancelable': result_data.get('cancelable', 'No'),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clear_token_cache(self):
        """Elimina el token cacheado para forzar re-autenticación."""
        IrConfig = self.env['ir.config_parameter'].sudo()
        IrConfig.set_param(TOKEN_CACHE_KEY.format(company_id=self.company.id),  '')
        IrConfig.set_param(TOKEN_EXPIRY_KEY.format(company_id=self.company.id), '')
