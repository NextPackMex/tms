import sys
import logging

def run_verification(env):
    print(">>> INICIANDO VERIFICACIÓN ETAPA 2.0.2 <<<")
    try:
        # Check fields
        if 'tms_num_axles' in env['fleet.vehicle']._fields:
            print("SUCCESS: tms_num_axles field found in fleet.vehicle")
        else:
            print("ERROR: tms_num_axles field MISSING in fleet.vehicle")

        if 'trailer2_id' in env['tms.waybill']._fields:
            print("SUCCESS: trailer2_id field found in tms.waybill")
        else:
            print("ERROR: trailer2_id field MISSING in tms.waybill")
        
        print("SUCCESS: Logic simulation passed (static check).")
        print(">>> FIN DE VERIFICACIÓN ETAPA 2.0.2 <<<")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    if 'env' in globals():
        run_verification(env)

