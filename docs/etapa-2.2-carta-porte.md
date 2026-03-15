# SDD — Etapa V2.2: Carta Porte 3.1 + Timbrado Dual PAC
**Módulo:** `tms/` | **Fecha:** 2026-03-15 | **Prioridad:** CRÍTICA | **Branch:** `feat/etapa-2.2-carta-porte`

---

## GIT
```bash
git checkout main && git pull origin main
git checkout feat/etapa-2.2-carta-porte
# La rama ya existe — no crear nueva
```

---

## PROBLEMA
El TMS tiene toda la estructura de Carta Porte 3.1 (campos SAT, validaciones, UUID) pero NO tiene el motor de timbrado. No se puede generar un CFDI 4.0 válido ni sellarlo ante el SAT.

---

## SOLUCIÓN
Implementar Opción B — XML propio con `lxml` + `cryptography`, sin depender de `l10n_mx_edi`. Dos PACs con failover automático: Formas Digitales (primario) + SW Sapien (respaldo).

```
FLUJO COMPLETO:
waybill en estado 'waybill'
    ↓
Botón "Timbrar Carta Porte"
    ↓
xml_builder.py → construye XML CFDI 4.0 + Complemento CP 3.1
    ↓
xml_signer.py → firma con CSD (.cer + .key + contraseña)
    ↓
pac_manager.py → intenta PAC 1 (Formas Digitales)
    ↓ falla?
pac_manager.py → intenta PAC 2 (SW Sapien)
    ↓
Guarda: UUID, XML timbrado, fecha, PAC usado
    ↓
Estado → in_transit (o el que corresponda)
```

---

## DECISIÓN ARQUITECTÓNICA
**Opción B seleccionada:** XML propio con `lxml` + `cryptography`
- SIN dependencia de `l10n_mx_edi`
- SIN dependencia de `account_edi`
- Control total del XML generado
- Compatible con cualquier PAC
- lxml y cryptography ya disponibles en el venv de Odoo 19

---

## CAMBIOS

### File Manifest

| Archivo | Acción | Agente |
|---|---|---|
| `models/res_company.py` | Modificar — credenciales FD + SW Sapien | A |
| `models/tms_waybill.py` | Modificar — campos post-timbrado + 3 métodos | A |
| `services/__init__.py` | Crear nuevo | B |
| `services/pac_manager.py` | Crear nuevo | B |
| `services/formas_digitales.py` | Crear nuevo | B |
| `services/sw_sapien.py` | Crear nuevo | B |
| `services/xml_builder.py` | Crear nuevo | B |
| `services/xml_signer.py` | Crear nuevo | B |
| `views/res_config_settings_views.xml` | Modificar — sección dual PAC | C |
| `views/tms_waybill_views.xml` | Modificar — botones timbrar/cancelar/estatus | C |
| `__manifest__.py` | Modificar — agregar carpeta services/ | A |

---

## CAMPOS NUEVOS

### res.company — Formas Digitales
```python
fd_usuario = fields.Char(
    string='Usuario Formas Digitales',
    help='Usuario de la cuenta en Formas Digitales (forsedi)'
)
fd_password = fields.Char(
    string='Contraseña Formas Digitales'
)
fd_user_id = fields.Char(
    string='User ID Formas Digitales',
    help='ID de usuario proporcionado por Formas Digitales'
)
fd_ambiente = fields.Selection([
    ('pruebas',    'Pruebas — dev33.facturacfdi.mx'),
    ('produccion', 'Producción — v33.facturacfdi.mx'),
], string='Ambiente FD', default='pruebas')
```

### res.company — SW Sapien
```python
sw_usuario = fields.Char(
    string='Usuario SW Sapien',
    help='Email de la cuenta en SW Sapien (sw.com.mx)'
)
sw_password = fields.Char(
    string='Contraseña SW Sapien'
)
sw_ambiente = fields.Selection([
    ('pruebas',    'Pruebas — services.test.sw.com.mx'),
    ('produccion', 'Producción — services.sw.com.mx'),
], string='Ambiente SW', default='pruebas')
```

