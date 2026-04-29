# ============================================================
# CATÁLOGOS SAT (Carta Porte 3.1) - GLOBALES (sin company_id)
# ============================================================
from . import sat_clave_prod          # c_ClaveProdServCP
from . import sat_clave_unidad        # c_ClaveUnidad
from . import sat_embalaje            # c_TipoEmbalaje
from . import sat_material_peligroso  # c_MaterialPeligroso

# Catálogos Geográficos
from . import sat_codigo_postal       # c_CodigoPostal
from . import sat_colonia             # c_Colonia
from . import sat_localidad           # c_Localidad
from . import sat_municipio           # c_Municipio

# Catálogos de Transporte
from . import sat_config_autotransporte  # c_ConfigAutotransporte
from . import sat_tipo_permiso        # c_TipoPermiso
from . import sat_figura_transporte   # c_FiguraTransporte
from . import sat_regimen_fiscal      # c_RegimenFiscal
from . import tms_sat_zona_especial   # Zonas ZEDE (IVA 0%) — global sin company_id

# Catálogos CFDI 4.0
from . import sat_uso_cfdi            # c_UsoCFDI
from . import sat_forma_pago          # c_FormaPago
from . import sat_metodo_pago         # c_MetodoPago
from . import sat_tipo_relacion       # c_TipoRelacion
from . import sat_periodicidad_pago   # c_Periodicidad

# ============================================================
# CATÁLOGOS TMS (GLOBALES — SIN company_id)
# ============================================================
from . import tms_expense_type        # Tipos de Gasto (Diesel, Casetas, etc.)

# ============================================================
# MODELOS OPERATIVOS - PRIVADOS (CON company_id OBLIGATORIO)
# ============================================================
from . import res_company           # Extensión de res.company (Defaults)
from . import res_partner_tms         # Extensión de res.partner
from . import hr_employee             # Extensión de Chofer/Operador
from . import tms_vehicle_type        # Tipos de vehículo
from . import tms_fleet_vehicle       # Extensión de fleet.vehicle
from . import tms_destination         # Destinos/Rutas
from . import tms_waybill             # Modelo Maestro (Viajes)
from . import tms_tracking_event      # Bitácora GPS

from . import tms_fuel_history
from . import tms_route_stats         # Estadísticas de rentabilidad por ruta (V2.4)
from . import tms_vehicle_performance  # Rendimiento acumulado por vehículo (V2.4.3)
from . import tms_expense             # Gasto Real del Viaje (V2.3.3)
from . import tms_driver_advance      # Anticipo al Chofer (V2.3.3)
from . import tms_liquidacion         # Liquidación de Viaje (V2.3.3)
from . import account_move_tms        # Extensión de account.move (CFDI Ingreso TMS)
from . import res_config_settings     # Configuración
from . import res_users_tms           # Extensión de res.users (manejo de grupos TMS)
