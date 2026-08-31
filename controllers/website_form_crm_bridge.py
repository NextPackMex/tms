# -*- coding: utf-8 -*-
"""
Puente: formulario de contacto del sitio TMS -> CRM del Odoo remoto (nextpack).

Al enviarse el formulario de contacto, además del comportamiento normal, crea una
oportunidad (crm.lead type=opportunity) en el Odoo remoto vía API XML-RPC.
Credenciales en ir.config_parameter (NO hardcodeadas):

    tms_crm_bridge.url       ej. https://app.nextpack.mx
    tms_crm_bridge.db        ej. nextpack
    tms_crm_bridge.user      usuario de Odoo remoto
    tms_crm_bridge.password  contraseña
    tms_crm_bridge.team_id   (opcional) id del equipo de ventas destino
    tms_crm_bridge.user_id   (opcional) id del usuario responsable (vendedor)

Best-effort: si falta config o la API falla, NO rompe el envío del formulario.
"""
import logging
import ssl
import xmlrpc.client

from odoo import http
from odoo.addons.website.controllers.form import WebsiteForm

_logger = logging.getLogger(__name__)


class WebsiteFormCrmBridge(WebsiteForm):

    @http.route()
    def website_form(self, model_name='', **kwargs):
        response = super().website_form(model_name, **kwargs)
        try:
            self._tms_bridge_create_lead(kwargs)
        except Exception as e:  # nunca romper el form por la integracion
            _logger.warning("TMS->CRM: no se pudo crear el lead remoto: %s", e)
        return response

    def _tms_bridge_create_lead(self, kwargs):
        # detectar el formulario de contacto por sus campos propios
        if 'Pregunta' not in kwargs and 'Nombre' not in kwargs:
            return
        ICP = http.request.env['ir.config_parameter'].sudo()
        url = (ICP.get_param('tms_crm_bridge.url') or '').rstrip('/')
        db = ICP.get_param('tms_crm_bridge.db')
        user = ICP.get_param('tms_crm_bridge.user')
        pwd = ICP.get_param('tms_crm_bridge.password')
        if not (url and db and user and pwd):
            return  # integracion no configurada
        ctx = ssl.create_default_context()
        common = xmlrpc.client.ServerProxy('%s/xmlrpc/2/common' % url, context=ctx)
        uid = common.authenticate(db, user, pwd, {})
        if not uid:
            _logger.warning("TMS->CRM: autenticacion remota fallida")
            return
        models = xmlrpc.client.ServerProxy('%s/xmlrpc/2/object' % url, context=ctx)
        nombre = (kwargs.get('Nombre') or '').strip()
        subject = (kwargs.get('subject') or '').strip()
        vals = {
            'name': subject or ('Contacto web TMS: %s' % (nombre or 'sin nombre')),
            'contact_name': nombre,
            'email_from': (kwargs.get('email_from') or '').strip(),
            'phone': (kwargs.get('Numero Telefonico') or '').strip(),
            'partner_name': (kwargs.get('Empresa') or '').strip(),
            'description': (kwargs.get('Pregunta') or '').strip(),
            'type': 'opportunity',
        }
        team = ICP.get_param('tms_crm_bridge.team_id')
        if team:
            try:
                vals['team_id'] = int(team)
            except (TypeError, ValueError):
                pass
        resp = ICP.get_param('tms_crm_bridge.user_id')
        if resp:
            try:
                vals['user_id'] = int(resp)
            except (TypeError, ValueError):
                pass
        lead_id = models.execute_kw(db, uid, pwd, 'crm.lead', 'create', [vals])
        _logger.info("TMS->CRM: oportunidad remota creada id=%s (%s)", lead_id, vals['email_from'])