### res.company — Control dual PAC
```python
pac_primario = fields.Selection([
    ('formas_digitales', 'Formas Digitales'),
    ('sw_sapien',        'SW Sapien'),
], string='PAC Primario', default='formas_digitales',
   help='PAC que se intentará primero al timbrar'
)
pac_failover = fields.Boolean(
    string='Activar failover automático',
    default=True,
    help='Si el PAC primario falla, intentar automáticamente con el secundario'
)
```

### tms.waybill — Campos post-timbrado
```python
cfdi_uuid = fields.Char(
    string='UUID CFDI',
    readonly=True,
    copy=False,
    help='Folio fiscal del CFDI timbrado por el SAT'
)
cfdi_xml = fields.Binary(
    string='XML Timbrado',
    readonly=True,
    copy=False,
    attachment=True,
    help='XML del CFDI con el Timbre Fiscal Digital'
)
cfdi_xml_fname = fields.Char(
    string='Nombre XML',
    readonly=True
)
cfdi_fecha = fields.Datetime(
    string='Fecha timbrado',
    readonly=True
)
cfdi_pac = fields.Char(
    string='PAC usado',
    readonly=True,
    help='Nombre del PAC que realizó el timbrado'
)
cfdi_no_cert_sat = fields.Char(
    string='No. Certificado SAT',
    readonly=True
)
cfdi_status = fields.Selection([
    ('none',      'Sin timbrar'),
    ('timbrado',  'Timbrado'),
    ('cancelado', 'Cancelado'),
    ('error',     'Error'),
], string='Estatus CFDI', default='none', readonly=True,
   tracking=True
)
cfdi_error_msg = fields.Text(
    string='Último error CFDI',
    readonly=True
)
```

---

## SERVICIOS A IMPLEMENTAR

### services/xml_builder.py
```python
class CartaPorteXmlBuilder:
    """
    Construye el XML CFDI 4.0 con Complemento Carta Porte 3.1
    a partir de un tms.waybill. Usa lxml para construcción.

    Namespaces requeridos:
    - cfdi:         http://www.sat.gob.mx/cfd/4
    - cartaporte31: http://www.sat.gob.mx/CartaPorte31
    - xsi:          http://www.w3.org/2001/XMLSchema-instance

    NO depende de l10n_mx_edi — implementación propia completa.
    """

    def build(self, waybill):
        """Retorna XML sin sellar como bytes. El sellado lo hace xml_signer."""

    def _build_comprobante(self, waybill):
        """Nodo raíz cfdi:Comprobante con atributos CFDI 4.0"""

    def _build_emisor(self, company):
        """cfdi:Emisor con RFC, Nombre, RegimenFiscal"""

    def _build_receptor(self, waybill):
        """cfdi:Receptor con RFC, Nombre, DomicilioFiscalReceptor, UsoCFDI=CP01"""

    def _build_conceptos(self, waybill):
        """
        cfdi:Conceptos — servicio de autotransporte de carga.
        ClaveProdServ: 78101800 (Servicios de transporte de carga)
        ClaveUnidad:   E48 (Unidad de servicio)
        """

    def _build_impuestos(self, waybill):
        """
        cfdi:Impuestos
        - Traslado IVA 16% siempre
        - Retención IVA 4% solo si partner_invoice_id.is_company == True
        """

    def _build_complemento_carta_porte(self, waybill):
        """
        cartaporte31:CartaPorte Version="3.1"
        Incluye:
        - Ubicaciones: TipoUbicacion Origen + Destino
        - Mercancias: todas las líneas del waybill
        - Autotransporte: vehículo + remolques + permisos SCT
        - FiguraTransporte: chofer con licencia federal
        """

    def _build_ubicaciones(self, waybill):
        """
        Origen: TipoUbicacion="Origen", IDUbicacion="OR000001"
        Destino: TipoUbicacion="Destino", IDUbicacion="DE000001"
        Domicilio con CodigoPostal, Estado, Pais="MEX"
        """

    def _build_mercancias(self, waybill):
        """
        Una cartaporte31:Mercancia por cada tms.waybill.line.
        Campos requeridos: BienesTransp (clave SAT), Descripcion,
        Cantidad, ClaveUnidad, PesoEnKg, Dimensiones
        """

    def _build_autotransporte(self, waybill):
        """
        cartaporte31:Autotransporte con:
        - PermSCT (tipo permiso SCT)
        - NumPermisoSCT
        - IdentificacionVehicular (AnioModeloVM, CoordenadasVehiculo)
        - Seguros (RC obligatorio, Carga opcional, Ambiental si peligroso)
        - Remolques si aplica
        """

    def _build_figura_transporte(self, waybill):
        """
        cartaporte31:FiguraTransporte
        TipoFigura="01" (Operador)
        RFC, Nombre, NumLicencia del chofer
        """
```

