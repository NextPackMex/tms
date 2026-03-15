# -*- coding: utf-8 -*-
"""
Tests unitarios para tms.onboarding.wizard (Etapa 2.1.5).

Ejecutar:
    ./odoo-bin -c odoo.conf -d tms_dev --test-enable --test-tags /tms -u tms --stop-after-init
"""
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'tms')
class TestOnboardingWizard(TransactionCase):
    """Tests para el wizard de onboarding TMS de 6 pasos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.wizard = cls.env['tms.onboarding.wizard'].create({
            'company_id': cls.company.id,
        })

    def test_01_wizard_creacion_inicial(self):
        """El wizard se crea en el paso 1 por defecto."""
        self.assertEqual(
            self.wizard.step, 1,
            'El wizard debe iniciar en el paso 1'
        )
        self.assertEqual(
            self.wizard.company_id, self.company,
            'El wizard debe tener la empresa del usuario actual'
        )

    def test_02_navegacion_siguiente(self):
        """action_next_step avanza el paso correctamente."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'step': 1,
        })
        wizard.action_next_step()
        self.assertEqual(wizard.step, 2, 'Debe avanzar del paso 1 al 2')
        wizard.action_next_step()
        self.assertEqual(wizard.step, 3, 'Debe avanzar del paso 2 al 3')

    def test_03_navegacion_no_pasa_de_6(self):
        """action_next_step no supera el paso 6."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'step': 6,
        })
        wizard.action_next_step()
        self.assertEqual(wizard.step, 6, 'El paso no debe superar 6')

    def test_04_navegacion_anterior(self):
        """action_prev_step retrocede el paso correctamente."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'step': 3,
        })
        wizard.action_prev_step()
        self.assertEqual(wizard.step, 2, 'Debe retroceder del paso 3 al 2')

    def test_05_navegacion_no_baja_de_1(self):
        """action_prev_step no baja del paso 1."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'step': 1,
        })
        wizard.action_prev_step()
        self.assertEqual(wizard.step, 1, 'El paso no debe bajar de 1')

    def test_06_paso1_guarda_empresa(self):
        """action_save_step_1 escribe nombre y RFC en res.company."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'company_name': 'Transportes Test SA de CV',
            'company_rfc': 'TTT200101ABC',
            'step': 1,
        })
        wizard.action_save_step_1()
        self.assertEqual(
            self.company.name, 'Transportes Test SA de CV',
            'El nombre de la empresa debe actualizarse'
        )
        self.assertEqual(
            self.company.vat, 'TTT200101ABC',
            'El RFC de la empresa debe actualizarse'
        )
        self.assertEqual(wizard.step, 2, 'Debe avanzar al paso 2 después de guardar')

    def test_07_paso2_crea_vehiculo(self):
        """action_save_step_2 crea un vehículo fleet.vehicle."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'vehicle_name': 'Kenworth T680 Test',
            'vehicle_plate': 'TEST-001',
            'step': 2,
        })
        count_before = self.env['fleet.vehicle'].search_count([
            ('company_id', '=', self.company.id),
            ('name', '=', 'Kenworth T680 Test'),
        ])
        wizard.action_save_step_2()
        count_after = self.env['fleet.vehicle'].search_count([
            ('company_id', '=', self.company.id),
            ('name', '=', 'Kenworth T680 Test'),
        ])
        self.assertEqual(
            count_after, count_before + 1,
            'Debe crearse 1 vehículo tracto'
        )
        self.assertEqual(wizard.step, 3, 'Debe avanzar al paso 3')

    def test_08_paso2_crea_remolque(self):
        """action_save_step_2 crea remolque cuando has_trailer=True."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'vehicle_name': 'Tracto Principal',
            'has_trailer': True,
            'trailer_name': 'Remolque 53ft Test',
            'trailer_plate': 'REM-001',
            'step': 2,
        })
        wizard.action_save_step_2()
        remolque = self.env['fleet.vehicle'].search([
            ('company_id', '=', self.company.id),
            ('name', '=', 'Remolque 53ft Test'),
            ('tms_is_trailer', '=', True),
        ])
        self.assertTrue(remolque, 'Debe crearse el remolque con tms_is_trailer=True')

    def test_09_paso3_guarda_seguros(self):
        """action_save_step_3 guarda datos de seguros en res.company."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'insurance_rc_company': 'Qualitas Test',
            'insurance_rc_policy': 'POL-TEST-001',
            'step': 3,
        })
        wizard.action_save_step_3()
        self.assertEqual(
            self.company.tms_insurance_rc_company, 'Qualitas Test',
            'La aseguradora RC debe guardarse en la empresa'
        )
        self.assertEqual(
            self.company.tms_insurance_rc_policy, 'POL-TEST-001',
            'La póliza RC debe guardarse en la empresa'
        )

    def test_10_paso4_crea_chofer(self):
        """action_save_step_4 crea un hr.employee con datos de licencia."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'driver_name': 'Chofer Test TMS',
            'driver_license_number': 'LIC-TEST-001',
            'driver_license_type': 'B',
            'step': 4,
        })
        wizard.action_save_step_4()
        emp = self.env['hr.employee'].search([
            ('company_id', '=', self.company.id),
            ('name', '=', 'Chofer Test TMS'),
        ], limit=1)
        self.assertTrue(emp, 'Debe crearse el empleado chofer')
        self.assertEqual(
            emp.tms_license_number, 'LIC-TEST-001',
            'El número de licencia debe guardarse'
        )
        self.assertEqual(
            emp.tms_license_type, 'B',
            'El tipo de licencia debe guardarse'
        )

    def test_11_paso5_crea_cliente(self):
        """action_save_step_5 crea un res.partner con datos del cliente."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'client_name': 'Cliente Test SA de CV',
            'client_rfc': 'CTE200101XYZ',
            'client_is_company': True,
            'step': 5,
        })
        wizard.action_save_step_5()
        partner = self.env['res.partner'].search([
            ('name', '=', 'Cliente Test SA de CV'),
        ], limit=1)
        self.assertTrue(partner, 'Debe crearse el partner cliente')
        self.assertEqual(
            partner.vat, 'CTE200101XYZ',
            'El RFC del cliente debe guardarse'
        )
        self.assertTrue(partner.is_company, 'El cliente debe ser persona moral')

    def test_12_paso5_no_crea_sin_nombre(self):
        """action_save_step_5 no crea partner si client_name está vacío."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'step': 5,
        })
        count_before = self.env['res.partner'].search_count([])
        wizard.action_save_step_5()
        count_after = self.env['res.partner'].search_count([])
        self.assertEqual(
            count_before, count_after,
            'No debe crearse partner si client_name está vacío'
        )

    def test_13_summary_compute(self):
        """_compute_summary genera texto correcto según campos llenados."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
            'company_name': 'Empresa Test',
            'vehicle_name': 'Vehículo Test',
            'driver_name': 'Chofer Test',
            'client_name': 'Cliente Test',
            'insurance_rc_policy': 'POL-001',
            'insurance_cargo_policy': 'POL-002',
        })
        self.assertEqual(wizard.summary_company, 'Empresa Test')
        self.assertEqual(wizard.summary_vehicle, 'Vehículo Test')
        self.assertEqual(wizard.summary_driver, 'Chofer Test')
        self.assertEqual(wizard.summary_client, 'Cliente Test')
        self.assertEqual(wizard.summary_insurance, '2/3 seguros configurados')

    def test_14_summary_sin_datos(self):
        """_compute_summary muestra 'Sin configurar' cuando no hay datos."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
        })
        self.assertEqual(wizard.summary_company, 'Sin configurar')
        self.assertEqual(wizard.summary_vehicle, 'Sin configurar')
        self.assertEqual(wizard.summary_insurance, '0/3 seguros configurados')

    def test_15_action_create_first_trip(self):
        """action_create_first_trip retorna acción al wizard de cotización."""
        wizard = self.env['tms.onboarding.wizard'].create({
            'company_id': self.company.id,
        })
        result = wizard.action_create_first_trip()
        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        self.assertEqual(result.get('res_model'), 'tms.cotizacion.wizard')
        self.assertEqual(result.get('target'), 'new')
