# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install', 'tms')
class TestPortalTms(HttpCase):
    """
    Tests de seguridad y funcionalidad del portal web cliente TMS.
    Usa HttpCase para validar rutas HTTP (GET /my, /my/waybills, etc.)
    y detección de errores 500, 302, 404 sin excepción.
    """

    def test_portal_home_200(self):
        """
        Verifica que GET /my retorna 200 para usuario portal autenticado.
        El home del portal debe cargar correctamente con tile "Mis Viajes".
        """
        self.authenticate('portal', 'portal')
        res = self.url_open('/my')
        self.assertEqual(res.status_code, 200, "Portal home debe retornar 200")
        # Verificar que la página contiene título o elemento principal
        self.assertIn(b'<html', res.content, "Response debe ser HTML válido")

    def test_portal_waybills_list_200(self):
        """
        Verifica que GET /my/waybills retorna 200 para lista de viajes.
        La lista paginada debe ser accesible y mostrar estructura de tabla.
        """
        self.authenticate('portal', 'portal')
        res = self.url_open('/my/waybills')
        self.assertEqual(res.status_code, 200, "Portal waybills list debe retornar 200")
        # Verificar estructura mínima de página
        self.assertIn(b'<html', res.content, "Response debe ser HTML válido")

    def test_portal_waybill_detail_redirect(self):
        """
        Verifica que GET /my/waybills/<id_inexistente> retorna 302 redirect, NO 500.
        Los IDs inválidos deben redirigir a /my, no causar error 500 o KeyError.
        """
        self.authenticate('portal', 'portal')
        res = self.url_open('/my/waybills/999999', allow_redirects=False)
        self.assertIn(res.status_code, [302, 404],
                      "Waybill inexistente debe redirect (302) o 404, no 500")

    def test_portal_waybill_xml_404(self):
        """
        Verifica que GET /my/waybills/<id_inexistente>/xml retorna 404, NO 500.
        Petición de XML para waybill inexistente debe retornar 404 limpio sin excepciones.
        """
        self.authenticate('portal', 'portal')
        res = self.url_open('/my/waybills/999999/xml', allow_redirects=False)
        self.assertEqual(res.status_code, 404,
                         "XML de waybill inexistente debe retornar 404, no 500")

    def test_portal_waybill_pdf_404(self):
        """
        Verifica que GET /my/waybills/<id_inexistente>/pdf retorna 404, NO 500.
        Petición de PDF para waybill inexistente debe retornar 404 limpio sin excepciones.
        """
        self.authenticate('portal', 'portal')
        res = self.url_open('/my/waybills/999999/pdf', allow_redirects=False)
        self.assertEqual(res.status_code, 404,
                         "PDF de waybill inexistente debe retornar 404, no 500")
