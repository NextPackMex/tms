import sys

def main():
    try:
        print("1. Creating a waybill with INCOMPLETE data to check validations...")
        # Create a basic waybill with DB-required fields but missing validation-required fields
        Waybill = env['tms.waybill']
        partner = env['res.partner'].search([], limit=1)
        vehicle = env['fleet.vehicle'].search([('tms_is_trailer', '=', False)], limit=1)
        city = env['tms.sat.municipio'].search([], limit=1)
        
        # Incomplete waybill: has origin/dest so it passes basic checks, but amount_total=0 
        # and partner vat might be empty.
        wb_incomplete = Waybill.create({
            'waybill_type': 'income',
            'vehicle_id': vehicle.id,
            'partner_invoice_id': partner.id,
            'partner_origin_id': partner.id,
            'origin_city_id': city.id,
            'partner_dest_id': partner.id,
            'dest_city_id': city.id,
            'origin_address': 'Test Orig',
            'origin_zip': '12345',
            'dest_address': 'Test Dest',
            'dest_zip': '54321',
            # We purposely leave amount_total = 0 to trigger _check_waybill_validity
        })
        
        print(f"Waybill {wb_incomplete.id} created in 'draft'. Attempting to advance to assigned...")
        
        try:
            wb_incomplete.action_set_en_pedido()
            wb_incomplete.action_assign()
            # This should trigger _check_waybill_validity somewhere and raise ValidationError
            print("ERROR: Should have failed validation but didn't.")
        except Exception as e:
            print(f"SUCCESS: Validation properly caught missing data: {e}")
            env.cr.rollback()

        print("2. Searching for a complete waybill in the system to test successful transition...")
        partner = env['res.partner'].search([], limit=1)
        vehicle = env['fleet.vehicle'].search([('tms_is_trailer', '=', False)], limit=1)
        city = env['tms.sat.municipio'].search([], limit=1)
        driver = env['hr.employee'].search([('tms_is_driver', '=', True)], limit=1)
        
        # We need a partner with an RFC to pass _check_waybill_validity
        partner_with_rfc = env['res.partner'].search([('vat', '!=', False)], limit=1)
        if not partner_with_rfc:
            partner.vat = 'XAXX010101000'
            partner_with_rfc = partner

        wb_complete = Waybill.create({
            'waybill_type': 'income',
            'partner_invoice_id': partner_with_rfc.id,
            'partner_origin_id': partner_with_rfc.id,
            'origin_city_id': city.id,
            'origin_address': 'Test Orig',
            'origin_zip': '12345',
            'partner_dest_id': partner_with_rfc.id,
            'dest_city_id': city.id,
            'dest_address': 'Test Dest',
            'dest_zip': '54321',
            'vehicle_id': vehicle.id,
            'driver_id': driver.id,
            'distance_km': 100,
            'duration_hours': 2,
            'cost_tolls': 0,
            'amount_untaxed': 1500.0,
            'selected_proposal': 'direct',
            'proposal_direct_amount': 1500.0,
            'state': 'draft',
        })
        
        print(f"Waybill 15 created: {wb_complete.id}. State: {wb_complete.state}")
        
        # We need to compute amount_total explicitly before any flush because Odoo constrains 
        # might be evaluating it as 0 if we write to it indirectly.
        wb_complete._compute_amount_all()
        
        # Force computations
        wb_complete.action_apply_proposal()
        wb_complete._compute_amount_all()
        print(f"Action apply proposal done. State is: {wb_complete.state}")
        env.flush_all()
        
        print(f"Waybill 15 created. Amount Untaxed is: {wb_complete.amount_untaxed}")
        print(f"Waybill 15 created. Amount Total is: {wb_complete.amount_total}")
        
        # Now change to income so it triggers validation but with the right amounts
        wb_complete.waybill_type = 'income'
        env.flush_all()
        
        print(f"Waybill 15 created. Amount Untaxed is: {wb_complete.amount_untaxed}")
        print(f"Waybill 15 created. Amount Total is: {wb_complete.amount_total}")
        
        # Add a line
        prod = env['tms.sat.clave.prod'].search([], limit=1)
        uom = env['tms.sat.clave.unidad'].search([], limit=1)
        
        env['tms.waybill.line'].create({
            'waybill_id': wb_complete.id,
            'product_sat_id': prod.id,
            'description': 'Test cargo',
            'quantity': 10,
            'uom_sat_id': uom.id,
            'weight_kg': 1000
        })
        
        wb_complete._compute_amount_all()
        env.flush_all()
        
        print(f"Waybill {wb_complete.id} created with lines. Amount Total is: {wb_complete.amount_total}. Transitioning...")
        wb_complete.action_set_en_pedido()
        wb_complete.action_assign()
        
        if wb_complete.state == 'assigned':
            print("SUCCESS: Waybill successfully transitioned to 'assigned' state with no AttributeError! Constraints fully working!")
        else:
            print(f"ERROR: Expected state 'assigned', got '{wb_complete.state}'")

    except Exception as e:
        print(f"FATAL ERROR during execution: {e}")

if __name__ == '__main__':
    main()