### services/xml_signer.py
```python
class CfdiSigner:
    """
    Firma el XML CFDI con el CSD del emisor.
    Usa: cryptography, lxml, base64, hashlib

    Proceso completo:
    1. Decodificar .cer (base64) → obtener NoCertificado y certificado en base64
    2. Decodificar .key (base64) → desencriptar con contraseña usando cryptography
    3. Aplicar XSLT SAT para obtener cadena original
    4. Firmar cadena original con SHA256withRSA
    5. Codificar sello en base64
    6. Insertar Sello, Certificado, NoCertificado en el XML
    7. Retornar XML sellado como bytes
    """

    XSLT_CFDI40_URL = 'http://www.sat.gob.mx/sitio_internet/cfd/4/cadenaoriginal_TFD_1_1.xslt'

    def sign(self, xml_bytes, csd_cer_b64, csd_key_b64, password):
        """
        Parámetros:
          xml_bytes   : XML sin sellar como bytes
          csd_cer_b64 : contenido del .cer en base64 (de res.company.tms_csd_cer)
          csd_key_b64 : contenido del .key en base64 (de res.company.tms_csd_key)
          password    : contraseña del .key como string

        Retorna: XML sellado como bytes, listo para enviar al PAC
        """

    def _get_no_certificado(self, cer_bytes):
        """Extrae el número de serie del certificado (20 dígitos)"""

    def _get_certificado_b64(self, cer_bytes):
        """Retorna el certificado en base64 sin saltos de línea"""

    def _load_private_key(self, key_bytes, password):
        """
        Carga y desencripta la llave privada .key del SAT.
        El .key del SAT usa formato PKCS#8 encriptado con 3DES.
        """

    def _generate_cadena_original(self, xml_tree):
        """
        Aplica el XSLT del SAT para obtener la cadena original.
        Descargar XSLT si no existe en caché local.
        """
```

### services/pac_manager.py
```python
class PacManager:
    """
    Gestor de PACs con failover automático.

    Uso desde tms.waybill:
        manager = PacManager(self.env)
        resultado = manager.timbrar(xml_sellado, self.company_id)
        # resultado = {'uuid': ..., 'xml': ..., 'pac': ..., 'fecha': ...}
    """

    def __init__(self, env):
        self.env = env

    def timbrar(self, xml_sellado_bytes, company):
        """
        Intenta timbrar en orden según pac_primario de la empresa.
        Si falla el primario y pac_failover=True, intenta el secundario.
        Registra en _logger qué PAC se usó (nunca el XML completo).
        Retorna dict con uuid, xml_timbrado, pac_usado, fecha_timbrado.
        Lanza UserError si todos los PACs fallan.
        """

    def cancelar(self, uuid, motivo, company):
        """
        Cancela usando el PAC registrado en cfdi_pac del waybill.
        Motivo SAT: '01' sustitución, '02' comprobante emitido error RFC,
                    '03' no se llevó a cabo la operación, '04' operación nominativa
        """

    def consultar_estatus(self, uuid, company):
        """Consulta estatus del UUID en el SAT vía el PAC configurado."""

    def _get_pac_instance(self, pac_type, company):
        """
        Retorna instancia del PAC correcto según pac_type.
        'formas_digitales' → FormasDigitalesPac(company)
        'sw_sapien'        → SwSapienPac(company)
        """

    def _get_pac_order(self, company):
        """
        Retorna lista de PACs en el orden de intento.
        Ej: ['formas_digitales', 'sw_sapien'] si primario es FD.
        Si pac_failover=False, retorna solo [pac_primario].
        """
```

