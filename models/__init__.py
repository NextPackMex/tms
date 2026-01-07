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
from . import res_config_settings     # Configuración
