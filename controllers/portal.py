# -*- coding: utf-8 -*-
from odoo import http, _, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class TMSCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """
        Prepara valores para el home del portal (contador de waybills).

        Valida que solo se cuenten waybills visibles para el usuario/cliente del portal:
        - Filtra por partner_invoice_id (commercial_partner_id)
        - Filtra por company_id en las empresas del usuario
        - Sin usar sudo() innecesario (usa permisos base.group_portal)
        """
        values = super()._prepare_home_portal_values(counters)
        if 'waybill_count' in counters:
            # Usar commercial_partner_id para manejar contactos hijos correctamente
            partner = request.env.user.partner_id.commercial_partner_id
            # Dominio para contar solo waybills visibles para el usuario/cliente del portal
            # Filtramos por partner y por empresas del usuario (sin sudo, usando permisos de portal)
            domain = [
                ('partner_invoice_id', '=', partner.id),
                ('company_id', 'in', request.env.user.company_ids.ids)
            ]
            # Usar el usuario del request directamente (tiene permisos base.group_portal)
            # Evitar sudo() innecesario - el ACL base.group_portal permite lectura
            values['waybill_count'] = request.env['tms.waybill'].search_count(domain)
        return values

    def _check_waybill_access_and_company(self, waybill_id, access_token=None):
        """
        Valida acceso al waybill y que pertenezca a la empresa correcta (multiempresa SaaS).

        CRÍTICO: Garantiza que un portal user/cliente de Empresa A no pueda ver/firmar/rechazar
        un waybill de Empresa B aunque tenga id y/o access_token.

        Args:
            waybill_id: ID del waybill a validar
            access_token: Token de acceso del portal (opcional)

        Returns:
            waybill_sudo: Recordset del waybill con permisos sudo

        Raises:
            MissingError: Si el waybill no existe o no tiene acceso
            AccessError: Si la empresa no coincide (violación multiempresa)
        """
        # Primero validar acceso por token/permiso (método estándar de portal.mixin)
        waybill_sudo = self._document_check_access('tms.waybill', waybill_id, access_token=access_token)

        # Validación multiempresa: asegurar que el waybill pertenece a una empresa accesible
        # Obtener las empresas a las que el usuario tiene acceso
        user_company_ids = request.env.user.company_ids.ids

        # Si el waybill tiene company_id, debe estar en las empresas del usuario
        if waybill_sudo.company_id and waybill_sudo.company_id.id not in user_company_ids:
            _logger.warning(
                f"TMS PORTAL: Intento de acceso a waybill {waybill_id} de empresa {waybill_sudo.company_id.id} "
                f"por usuario de empresas {user_company_ids}"
            )
            raise MissingError(_("No se encontró el documento solicitado."))

        return waybill_sudo

    @http.route(['/my/waybills/<int:waybill_id>'], type='http', auth="public", website=True)
    def portal_my_waybill(self, waybill_id, access_token=None, report_type=None, download=False, **kw):
        """
        Ruta principal del portal para ver un waybill individual.

        Valida acceso + empresa antes de mostrar el documento.
        Si report_type='pdf', retorna el PDF del reporte.

        Args:
            waybill_id: ID del waybill
            access_token: Token de acceso del portal
            report_type: Tipo de reporte ('pdf' o 'html')
            download: Si True, fuerza descarga del PDF
        """
        _logger.info(f"TMS PORTAL: Accediendo a Waybill {waybill_id}")
        try:
            # Validar acceso y empresa (multiempresa SaaS)
            waybill_sudo = self._check_waybill_access_and_company(waybill_id, access_token=access_token)
        except (AccessError, MissingError) as e:
            _logger.warning(f"TMS PORTAL ERROR: {e}")
            return request.redirect('/my')

        # Si se solicita PDF, retornarlo
        if report_type in ('pdf', 'html') and download:
            return self._show_report(
                model=waybill_sudo,
                report_type=report_type,
                report_ref='tms.action_report_tms_waybill',
                download=download
            )

        # Preparar valores para la plantilla
        values = {
            'waybill': waybill_sudo,
            'token': access_token,
            'page_name': 'waybill',
            'report_type': 'html',
        }
        return request.render("tms.portal_my_waybill", values)

    @http.route(['/my/waybills/<int:waybill_id>/sign'], type='http', auth="public", methods=['POST'], website=True)
    def portal_waybill_sign(self, waybill_id, access_token=None, name=None, signature=None, latitude=None, longitude=None):
        """
        Endpoint para firmar y aceptar un waybill desde el portal.

        Valida acceso + empresa, estado permitido, y guarda firma + nombre + fecha.
        También captura IP y coordenadas si están disponibles.
        Cambia estado a 'aprobado' (cliente aceptó cotización).
        Registra mensaje en chatter si mail.thread existe.

        Args:
            waybill_id: ID del waybill
            access_token: Token de acceso del portal
            name: Nombre de quien firma
            signature: Imagen de la firma en base64
            latitude: Latitud capturada (opcional)
            longitude: Longitud capturada (opcional)
        """
        try:
            # Validar acceso y empresa (multiempresa SaaS)
            waybill_sudo = self._check_waybill_access_and_company(waybill_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Validar que no esté ya firmado (bloqueo de re-firma)
        if waybill_sudo.signature:
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=already_signed'))

        # Validar que el estado permita firma: cotizado o aprobado
        if waybill_sudo.state not in ('cotizado', 'aprobado'):
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=invalid_state'))

        if not signature:
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=missing_signature'))

        try:
            # Obtener IP
            client_ip = request.httprequest.remote_addr or ''

            # Transición de estado: cotizado → aprobado (cliente aceptó precio)
            # aprobado → aprobado (re-firma, mantiene estado)
            new_state = 'aprobado'

            # Guardar firma, nombre, fecha y datos de localización
            waybill_sudo.write({
                'signature': signature,
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'signed_ip': client_ip,
                'signed_latitude': float(latitude) if latitude else 0.0,
                'signed_longitude': float(longitude) if longitude else 0.0,
                'state': new_state,
            })

            # Registrar mensaje en chatter si mail.thread existe
            if hasattr(waybill_sudo, 'message_post'):
                waybill_sudo.message_post(
                    body=_('Cotización firmada y aceptada por %s desde el portal.') % (name or 'Cliente'),
                    subject=_('Cotización Aceptada')
                )

        except Exception as e:
            _logger.error(f"TMS PORTAL ERROR al guardar firma: {e}")
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=save_error'))

        return request.redirect(waybill_sudo.get_portal_url(query_string='&success=true'))

    @http.route(['/my/waybills/<int:waybill_id>/reject'], type='http', auth="public", methods=['POST'], website=True)
    def portal_waybill_reject(self, waybill_id, access_token=None, rejection_reason=None, **kw):
        """
        Endpoint para rechazar un waybill desde el portal.

        Valida acceso + empresa, estado permitido, y guarda motivo de rechazo.
        Cambia estado a 'rejected'.
        Registra mensaje en chatter si mail.thread existe.

        Args:
            waybill_id: ID del waybill
            access_token: Token de acceso del portal
            rejection_reason: Motivo del rechazo (textarea)
        """
        try:
            # Validar acceso y empresa (multiempresa SaaS)
            waybill_sudo = self._check_waybill_access_and_company(waybill_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Validar que el estado permita rechazo: cotizado o aprobado
        if waybill_sudo.state not in ('cotizado', 'aprobado'):
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=invalid_state'))

        if not rejection_reason or not rejection_reason.strip():
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=missing_reason'))

        try:
            # Guardar motivo de rechazo y cambiar estado
            waybill_sudo.write({
                'rejection_reason': rejection_reason.strip(),
                'state': 'rejected',
            })

            # Registrar mensaje en chatter si mail.thread existe
            if hasattr(waybill_sudo, 'message_post'):
                waybill_sudo.message_post(
                    body=_('Cotización rechazada desde el portal.\n\nMotivo:\n%s') % rejection_reason.strip(),
                    subject=_('Cotización Rechazada')
                )

        except Exception as e:
            _logger.error(f"TMS PORTAL ERROR al guardar rechazo: {e}")
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=save_error'))

        return request.redirect(waybill_sudo.get_portal_url(query_string='&rejected=true'))

    @http.route(['/my/waybills/<int:waybill_id>/pdf'], type='http', auth="public", website=True)
    def portal_waybill_pdf(self, waybill_id, access_token=None, download=True, **kw):
        """
        Endpoint seguro para descargar PDF del waybill desde el portal.

        Valida acceso + empresa antes de retornar el PDF.

        Args:
            waybill_id: ID del waybill
            access_token: Token de acceso del portal
            download: Si True, fuerza descarga del PDF
        """
        try:
            # Validar acceso y empresa (multiempresa SaaS)
            waybill_sudo = self._check_waybill_access_and_company(waybill_id, access_token=access_token)
        except (AccessError, MissingError):
            # Retornar 404 si no tiene acceso (seguridad)
            return request.not_found()

        # Retornar PDF usando el método estándar de portal
        return self._show_report(
            model=waybill_sudo,
            report_type='pdf',
            report_ref='tms.action_report_tms_waybill',
            download=download
        )