### services/formas_digitales.py
```python
class FormasDigitalesPac:
    """
    Wrapper para la API REST de Formas Digitales (forsedi.facturacfdi.mx).

    URLs por ambiente:
    Pruebas:    https://dev33.facturacfdi.mx
    Producción: https://v33.facturacfdi.mx

    Autenticación: usuario + password en cada request (Basic Auth o header)
    Timeout: 30 segundos en todas las llamadas
    """

    def __init__(self, company):
        self.company = company
        self.base_url = self._get_base_url()

    def _get_base_url(self):
        """Retorna URL según fd_ambiente de la empresa."""

    def timbrar(self, xml_sellado_bytes):
        """
        POST al endpoint de timbrado.
        Retorna dict: {uuid, xml_timbrado, fecha, no_cert_sat}
        Lanza Exception con mensaje claro si falla.
        NUNCA incluir el XML completo en el mensaje de error.
        """

    def cancelar(self, uuid, motivo, cer_b64, key_b64, password):
        """Cancelación con CSD (método 1)."""

    def consultar_estatus(self, uuid):
        """Consulta estatus del UUID."""
```

### services/sw_sapien.py
```python
class SwSapienPac:
    """
    Wrapper para la API REST de SW Sapien (sw.com.mx / smarterweb.com.mx).

    URLs por ambiente:
    Pruebas:    https://services.test.sw.com.mx
    Producción: https://services.sw.com.mx

    Autenticación: Bearer token JWT (válido ~2 horas)
    El token se cachea en ir.config_parameter para no autenticar en cada llamada.

    Endpoints (path dice cfdi33 pero acepta CFDI 4.0):
    POST /cfdi33/stamp/v4   → timbrar XML sellado
    POST /cfdi33/cancel     → cancelar
    GET  /cfdi33/status     → estatus
    """

    TOKEN_CACHE_KEY = 'tms.sw_sapien.token.{company_id}'
    TOKEN_EXPIRY_KEY = 'tms.sw_sapien.token.expiry.{company_id}'

    def __init__(self, company):
        self.company = company
        self.base_url = self._get_base_url()

    def _get_base_url(self):
        """Retorna URL según sw_ambiente de la empresa."""

    def _get_token(self):
        """
        Obtiene Bearer token desde caché o autenticando.
        Cachea en ir.config_parameter con expiración de 90 minutos
        (token válido 2h, renovar antes para seguridad).
        """

    def timbrar(self, xml_sellado_bytes):
        """
        POST /cfdi33/stamp/v4 con Authorization: Bearer {token}
        Retorna dict: {uuid, xml_timbrado, fecha, no_cert_sat}
        Lanza Exception con mensaje claro si falla.
        """

    def cancelar(self, uuid, motivo):
        """Cancelación via SW Sapien."""

    def consultar_estatus(self, uuid):
        """Consulta estatus del UUID."""
```

---

## MÉTODOS EN tms.waybill

```python
def action_stamp_cfdi(self):
    """
    Timbra la Carta Porte 3.1 del waybill.
    Solo ejecutable en estado 'waybill'.

    Flujo:
    1. Construir XML con CartaPorteXmlBuilder
    2. Firmar XML con CfdiSigner usando CSD de la empresa
    3. Enviar a PAC via PacManager (con failover automático)
    4. Guardar UUID, XML, fecha, PAC en campos cfdi_*
    5. Registrar en chatter: UUID + PAC usado
    6. Cambiar cfdi_status a 'timbrado'
    """

def action_cancel_cfdi(self):
    """
    Cancela el CFDI timbrado.
    Solo ejecutable cuando cfdi_status='timbrado'.
    Abre wizard para seleccionar motivo de cancelación SAT.
    """

def action_check_cfdi_status(self):
    """
    Consulta el estatus del CFDI en el SAT.
    Actualiza cfdi_status según respuesta.
    Muestra resultado en notificación.
    """

def action_download_cfdi_xml(self):
    """
    Descarga el XML timbrado como archivo adjunto.
    Solo disponible cuando cfdi_status='timbrado'.
    """
```

---

## ACCEPTANCE CRITERIA

