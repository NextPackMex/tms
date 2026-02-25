import sys

def main():
    try:
        Waybill = env['tms.waybill']
        Partner = env['res.partner']
        Vehicle = env['fleet.vehicle']
        Destination = env['tms.destination']
        Employee = env['hr.employee']
        Model = env['fleet.vehicle.model']
        Prod = env['tms.sat.clave.prod']
        Uom = env['tms.sat.clave.unidad']

        print("\n--- INICIANDO QA WORKFLOW COMPLETO (Etapa 2.0.9) ---")
        print("1. Generando datos dinámicos...")

        # Mocks
        brand = env['fleet.vehicle.model.brand'].create({'name': 'Brand QA'})
        modelo_tractor = Model.create({'name': 'Tractor Demo QA', 'brand_id': brand.id})
        v_type = env['tms.vehicle.type'].search([('is_trailer', '=', False)], limit=1)
        if not v_type:
            v_type = env['tms.vehicle.type'].create({'name': 'Tractor Type QA', 'is_trailer': False})

        vehiculo = Vehicle.create({
            'model_id': modelo_tractor.id,
            'license_plate': 'QA-111-XX',
            'tms_is_trailer': False,
            'tms_vehicle_type_id': v_type.id
        })
        
        chofer = Employee.create({
            'name': 'Chofer QA',
            'tms_is_driver': True,
            'tms_driver_license': 'LIC-QA-123'
        })
        
        partner_origin = Partner.create({
            'name': 'Origen QA Aceros',
            'customer_rank': 1,
            'city': 'Monterrey',
            'zip': '64000',
            'vat': 'XAXX010101000'
        })
        partner_dest = Partner.create({
            'name': 'Destino QA',
            'customer_rank': 1,
            'city': 'CDMX',
            'zip': '06000',
            'vat': 'XAXX010101000'
        })
        
        ruta = Destination.create({
            'origin_zip': '64000',
            'dest_zip': '06000',
            'distance_km': 900,
            'duration_hours': 12.5
        })

        # Mocks adiciones (Ciudades)
        mty_city = env['tms.sat.municipio'].search([('name', 'ilike', 'monterrey')], limit=1)
        cdmx_city = env['tms.sat.municipio'].search([('name', 'ilike', 'cuauhtemoc')], limit=1)
        if not mty_city: mty_city = env['tms.sat.municipio'].search([], limit=1)
        if not cdmx_city: cdmx_city = env['tms.sat.municipio'].search([('id', '!=', mty_city.id)], limit=1)

        print("1. Datos Base Creados Correctamente.")

        # 2. Crear Waybill (estado draft)
        wb = Waybill.create({
            'waybill_type': 'income',
            'partner_invoice_id': partner_origin.id,
            'partner_origin_id': partner_origin.id,
            'partner_dest_id': partner_dest.id,
            'origin_city_id': mty_city.id,
            'dest_city_id': cdmx_city.id,
            'route_id': ruta.id,
            'distance_km': ruta.distance_km,
            'duration_hours': ruta.duration_hours,
            'amount_untaxed': 25000.0,
            'vehicle_id': vehiculo.id,
            'driver_id': chofer.id,
        })
        print(f"2. Waybill {wb.id} creado - Estado actual: {wb.state}")

        # Añadir linea de carga
        prod = Prod.search([], limit=1)
        uom = Uom.search([], limit=1)
        
        env['tms.waybill.line'].create({
            'waybill_id': wb.id,
            'product_sat_id': prod.id,
            'description': 'Mercancía QA',
            'quantity': 25,
            'uom_sat_id': uom.id,
            'weight_kg': 15000
        })

        wb._compute_amount_all()
        # Fuerza recomputo y guardar DB
        mty_id = mty_city.id if mty_city else None
        cdmx_id = cdmx_city.id if cdmx_city else None

        env.cr.execute("""
            UPDATE tms_waybill
            SET origin_city_id = %s, dest_city_id = %s
            WHERE id = %s
        """, (mty_id, cdmx_id, wb.id))
        env.invalidate_all()

        # 3. Confirmar (en_pedido)
        wb.action_set_en_pedido()
        print(f"3. Confirmado. Estado actual: {wb.state}")

        # 4. Asignar recurso (assigned)
        wb.write({'vehicle_id': vehiculo.id, 'driver_id': chofer.id})
        wb.action_assign()
        print(f"4. Vehículo y Chofer asignados. Estado actual: {wb.state}")

        # 5. Generar Carta Porte (waybill)
        wb.action_approve_cp()
        print(f"5. Carta Porte generada. Estado actual: {wb.state}")

        # 6. Iniciar Ruta (in_transit)
        wb.action_start_route_manual()
        print(f"6. Ruta iniciada. Estado actual: {wb.state}")

        # 7. Llegada (arrived)
        wb.action_arrived_dest_manual()
        print(f"7. Llegada a destino. Estado actual: {wb.state}")

        print("\n=== SUCCESS: Flujo QA Completo Exitoso ===")

        # Hacemos rollback para mantener BD limpia
        env.cr.rollback()

    except Exception as e:
        print(f"\nFATAL ERROR en QA Workflow: {e}")

if __name__ == '__main__':
    main()
