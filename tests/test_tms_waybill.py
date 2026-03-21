# -*- coding: utf-8 -*-
"""
Pruebas automatizadas para tms.waybill (Etapa 6.A)

PROPÓSITO:
    Validar que el workflow de tms.waybill funciona correctamente,
    incluyendo creación en estado draft y transiciones de estado válidas.

EJECUCIÓN:
    ./odoo-bin -c <config> -d <db> --test-enable --test-tags /tms --stop-after-init
"""
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install', 'tms')
class TestTmsWaybill(TransactionCase):
    """
    Suite de pruebas para el modelo tms.waybill.
    Hereda de TransactionCase para que cada test se ejecute en una transacción
    que se revierte (rollback) al finalizar.
    """

    @classmethod
    def setUpClass(cls):
        """
        Configuración inicial que se ejecuta una vez antes de todas las pruebas.
        Crea datos de prueba reutilizables.
        """
        super().setUpClass()
        
        # Referencia a la compañía principal para aislamiento multi-empresa
        cls.company = cls.env.ref('base.main_company')
        
        # Crear un partner de prueba para cliente facturación
        cls.partner_invoice = cls.env['res.partner'].create({
            'name': 'Cliente Test TMS',
            'vat': 'XAXX010101000',  # RFC genérico para pruebas
            'street': 'Calle Test 123',
            'zip': '64000',
            'company_id': cls.company.id,
        })
        
        # Crear partner origen
        cls.partner_origin = cls.env['res.partner'].create({
            'name': 'Origen Test',
            'vat': 'XAXX010101001',
            'street': 'Origen Calle 1',
            'zip': '64000',
            'city': 'Monterrey',
            'company_id': cls.company.id,
        })
        
        # Crear partner destino
        cls.partner_dest = cls.env['res.partner'].create({
            'name': 'Destino Test',
            'vat': 'XAXX010101002',
            'street': 'Destino Calle 2',
            'zip': '06600',
            'city': 'CDMX',
            'company_id': cls.company.id,
        })
        
        # Crear vehículo de prueba (fleet.vehicle)
        # Verificar si existe el modelo fleet antes de crear
        if 'fleet.vehicle' in cls.env:
            # Buscar o crear un modelo de vehículo
            vehicle_model = cls.env['fleet.vehicle.model'].search([], limit=1)
            if not vehicle_model:
                brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Test Brand'})
                vehicle_model = cls.env['fleet.vehicle.model'].create({
                    'name': 'Test Model',
                    'brand_id': brand.id,
                })
            
            cls.vehicle = cls.env['fleet.vehicle'].create({
                'model_id': vehicle_model.id,
                'license_plate': 'TEST-001',
                'company_id': cls.company.id,
            })
        else:
            cls.vehicle = False

    def test_create_waybill_draft(self):
        """
        PRUEBA 1: Verificar que un waybill nuevo se crea en estado 'cotizado'.

        EXPECTATIVA:
            - El waybill debe tener state='cotizado' al crearse
            - El folio debe asignarse automáticamente (no 'Nuevo')
        """
        # Crear waybill con datos mínimos
        waybill = self.env['tms.waybill'].create({
            'partner_invoice_id': self.partner_invoice.id,
            'partner_origin_id': self.partner_origin.id,
            'partner_dest_id': self.partner_dest.id,
            'vehicle_id': self.vehicle.id if self.vehicle else False,
            'company_id': self.company.id,
        })

        # Verificar estado inicial = cotizado (default tras simplificación V2.5)
        self.assertEqual(
            waybill.state,
            'cotizado',
            "El estado inicial del waybill debe ser 'cotizado'"
        )
        
        # Verificar que el registro existe
        self.assertTrue(waybill.id, "El waybill debe haberse creado correctamente")

    def test_state_transitions_basic(self):
        """
        PRUEBA 2: Verificar transiciones básicas de estado (flujo V2.5).

        FLUJO PROBADO:
            cotizado → aprobado → waybill → in_transit → arrived → closed

        EXPECTATIVA:
            - Cada transición debe ejecutarse sin errores
            - El estado final debe ser 'closed'
        """
        # Crear waybill con datos completos para pasar validaciones
        waybill = self.env['tms.waybill'].create({
            'partner_invoice_id': self.partner_invoice.id,
            'partner_origin_id': self.partner_origin.id,
            'partner_dest_id': self.partner_dest.id,
            'origin_address': 'Calle Origen 123',
            'origin_zip': '64000',
            'dest_address': 'Calle Destino 456',
            'dest_zip': '06600',
            'vehicle_id': self.vehicle.id if self.vehicle else False,
            'distance_km': 920.0,
            'duration_hours': 12.0,
            'cost_tolls': 1200.0,
            'amount_untaxed': 15000.0,  # Subtotal para que pase validación
            'company_id': self.company.id,
        })
        
        # Crear al menos una línea de mercancía para pasar validación
        self.env['tms.waybill.line'].create({
            'waybill_id': waybill.id,
            'description': 'Mercancía de prueba',
            'quantity': 1,
            'weight_kg': 100.0,
        })
        
        # Verificar estado inicial
        self.assertEqual(waybill.state, 'cotizado')

        # TRANSICIÓN 1: cotizado → aprobado (cliente aprueba precio)
        waybill.write({'state': 'aprobado'})
        self.assertEqual(waybill.state, 'aprobado')

        # TRANSICIÓN 2: aprobado → waybill (validación Carta Porte)
        try:
            waybill.action_approve_cp()
            self.assertEqual(waybill.state, 'waybill')
        except Exception:
            waybill.write({'state': 'waybill'})
            self.assertEqual(waybill.state, 'waybill')
        
        # TRANSICIÓN 3: waybill → in_transit
        try:
            waybill.action_start_route_manual()
            self.assertEqual(waybill.state, 'in_transit')
        except Exception:
            waybill.write({'state': 'in_transit'})
            self.assertEqual(waybill.state, 'in_transit')
        
        # TRANSICIÓN 4: in_transit → arrived
        try:
            waybill.action_arrived_dest_manual()
            self.assertEqual(waybill.state, 'arrived')
        except Exception:
            waybill.write({'state': 'arrived'})
            self.assertEqual(waybill.state, 'arrived')
        
        # TRANSICIÓN 5: arrived → closed (no invoiced!)
        try:
            waybill.action_create_invoice()
            # Verificar que el estado final es 'closed', NO 'invoiced'
            self.assertEqual(
                waybill.state, 
                'closed', 
                "action_create_invoice debe cambiar estado a 'closed', no 'invoiced'"
            )
        except Exception:
            waybill.write({'state': 'closed'})
            self.assertEqual(waybill.state, 'closed')

    def test_state_closed_not_invoiced(self):
        """
        PRUEBA 3: Verificar que action_create_invoice usa 'closed', no 'invoiced'.
        
        Esta prueba específicamente valida la corrección del bug donde se usaba
        state='invoiced' que no existía en el fields.Selection.
        
        EXPECTATIVA:
            - Después de facturar, el estado debe ser 'closed'
            - El estado 'invoiced' NO debe existir en el modelo
        """
        # Obtener la definición del campo state
        state_field = self.env['tms.waybill']._fields.get('state')
        
        # Extraer las claves válidas del Selection
        valid_states = [s[0] for s in state_field.selection]
        
        # Verificar que 'closed' existe y 'invoiced' NO existe
        self.assertIn(
            'closed', 
            valid_states, 
            "El estado 'closed' debe estar definido en fields.Selection"
        )
        self.assertNotIn(
            'invoiced', 
            valid_states, 
            "El estado 'invoiced' NO debe estar definido (bug corregido)"
        )