| ID | Criterio | Cómo verificar |
|---|---|---|
| AC-01 | Botón "Timbrar" visible solo en estado 'waybill' | Cambiar estado y verificar visibilidad |
| AC-02 | XML CFDI 4.0 generado es válido | Validar con herramienta SAT |
| AC-03 | XML firmado con CSD FUNK671228PH6 | Ver NoCertificado en el XML |
| AC-04 | Timbrado exitoso con Formas Digitales pruebas | UUID retornado y guardado |
| AC-05 | Si FD falla, intenta SW Sapien automáticamente | Simular error FD, verificar intento SW |
| AC-06 | UUID, XML, fecha guardados en el waybill | Verificar campos cfdi_* |
| AC-07 | Botón "Cancelar" visible solo cuando timbrado | Verificar con cfdi_status='timbrado' |
| AC-08 | Cancelación exitosa en pruebas | Estado cambia a 'cancelado' |
| AC-09 | Botón "Consultar estatus SAT" funciona | Muestra estatus correcto |
| AC-10 | Chatter registra UUID + PAC usado | Ver log en el waybill |
| AC-11 | Credenciales configurables en res.company | Guardar y leer correctamente |
| AC-12 | Radio pruebas/producción independiente por PAC | Cambiar y verificar URL usada |
| AC-13 | Credenciales NO aparecen en logs de Odoo | grep en odoo.log |
| AC-14 | Token SW Sapien se cachea (no autentica en cada timbre) | Verificar ir.config_parameter |

---

## UPGRADE COMMAND
```bash
cd /Users/macbookpro/odoo/odoo19ce
odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin \
  -c proyectos/tms/odoo.conf -d tms_v2 -u tms --stop-after-init
```

---

## ROLLBACK
```bash
git checkout main
# Campos nuevos en BD no se eliminan pero no rompen nada
# Para limpiar campos: ALTER TABLE res_company DROP COLUMN IF EXISTS fd_usuario; etc.
```

---

## CONTEXT BLUEPRINT PARA AGENTES

### Modelos existentes — NO modificar estructura
```
tms.waybill          _name = 'tms.waybill'
tms.waybill.line     _name = 'tms.waybill.line'
tms.sat.codigo.postal _name = 'tms.sat.codigo.postal'
tms.sat.clave.prod   _name = 'tms.sat.clave.prod'
tms.sat.figura.transporte _name = 'tms.sat.figura.transporte'
```

### Campos existentes clave en tms.waybill
```python
tms_id_ccp          # UUID Carta Porte — YA EXISTE, no crear otro
origin_zip          # CP origen → tms.sat.codigo.postal
dest_zip            # CP destino → tms.sat.codigo.postal
vehicle_id          # fleet.vehicle (tracto)
trailer1_id         # fleet.vehicle (remolque 1)
dolly_id            # fleet.vehicle (dolly)
trailer2_id         # fleet.vehicle (remolque 2)
driver_id           # hr.employee (chofer)
line_ids            # tms.waybill.line (mercancías)
partner_invoice_id  # res.partner (cliente facturación)
partner_origin_id   # res.partner (remitente)
partner_dest_id     # res.partner (destinatario)
amount_untaxed      # subtotal del flete
```

### Campos existentes en tms.waybill.line
```python
name                # descripción de la mercancía
product_sat_id      # tms.sat.clave.prod (BienesTransp)
uom_sat_id          # tms.sat.clave.unidad (ClaveUnidad)
quantity            # cantidad
weight_kg           # peso en kg
is_dangerous        # Boolean — materiales peligrosos
dim_largo           # Float — largo en cm
dim_ancho           # Float — ancho en cm
dim_alto            # Float — alto en cm
dimensions          # computed '000/000/000cm' (formato SAT)
```

### Campos existentes en res.company
```python
tms_csd_cer         # Binary — certificado público (.cer)
tms_csd_key         # Binary — llave privada (.key)
tms_csd_password    # Char — contraseña del .key
tms_regimen_fiscal  # Selection — régimen fiscal SAT
vat                 # RFC de la empresa (campo estándar Odoo)
name                # Nombre de la empresa
```

### Certificados de prueba disponibles en la BD
```
Empresa activa: MARTHA LAURA FUNK WEIMBERG
RFC:            FUNK671228PH6
Régimen:        612
CSD cargados:   FUNK671228PH6.cer + FUNK671228PH6.key
Contraseña:     12345678
```

### Credenciales PAC pruebas
```
Formas Digitales:
  URL pruebas:  https://dev33.facturacfdi.mx
  Documentar URL endpoints al inspeccionar la API

SW Sapien:
  URL pruebas:  https://services.test.sw.com.mx
  Usuario:      demo@sw.com.mx
  Password:     123456789
  Doc API:      https://developers.sw.com.mx
```

