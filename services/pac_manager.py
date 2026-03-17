# -*- coding: utf-8 -*-
"""
Gestor de PACs con failover automático.

Orquesta el timbrado intentando el PAC primario configurado en la empresa
y, si falla y pac_failover=True, intenta automáticamente el PAC secundario.

Integra:
  - FormasDigitalesPac → wrapper REST Formas Digitales
  - SwSapienPac        → wrapper REST SW Sapien

Reglas de negocio:
  - Si PAC 1 falla: log warning (SIN datos sensibles) → intenta PAC 2
  - Si PAC 2 también falla: log error → lanza UserError con ambos mensajes
  - El chatter registra cuántos intentos y qué PAC funcionó
  - NUNCA incluir XML completo en mensajes de error
"""
import logging

from odoo.exceptions import UserError

from .cfdi_errors import traducir_error
from .formas_digitales import FormasDigitalesPac
from .sw_sapien import SwSapienPac

_logger = logging.getLogger(__name__)


class PacManager:
    """
    Gestor principal de PACs con failover.

    Uso desde tms.waybill:
        manager = PacManager(self.env)
        resultado = manager.timbrar(xml_sellado_bytes, self.company_id)
        # resultado = {
        #     'uuid':         str,
        #     'xml_timbrado': bytes,
        #     'pac_usado':    str,
        #     'fecha':        str,
        #     'no_cert_sat':  str,
        # }
    """

    def __init__(self, env):
        """
        Args:
            env: entorno Odoo del waybill (self.env en tms.waybill)
        """
        self.env = env

    # ------------------------------------------------------------------
    # Timbrado con failover
    # ------------------------------------------------------------------

    def timbrar(self, xml_sellado_bytes, company):
        """
        Intenta timbrar en orden según pac_primario de la empresa.
        Si falla el primario y pac_failover=True, intenta el secundario.

        Args:
            xml_sellado_bytes : XML firmado como bytes
            company           : res.company con configuración de PACs

        Returns:
            dict con: uuid, xml_timbrado, pac_usado, fecha, no_cert_sat

        Raises:
            UserError: si todos los PACs disponibles fallan
        """
        pac_order  = self._get_pac_order(company)
        errores    = {}
        resultado  = None

        for pac_type in pac_order:
            pac_instance = self._get_pac_instance(pac_type, company)
            try:
                _logger.info(
                    'Intentando timbrado con PAC: %s (empresa: %s)',
                    pac_type, company.name
                )
                result = pac_instance.timbrar(xml_sellado_bytes)
                resultado = result
                resultado['pac_usado'] = pac_type
                _logger.info(
                    'Timbrado exitoso con %s — UUID: %s',
                    pac_type, result.get('uuid', '')
                )
                break  # éxito — no intentar el siguiente
            except Exception as e:
                msg_error = str(e)
                errores[pac_type] = msg_error
                _logger.warning(
                    'PAC %s falló para empresa %s: %s',
                    pac_type, company.name, msg_error[:200]
                )
                # Continuar con el siguiente PAC si hay failover

        if resultado is None:
            # Todos los PACs fallaron — loggear mensaje RAW completo para diagnóstico
            _logger.error(
                'Todos los PACs fallaron para empresa %s. '
                'Mensajes RAW del PAC (sin truncar): %s',
                company.name,
                {pac: msg for pac, msg in errores.items()},
            )
            errores_traducidos = [
                f'• {traducir_error(msg)}' for msg in errores.values()
            ]
            raise UserError(
                'No se pudo timbrar la Carta Porte:\n\n'
                + '\n'.join(errores_traducidos)
            )

        return resultado

    # ------------------------------------------------------------------
    # Cancelación
    # ------------------------------------------------------------------

    def cancelar(self, uuid, motivo, company):
        """
        Cancela el CFDI usando el PAC indicado en pac_primario de la empresa.
        La cancelación usa el PAC primario siempre (no failover).

        Args:
            uuid    : UUID del CFDI a cancelar
            motivo  : '01','02','03','04' según catálogo SAT
            company : res.company

        Returns:
            dict: {'acuse': str, 'estatus': str}
        """
        pac_type     = company.pac_primario or 'formas_digitales'
        pac_instance = self._get_pac_instance(pac_type, company)

        _logger.info(
            'Cancelando CFDI %s con PAC %s (empresa: %s)',
            uuid, pac_type, company.name
        )

        try:
            if pac_type == 'formas_digitales':
                return pac_instance.cancelar(
                    uuid, motivo,
                    company.tms_csd_cer,
                    company.tms_csd_key,
                    company.tms_csd_password or '',
                )
            else:  # sw_sapien
                return pac_instance.cancelar(uuid, motivo)
        except Exception as e:
            raise UserError(
                f'Error al cancelar el CFDI:\n{traducir_error(str(e))}'
            )

    # ------------------------------------------------------------------
    # Consulta de estatus
    # ------------------------------------------------------------------

    def consultar_estatus(self, uuid, company):
        """
        Consulta el estatus del UUID en el SAT vía el PAC primario.

        Returns:
            dict: {'estatus': str, 'cancelable': str}
        """
        pac_type     = company.pac_primario or 'formas_digitales'
        pac_instance = self._get_pac_instance(pac_type, company)

        _logger.info(
            'Consultando estatus %s con PAC %s (empresa: %s)',
            uuid, pac_type, company.name
        )

        try:
            return pac_instance.consultar_estatus(uuid)
        except Exception as e:
            raise UserError(
                f'Error al consultar estatus del CFDI:\n{traducir_error(str(e))}'
            )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _get_pac_instance(self, pac_type, company):
        """
        Retorna la instancia del PAC correspondiente.

        Args:
            pac_type : 'formas_digitales' o 'sw_sapien'
            company  : res.company con credenciales

        Returns:
            FormasDigitalesPac | SwSapienPac
        """
        if pac_type == 'formas_digitales':
            return FormasDigitalesPac(company)
        elif pac_type == 'sw_sapien':
            return SwSapienPac(company, self.env)
        else:
            raise ValueError(f'PAC desconocido: {pac_type}')

    def _get_pac_order(self, company):
        """
        Retorna la lista ordenada de PACs a intentar.

        Si pac_failover=True: [primario, secundario]
        Si pac_failover=False: [primario]

        Returns:
            list[str]: lista de tipos de PAC en orden de intento
        """
        primario   = company.pac_primario or 'formas_digitales'
        todos      = ['formas_digitales', 'sw_sapien']
        secundario = [p for p in todos if p != primario]

        if company.pac_failover and secundario:
            return [primario] + secundario
        return [primario]