---

## INSTRUCCIONES PARA EL ORQUESTADOR

```
AGENTE A — models/ (rama: feat/etapa-2.2-models)
Archivos a modificar:
  - models/res_company.py   → campos nuevos FD + SW Sapien + control PAC
  - models/tms_waybill.py   → campos cfdi_* + métodos stamp/cancel/check
  - __manifest__.py         → agregar 'services' en la estructura

Reglas:
  - grep ANTES de agregar cualquier campo nuevo
  - Los métodos action_stamp/cancel/check llaman a PacManager
  - NO implementan HTTP directamente en tms_waybill.py
  - Agregar hook vacío en write() para tms.route.analytics (semilla V2.3)

AGENTE B — services/ (rama: feat/etapa-2.2-services)
Archivos a crear:
  - services/__init__.py
  - services/pac_manager.py
  - services/formas_digitales.py
  - services/sw_sapien.py
  - services/xml_builder.py
  - services/xml_signer.py

Reglas:
  - Todos los métodos con try/except y logging apropiado
  - Timeout de 30s en TODAS las llamadas HTTP
  - Token SW Sapien cacheado en ir.config_parameter
  - NUNCA incluir XML completo en mensajes de error
  - NUNCA hacer _logger.info() con credenciales
  - lxml, cryptography, requests ya disponibles en el venv

AGENTE C — views/ (rama: feat/etapa-2.2-views)
Archivos a modificar:
  - views/tms_waybill_views.xml         → botones + sección CFDI
  - views/res_config_settings_views.xml → sección dual PAC config

Reglas:
  - Botón "Timbrar": invisible="state != 'waybill' or cfdi_status == 'timbrado'"
  - Botón "Cancelar": invisible="cfdi_status != 'timbrado'"
  - Botón "Estatus SAT": invisible="cfdi_status == 'none'"
  - NUNCA usar attrs= (deprecated Odoo 19)
  - SIEMPRE usar invisible= directo

AGENTE D — Auditoría seguridad (sin rama, solo reporta)
Verificar:
  1. Credenciales fd_password y sw_password → usar password=True en vista
  2. tms_csd_password → ya existe, verificar que tenga password=True
  3. Token SW Sapien en ir.config_parameter (NO en res.company)
  4. Timeout en todas las llamadas HTTP (buscar 'requests.post' sin timeout)
  5. Try/except en todos los métodos de PAC (buscar métodos sin try/except)
  6. _logger nunca con XML completo ni credenciales
  7. cfdi_xml como Binary/attachment (NO como Text en BD)
```

---

## SEMILLA OBLIGATORIA (V2.3)
```python
# En tms.waybill — agregar en método write() o action que cierra el viaje
# El modelo tms.route.analytics ya existe desde V2.2 (modelo vacío)
# Agente A debe dejar el hook comentado listo para activar en V2.3:

def write(self, vals):
    res = super().write(vals)
    # SEMILLA V2.3: activar cuando se implemente tms.route.analytics
    # if vals.get('state') == 'closed':
    #     self.env['tms.route.analytics']._update_from_waybill(self)
    return res
```

---

## NOTAS IMPORTANTES

### Sobre el XML CFDI 4.0 + Carta Porte 3.1
- Version del CFDI: `4.0`
- Version del Complemento: `3.1`
- TipoDeComprobante: `T` (Traslado) para Carta Porte
- UsoCFDI del receptor: `CP01` (Adquisición de mercancias)
- Exportacion: `01` (No aplica)
- LugarExpedicion: CP de la empresa emisora

### Sobre el firmado del CSD
- El .key del SAT está en formato PKCS#8 encriptado con 3DES
- Usar: `cryptography.hazmat.primitives.serialization.load_der_private_key()`
- El .cer es DER — decodificar con `cryptography.x509.load_der_x509_certificate()`
- NoCertificado: 20 dígitos del serial number, sin guiones

### Sobre el failover
- Si PAC 1 lanza Exception → log warning → intenta PAC 2
- Si PAC 2 también falla → log error → UserError al usuario con ambos mensajes
- El chatter debe registrar: cuántos intentos, qué PAC funcionó

---

*SDD generado: 2026-03-15*
*Siguiente etapa: V2.3 — Facturación Real (account.move)*
