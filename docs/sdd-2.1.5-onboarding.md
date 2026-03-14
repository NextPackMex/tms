# SDD — Etapa 2.1.5: Onboarding Wizard 6 Pasos

| Campo | Valor |
|---|---|
| **Módulo** | TMS "Hombre Camión" (`tms/`) |
| **Fecha** | 2026-03-14 |
| **Prioridad** | Alta |
| **Branch GIT** | `feat/etapa-2.1.5-onboarding` |
| **Modo Antigravity** | `Planning + High` |

---

## GIT — Crear rama antes de tocar código

```bash
cd ~/odoo/proyectos/tms
git checkout main && git pull origin main
git checkout -b feat/etapa-2.1.5-onboarding
```

⚠️ **NO hacer push — Mois lo hace manualmente después de revisar.**

---

## PROBLEMA

Un usuario nuevo que instala el TMS no tiene guía de configuración inicial. Tiene que descubrir solo dónde crear su empresa, vehículos, seguros, chofer y primer cliente. Esto genera abandono y soporte innecesario.

**Objetivo:** usuario nuevo saca su primera Carta Porte en **< 14 minutos** siguiendo un wizard guiado de 6 pasos.

---

## SOLUCIÓN

Crear un **TransientModel** `tms.onboarding.wizard` con 6 pasos secuenciales que guían al usuario desde cero hasta tener todo configurado para crear su primer viaje. El wizard se lanza automáticamente la primera vez que el usuario entra al módulo TMS (si no hay waybills creados), o manualmente desde Configuración → Onboarding.

---

## ARCHIVOS A CREAR/MODIFICAR

| Archivo | Acción |
|---|---|
| `wizard/tms_onboarding_wizard.py` | **CREAR** — TransientModel con los 6 pasos |
| `wizard/tms_onboarding_wizard_views.xml` | **CREAR** — Vistas form del wizard |
| `wizard/__init__.py` | **MODIFICAR** — Agregar import del onboarding |
| `views/tms_menus.xml` | **MODIFICAR** — Agregar menuitem en Configuración |
| `security/ir.model.access.csv` | **MODIFICAR** — Permisos para el wizard |
| `__manifest__.py` | **MODIFICAR** — Agregar archivos nuevos al data list |

⚠️ **NO tocar:** `tms_waybill.py`, `tms_cotizacion_wizard.py`, `tms_waybill_views.xml`

---

## ANTES DE TOCAR CÓDIGO — Verificar con grep

```bash
# Verificar que NO existe un onboarding wizard previo
grep -rn "onboarding" wizard/ models/ views/
grep -rn "tms.onboarding" wizard/ models/

# Verificar modelos que vamos a usar (_inherit)
grep -rn "class.*ResCompany\|_inherit.*res.company" models/
grep -rn "class.*FleetVehicle\|_inherit.*fleet.vehicle" models/
grep -rn "class.*HrEmployee\|_inherit.*hr.employee" models/
grep -rn "class.*ResPartner\|_inherit.*res.partner" models/

# Verificar campos existentes en res.company
grep -rn "csd_cer\|csd_key\|csd_password\|fd_usuario" models/res_company.py

# Verificar wizard/__init__.py actual
cat wizard/__init__.py
```

---

## MODELO: tms.onboarding.wizard (TransientModel)

### Campos de control del wizard

```python
class TmsOnboardingWizard(models.TransientModel):
    """
    Wizard de onboarding para configuración inicial del TMS.
    Guía al usuario nuevo en 6 pasos hasta crear su primer viaje.
    """
    _name = 'tms.onboarding.wizard'
    _description = 'Onboarding TMS - Configuración Inicial'

    # --- Control del wizard ---
    step = fields.Integer(
        string='Paso actual',
        default=1,
        help='Controla en qué paso del onboarding está el usuario'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        required=True,
    )
```

### PASO 1 — Empresa + CSD + Logo

```python
    # --- Paso 1: Empresa ---
    company_name = fields.Char(
        string='Nombre de la empresa',
        help='Razón social como aparece en el SAT'
    )
    company_rfc = fields.Char(
        string='RFC',
        size=13,
        help='RFC del emisor (12 o 13 caracteres)'
    )
    company_logo = fields.Binary(
        string='Logo de la empresa',
        help='Logo que aparecerá en documentos y Carta Porte'
    )
    # CSD para timbrado — se guardan en res.company
    csd_cer_file = fields.Binary(
        string='Archivo CSD (.cer)',
        help='Certificado de Sello Digital del SAT'
    )
    csd_cer_filename = fields.Char(string='Nombre archivo .cer')
    csd_key_file = fields.Binary(
        string='Archivo CSD (.key)',
        help='Llave privada del Certificado de Sello Digital'
    )
    csd_key_filename = fields.Char(string='Nombre archivo .key')
    csd_password = fields.Char(
        string='Contraseña CSD',
        help='Contraseña de la llave privada del CSD'
    )
    regimen_fiscal = fields.Selection(
        selection=[
            ('601', '601 - General de Ley Personas Morales'),
            ('603', '603 - Personas Morales con Fines no Lucrativos'),
            ('605', '605 - Sueldos y Salarios'),
            ('606', '606 - Arrendamiento'),
            ('612', '612 - Personas Físicas con Actividades Empresariales y Profesionales'),
            ('616', '616 - Sin obligaciones fiscales'),
            ('620', '620 - Sociedades Cooperativas de Producción'),
            ('621', '621 - Incorporación Fiscal'),
            ('622', '622 - Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
            ('623', '623 - Opcional para Grupos de Sociedades'),
            ('624', '624 - Coordinados'),
            ('625', '625 - Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas'),
            ('626', '626 - Régimen Simplificado de Confianza'),
        ],
        string='Régimen Fiscal',
        help='Régimen fiscal del emisor según el SAT'
    )
```

### PASO 2 — Vehículo principal + remolque + config SCT

```python
    # --- Paso 2: Vehículo ---
    vehicle_name = fields.Char(
        string='Nombre del vehículo',
        help='Ej: Kenworth T680 2022, Freightliner Cascadia'
    )
    vehicle_plate = fields.Char(
        string='Placas',
        help='Placas del tracto/camión'
    )
    vehicle_year = fields.Char(
        string='Año/Modelo',
        size=4,
        help='Año del modelo del vehículo'
    )
    vehicle_config_id = fields.Many2one(
        'tms.sat.config.autotransporte',
        string='Configuración vehicular SCT',
        help='Tipo de configuración según catálogo SAT (ej: C2, C3, T3S2)'
    )
    vehicle_permit_type_id = fields.Many2one(
        'tms.sat.tipo.permiso',
        string='Tipo de permiso SCT',
        help='Tipo de permiso SCT del vehículo'
    )
    vehicle_permit_number = fields.Char(
        string='Número de permiso SCT',
        help='Número del permiso SCT vigente'
    )
    # Remolque opcional
    has_trailer = fields.Boolean(
        string='¿Tiene remolque?',
        default=False,
    )
    trailer_name = fields.Char(string='Nombre del remolque')
    trailer_plate = fields.Char(string='Placas del remolque')
    trailer_sub_type = fields.Many2one(
        'tms.sat.config.autotransporte',
        string='Subtipo remolque SCT',
        help='Configuración del remolque según catálogo SAT'
    )
    # Dolly opcional
    has_dolly = fields.Boolean(
        string='¿Tiene dolly?',
        default=False,
    )
    dolly_name = fields.Char(string='Nombre del dolly')
    dolly_plate = fields.Char(string='Placas del dolly')
```

### PASO 3 — Seguros (RC + Carga + Ambiental)

```python
    # --- Paso 3: Seguros ---
    # Seguro de Responsabilidad Civil
    insurance_rc_company = fields.Char(
        string='Aseguradora RC',
        help='Nombre de la aseguradora de Responsabilidad Civil'
    )
    insurance_rc_policy = fields.Char(
        string='Póliza RC',
        help='Número de póliza de Responsabilidad Civil'
    )
    insurance_rc_expiry = fields.Date(
        string='Vigencia RC',
        help='Fecha de vencimiento de la póliza RC'
    )
    # Seguro de Carga
    insurance_cargo_company = fields.Char(
        string='Aseguradora Carga',
        help='Nombre de la aseguradora de la carga'
    )
    insurance_cargo_policy = fields.Char(
        string='Póliza Carga',
        help='Número de póliza de seguro de carga'
    )
    insurance_cargo_expiry = fields.Date(
        string='Vigencia Carga',
        help='Fecha de vencimiento del seguro de carga'
    )
    # Seguro Ambiental (solo para materiales peligrosos, opcional)
    insurance_env_company = fields.Char(
        string='Aseguradora Ambiental',
        help='Solo requerido si transportas materiales peligrosos'
    )
    insurance_env_policy = fields.Char(string='Póliza Ambiental')
    insurance_env_expiry = fields.Date(string='Vigencia Ambiental')
```

### PASO 4 — Chofer + licencia federal

```python
    # --- Paso 4: Chofer ---
    driver_name = fields.Char(
        string='Nombre del chofer',
        help='Nombre completo del operador'
    )
    driver_rfc = fields.Char(
        string='RFC del chofer',
        size=13,
    )
    driver_curp = fields.Char(
        string='CURP del chofer',
        size=18,
    )
    driver_license_number = fields.Char(
        string='Número de licencia federal',
        help='Número de la licencia federal de conducir'
    )
    driver_license_type = fields.Selection(
        selection=[
            ('A', 'Tipo A - Vehículos ligeros'),
            ('B', 'Tipo B - Vehículos pesados'),
            ('C', 'Tipo C - Doble articulado'),
            ('D', 'Tipo D - Materiales peligrosos'),
            ('E', 'Tipo E - Doble articulado + peligrosos'),
        ],
        string='Tipo de licencia',
        help='Tipo de licencia federal de conducir SCT'
    )
    driver_license_expiry = fields.Date(
        string='Vigencia licencia',
        help='Fecha de vencimiento de la licencia federal'
    )
```

### PASO 5 — Primer cliente

```python
    # --- Paso 5: Primer cliente ---
    client_name = fields.Char(
        string='Nombre o razón social del cliente',
        help='Nombre del primer cliente al que le vas a facturar'
    )
    client_rfc = fields.Char(
        string='RFC del cliente',
        size=13,
        help='RFC para facturación'
    )
    client_email = fields.Char(
        string='Email del cliente',
        help='Email para envío de facturas y Carta Porte'
    )
    client_phone = fields.Char(
        string='Teléfono del cliente',
    )
    client_street = fields.Char(string='Calle y número')
    client_city = fields.Char(string='Ciudad')
    client_state_id = fields.Many2one(
        'res.country.state',
        string='Estado',
        domain="[('country_id.code', '=', 'MX')]",
    )
    client_zip = fields.Char(string='Código Postal', size=5)
    client_is_company = fields.Boolean(
        string='¿Es persona moral?',
        default=True,
        help='Marca si el cliente es empresa (persona moral). Afecta la retención de IVA 4%.'
    )
```

### PASO 6 — Resumen + crear primer viaje

```python
    # --- Paso 6: Resumen (solo lectura, campos computed) ---
    summary_company = fields.Char(
        string='Empresa configurada',
        compute='_compute_summary',
    )
    summary_vehicle = fields.Char(
        string='Vehículo configurado',
        compute='_compute_summary',
    )
    summary_driver = fields.Char(
        string='Chofer configurado',
        compute='_compute_summary',
    )
    summary_client = fields.Char(
        string='Cliente configurado',
        compute='_compute_summary',
    )
    summary_insurance = fields.Char(
        string='Seguros configurados',
        compute='_compute_summary',
    )

    @api.depends('company_name', 'vehicle_name', 'driver_name',
                 'client_name', 'insurance_rc_policy')
    def _compute_summary(self):
        """Calcula el texto de resumen para el paso 6."""
        for rec in self:
            rec.summary_company = rec.company_name or 'Sin configurar'
            rec.summary_vehicle = rec.vehicle_name or 'Sin configurar'
            rec.summary_driver = rec.driver_name or 'Sin configurar'
            rec.summary_client = rec.client_name or 'Sin configurar'
            # Conteo de seguros configurados
            count = 0
            if rec.insurance_rc_policy:
                count += 1
            if rec.insurance_cargo_policy:
                count += 1
            if rec.insurance_env_policy:
                count += 1
            rec.summary_insurance = f'{count}/3 seguros configurados'
```

### MÉTODOS DE NAVEGACIÓN

```python
    def action_next_step(self):
        """Avanza al siguiente paso del wizard."""
        self.ensure_one()
        if self.step < 6:
            self.step += 1
        return self._reopen_wizard()

    def action_prev_step(self):
        """Regresa al paso anterior del wizard."""
        self.ensure_one()
        if self.step > 1:
            self.step -= 1
        return self._reopen_wizard()

    def _reopen_wizard(self):
        """Reabre el wizard en el paso actual."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.onboarding.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
```

### MÉTODOS DE GUARDADO POR PASO

```python
    def action_save_step_1(self):
        """
        Guarda datos de empresa en res.company.
        Escribe RFC, logo, régimen fiscal y archivos CSD.
        """
        self.ensure_one()
        company = self.company_id
        vals = {}
        if self.company_name:
            vals['name'] = self.company_name
        if self.company_rfc:
            vals['vat'] = self.company_rfc
        if self.company_logo:
            vals['logo'] = self.company_logo
        if self.regimen_fiscal:
            vals['tms_regimen_fiscal'] = self.regimen_fiscal
        if self.csd_cer_file:
            vals['tms_csd_cer'] = self.csd_cer_file
        if self.csd_key_file:
            vals['tms_csd_key'] = self.csd_key_file
        if self.csd_password:
            vals['tms_csd_password'] = self.csd_password
        if vals:
            company.write(vals)
        return self.action_next_step()

    def action_save_step_2(self):
        """
        Crea el vehículo principal (tracto) y opcionalmente remolque y dolly.
        Usa fleet.vehicle con extensiones TMS.
        """
        self.ensure_one()
        Vehicle = self.env['fleet.vehicle']

        # Crear tracto principal
        if self.vehicle_name:
            tracto_vals = {
                'name': self.vehicle_name,
                'license_plate': self.vehicle_plate or '',
                'model_year': self.vehicle_year or '',
                'tms_is_trailer': False,
                'company_id': self.company_id.id,
            }
            if self.vehicle_config_id:
                tracto_vals['tms_vehicle_config_id'] = self.vehicle_config_id.id
            if self.vehicle_permit_type_id:
                tracto_vals['tms_permit_type_id'] = self.vehicle_permit_type_id.id
            if self.vehicle_permit_number:
                tracto_vals['tms_permit_number'] = self.vehicle_permit_number
            Vehicle.create(tracto_vals)

        # Crear remolque si aplica
        if self.has_trailer and self.trailer_name:
            trailer_vals = {
                'name': self.trailer_name,
                'license_plate': self.trailer_plate or '',
                'tms_is_trailer': True,
                'company_id': self.company_id.id,
            }
            if self.trailer_sub_type:
                trailer_vals['tms_vehicle_config_id'] = self.trailer_sub_type.id
            Vehicle.create(trailer_vals)

        # Crear dolly si aplica
        if self.has_dolly and self.dolly_name:
            dolly_vals = {
                'name': self.dolly_name,
                'license_plate': self.dolly_plate or '',
                'tms_is_trailer': True,
                'company_id': self.company_id.id,
            }
            Vehicle.create(dolly_vals)

        return self.action_next_step()

    def action_save_step_3(self):
        """
        Guarda datos de seguros en res.company.
        Los seguros de Carta Porte van a nivel empresa.
        """
        self.ensure_one()
        company = self.company_id
        vals = {}
        # RC
        if self.insurance_rc_company:
            vals['tms_insurance_rc_company'] = self.insurance_rc_company
        if self.insurance_rc_policy:
            vals['tms_insurance_rc_policy'] = self.insurance_rc_policy
        if self.insurance_rc_expiry:
            vals['tms_insurance_rc_expiry'] = self.insurance_rc_expiry
        # Carga
        if self.insurance_cargo_company:
            vals['tms_insurance_cargo_company'] = self.insurance_cargo_company
        if self.insurance_cargo_policy:
            vals['tms_insurance_cargo_policy'] = self.insurance_cargo_policy
        if self.insurance_cargo_expiry:
            vals['tms_insurance_cargo_expiry'] = self.insurance_cargo_expiry
        # Ambiental
        if self.insurance_env_company:
            vals['tms_insurance_env_company'] = self.insurance_env_company
        if self.insurance_env_policy:
            vals['tms_insurance_env_policy'] = self.insurance_env_policy
        if self.insurance_env_expiry:
            vals['tms_insurance_env_expiry'] = self.insurance_env_expiry
        if vals:
            company.write(vals)
        return self.action_next_step()

    def action_save_step_4(self):
        """
        Crea el chofer como hr.employee con datos de licencia federal.
        """
        self.ensure_one()
        if self.driver_name:
            Employee = self.env['hr.employee']
            emp_vals = {
                'name': self.driver_name,
                'company_id': self.company_id.id,
            }
            if self.driver_rfc:
                emp_vals['tms_rfc'] = self.driver_rfc
            if self.driver_curp:
                emp_vals['tms_curp'] = self.driver_curp
            if self.driver_license_number:
                emp_vals['tms_license_number'] = self.driver_license_number
            if self.driver_license_type:
                emp_vals['tms_license_type'] = self.driver_license_type
            if self.driver_license_expiry:
                emp_vals['tms_license_expiry'] = self.driver_license_expiry
            Employee.create(emp_vals)
        return self.action_next_step()

    def action_save_step_5(self):
        """
        Crea el primer cliente como res.partner.
        Respeta la regla: NO required=True en campos heredados.
        """
        self.ensure_one()
        if self.client_name:
            Partner = self.env['res.partner']
            partner_vals = {
                'name': self.client_name,
                'is_company': self.client_is_company,
                'company_type': 'company' if self.client_is_company else 'person',
            }
            if self.client_rfc:
                partner_vals['vat'] = self.client_rfc
            if self.client_email:
                partner_vals['email'] = self.client_email
            if self.client_phone:
                partner_vals['phone'] = self.client_phone
            if self.client_street:
                partner_vals['street'] = self.client_street
            if self.client_city:
                partner_vals['city'] = self.client_city
            if self.client_state_id:
                partner_vals['state_id'] = self.client_state_id.id
            if self.client_zip:
                partner_vals['zip'] = self.client_zip
            # País siempre México
            mx = self.env.ref('base.mx', raise_if_not_found=False)
            if mx:
                partner_vals['country_id'] = mx.id
            Partner.create(partner_vals)
        return self.action_next_step()

    def action_create_first_trip(self):
        """
        Cierra el onboarding y abre el wizard de cotización
        para que el usuario cree su primer viaje.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.cotizacion.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': '¡Crea tu primer viaje!',
        }
```

---

## CAMPOS NUEVOS EN res.company (models/res_company.py)

⚠️ **ANTES de agregar, verificar que no existan ya:**
```bash
grep -rn "tms_regimen_fiscal\|tms_csd_cer\|tms_csd_key\|tms_csd_password" models/res_company.py
grep -rn "tms_insurance_rc\|tms_insurance_cargo\|tms_insurance_env" models/res_company.py
```

Solo agregar los campos que **NO existan**:

```python
# --- CSD para timbrado ---
tms_regimen_fiscal = fields.Selection(
    selection=[
        ('601', '601 - General de Ley Personas Morales'),
        ('612', '612 - Actividades Empresariales y Profesionales'),
        ('621', '621 - Incorporación Fiscal'),
        ('626', '626 - RESICO'),
    ],
    string='Régimen Fiscal SAT',
)
tms_csd_cer = fields.Binary(string='CSD Certificado (.cer)')
tms_csd_key = fields.Binary(string='CSD Llave Privada (.key)')
tms_csd_password = fields.Char(string='Contraseña CSD')

# --- Seguros Carta Porte ---
tms_insurance_rc_company = fields.Char(string='Aseguradora RC')
tms_insurance_rc_policy = fields.Char(string='Póliza RC')
tms_insurance_rc_expiry = fields.Date(string='Vigencia RC')

tms_insurance_cargo_company = fields.Char(string='Aseguradora Carga')
tms_insurance_cargo_policy = fields.Char(string='Póliza Carga')
tms_insurance_cargo_expiry = fields.Date(string='Vigencia Carga')

tms_insurance_env_company = fields.Char(string='Aseguradora Ambiental')
tms_insurance_env_policy = fields.Char(string='Póliza Ambiental')
tms_insurance_env_expiry = fields.Date(string='Vigencia Ambiental')
```

---

## CAMPOS NECESARIOS EN hr.employee (models/hr_employee.py)

⚠️ **Verificar antes:**
```bash
grep -rn "tms_rfc\|tms_curp\|tms_license_number\|tms_license_type\|tms_license_expiry" models/hr_employee.py
```

Solo agregar los que **NO existan**:

```python
tms_rfc = fields.Char(string='RFC del chofer', size=13)
tms_curp = fields.Char(string='CURP del chofer', size=18)
tms_license_number = fields.Char(string='Número licencia federal')
tms_license_type = fields.Selection(
    selection=[
        ('A', 'Tipo A'), ('B', 'Tipo B'), ('C', 'Tipo C'),
        ('D', 'Tipo D'), ('E', 'Tipo E'),
    ],
    string='Tipo licencia federal',
)
tms_license_expiry = fields.Date(string='Vigencia licencia')
```

---

## VISTA XML — wizard/tms_onboarding_wizard_views.xml

La vista debe:
1. Mostrar un **stepper visual** arriba con los 6 pasos (indicador de progreso)
2. Usar `invisible="step != X"` para mostrar solo los campos del paso actual
3. Botones "Anterior" / "Siguiente" en el footer
4. Paso 6 muestra resumen + botón "🚛 Crear mi primer viaje"

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>

    <!-- Vista form del onboarding wizard -->
    <record id="view_tms_onboarding_wizard_form" model="ir.ui.view">
        <field name="name">tms.onboarding.wizard.form</field>
        <field name="model">tms.onboarding.wizard</field>
        <field name="arch" type="xml">
            <form string="Configuración Inicial TMS">

                <!-- Stepper visual — indicador de progreso -->
                <div class="alert alert-info text-center" style="font-size: 16px;">
                    <span invisible="step != 1"><strong>Paso 1 de 6</strong> — 🏢 Tu Empresa</span>
                    <span invisible="step != 2"><strong>Paso 2 de 6</strong> — 🚛 Tu Vehículo</span>
                    <span invisible="step != 3"><strong>Paso 3 de 6</strong> — 🛡️ Tus Seguros</span>
                    <span invisible="step != 4"><strong>Paso 4 de 6</strong> — 👷 Tu Chofer</span>
                    <span invisible="step != 5"><strong>Paso 5 de 6</strong> — 🤝 Tu Primer Cliente</span>
                    <span invisible="step != 6"><strong>Paso 6 de 6</strong> — ✅ ¡Todo Listo!</span>
                </div>

                <!-- Barra de progreso visual -->
                <div class="o_horizontal_separator" style="margin-bottom: 16px;">
                    <div class="progress" style="height: 8px;">
                        <!-- Nota: Antigravity puede implementar esto con CSS dinámico o con
                             un widget simple. Alternativa: usar un campo computed HTML. -->
                    </div>
                </div>

                <field name="step" invisible="1"/>
                <field name="company_id" invisible="1"/>

                <!-- ===== PASO 1 — EMPRESA ===== -->
                <group invisible="step != 1" string="Datos de tu Empresa">
                    <group>
                        <field name="company_name" placeholder="Ej: Transportes García SA de CV"/>
                        <field name="company_rfc" placeholder="Ej: TGA200101ABC"/>
                        <field name="regimen_fiscal"/>
                    </group>
                    <group>
                        <field name="company_logo" widget="image" class="oe_avatar"/>
                    </group>
                    <separator string="Certificado de Sello Digital (CSD)"/>
                    <div class="alert alert-warning">
                        <strong>💡 Tip:</strong> El CSD lo descargas del portal del SAT.
                        Lo necesitas para timbrar tus Cartas Porte. Si no lo tienes aún,
                        puedes saltarte este paso y agregarlo después en Configuración.
                    </div>
                    <group>
                        <field name="csd_cer_file" filename="csd_cer_filename"/>
                        <field name="csd_cer_filename" invisible="1"/>
                        <field name="csd_key_file" filename="csd_key_filename"/>
                        <field name="csd_key_filename" invisible="1"/>
                        <field name="csd_password" password="True"/>
                    </group>
                </group>

                <!-- ===== PASO 2 — VEHÍCULO ===== -->
                <group invisible="step != 2" string="Tu Vehículo Principal">
                    <group>
                        <field name="vehicle_name" placeholder="Ej: Kenworth T680 2022"/>
                        <field name="vehicle_plate" placeholder="Ej: ABC-123-A"/>
                        <field name="vehicle_year" placeholder="Ej: 2022"/>
                    </group>
                    <group>
                        <field name="vehicle_config_id"/>
                        <field name="vehicle_permit_type_id"/>
                        <field name="vehicle_permit_number" placeholder="Ej: PERM-12345"/>
                    </group>
                    <separator string="Remolque"/>
                    <group>
                        <field name="has_trailer"/>
                    </group>
                    <group invisible="not has_trailer">
                        <field name="trailer_name" placeholder="Ej: Remolque Utility 53ft"/>
                        <field name="trailer_plate"/>
                        <field name="trailer_sub_type"/>
                    </group>
                    <separator string="Dolly (doble articulado)" invisible="not has_trailer"/>
                    <group invisible="not has_trailer">
                        <field name="has_dolly"/>
                    </group>
                    <group invisible="not has_dolly">
                        <field name="dolly_name"/>
                        <field name="dolly_plate"/>
                    </group>
                </group>

                <!-- ===== PASO 3 — SEGUROS ===== -->
                <group invisible="step != 3" string="Seguros de tu Operación">
                    <div class="alert alert-info" colspan="2">
                        <strong>📋 Nota:</strong> La Carta Porte 3.1 requiere mínimo el seguro de
                        Responsabilidad Civil. El seguro de Carga es recomendado y el Ambiental
                        solo aplica si transportas materiales peligrosos.
                    </div>
                    <separator string="Seguro de Responsabilidad Civil (obligatorio)"/>
                    <group>
                        <field name="insurance_rc_company" placeholder="Ej: Qualitas, HDI, GNP"/>
                        <field name="insurance_rc_policy" placeholder="Ej: POL-2024-12345"/>
                        <field name="insurance_rc_expiry"/>
                    </group>
                    <separator string="Seguro de Carga (recomendado)"/>
                    <group>
                        <field name="insurance_cargo_company"/>
                        <field name="insurance_cargo_policy"/>
                        <field name="insurance_cargo_expiry"/>
                    </group>
                    <separator string="Seguro Ambiental (solo materiales peligrosos)"/>
                    <group>
                        <field name="insurance_env_company"/>
                        <field name="insurance_env_policy"/>
                        <field name="insurance_env_expiry"/>
                    </group>
                </group>

                <!-- ===== PASO 4 — CHOFER ===== -->
                <group invisible="step != 4" string="Datos de tu Chofer">
                    <group>
                        <field name="driver_name" placeholder="Ej: Juan Pérez López"/>
                        <field name="driver_rfc" placeholder="Ej: PELJ850101ABC"/>
                        <field name="driver_curp" placeholder="Ej: PELJ850101HJCRZN09"/>
                    </group>
                    <group>
                        <field name="driver_license_number" placeholder="Ej: LIC-FED-12345"/>
                        <field name="driver_license_type"/>
                        <field name="driver_license_expiry"/>
                    </group>
                </group>

                <!-- ===== PASO 5 — PRIMER CLIENTE ===== -->
                <group invisible="step != 5" string="Tu Primer Cliente">
                    <group>
                        <field name="client_name" placeholder="Ej: Industrias ABC SA de CV"/>
                        <field name="client_rfc" placeholder="Ej: IAB200101XYZ"/>
                        <field name="client_is_company"/>
                        <field name="client_email" placeholder="facturacion@cliente.com"/>
                        <field name="client_phone" placeholder="33 1234 5678"/>
                    </group>
                    <group>
                        <field name="client_street" placeholder="Av. Vallarta 1234"/>
                        <field name="client_city" placeholder="Guadalajara"/>
                        <field name="client_state_id"/>
                        <field name="client_zip" placeholder="44100"/>
                    </group>
                </group>

                <!-- ===== PASO 6 — RESUMEN ===== -->
                <group invisible="step != 6" string="¡Todo Listo!">
                    <div class="alert alert-success text-center" colspan="2">
                        <h3>🎉 ¡Felicidades! Tu TMS está configurado</h3>
                        <p>Aquí el resumen de lo que configuraste:</p>
                    </div>
                    <group>
                        <field name="summary_company" readonly="1"/>
                        <field name="summary_vehicle" readonly="1"/>
                        <field name="summary_insurance" readonly="1"/>
                        <field name="summary_driver" readonly="1"/>
                        <field name="summary_client" readonly="1"/>
                    </group>
                    <div class="alert alert-info text-center" colspan="2">
                        <p>Puedes modificar cualquier dato después en <strong>Configuración</strong>.</p>
                        <p>¡Ahora crea tu primer viaje!</p>
                    </div>
                </group>

                <!-- FOOTER — botones de navegación -->
                <footer>
                    <!-- Botón Anterior (no aparece en paso 1) -->
                    <button string="← Anterior"
                            type="object"
                            name="action_prev_step"
                            class="btn-secondary"
                            invisible="step == 1"/>

                    <!-- Botón Guardar y Siguiente (pasos 1-5) -->
                    <button string="Guardar y Siguiente →"
                            type="object"
                            name="action_save_step_1"
                            class="btn-primary"
                            invisible="step != 1"/>
                    <button string="Guardar y Siguiente →"
                            type="object"
                            name="action_save_step_2"
                            class="btn-primary"
                            invisible="step != 2"/>
                    <button string="Guardar y Siguiente →"
                            type="object"
                            name="action_save_step_3"
                            class="btn-primary"
                            invisible="step != 3"/>
                    <button string="Guardar y Siguiente →"
                            type="object"
                            name="action_save_step_4"
                            class="btn-primary"
                            invisible="step != 4"/>
                    <button string="Guardar y Siguiente →"
                            type="object"
                            name="action_save_step_5"
                            class="btn-primary"
                            invisible="step != 5"/>

                    <!-- Botón final — Crear primer viaje (solo paso 6) -->
                    <button string="🚛 Crear mi primer viaje"
                            type="object"
                            name="action_create_first_trip"
                            class="btn-primary btn-lg"
                            invisible="step != 6"/>

                    <button string="Cerrar" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <!-- Acción para abrir el onboarding -->
    <record id="action_tms_onboarding_wizard" model="ir.actions.act_window">
        <field name="name">Configuración Inicial TMS</field>
        <field name="res_model">tms.onboarding.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>

</odoo>
```

---

## SEGURIDAD — ir.model.access.csv

Agregar estas líneas al archivo existente:

```csv
access_tms_onboarding_wizard_user,tms.onboarding.wizard.user,model_tms_onboarding_wizard,tms.group_tms_user,1,1,1,0
access_tms_onboarding_wizard_manager,tms.onboarding.wizard.manager,model_tms_onboarding_wizard,tms.group_tms_manager,1,1,1,1
```

---

## MENUITEM — Agregar en tms_menus.xml o wizard views

```xml
<menuitem
    id="menu_tms_onboarding"
    name="Configuración Inicial"
    parent="menu_tms_config"
    action="action_tms_onboarding_wizard"
    sequence="1"
    groups="tms.group_tms_manager"/>
```

⚠️ Verificar primero que existe `menu_tms_config`:
```bash
grep -rn "menu_tms_config" views/ wizard/
```

Si no existe, crear el menú bajo el menú raíz de TMS.

---

## __manifest__.py — Agregar archivos

En la lista `data`, agregar (respetando el orden — wizard views después de menus):

```python
'wizard/tms_onboarding_wizard_views.xml',
```

---

## ACCEPTANCE CRITERIA

| ID | Criterio | Verificación |
|---|---|---|
| AC-01 | Wizard abre desde Configuración → Configuración Inicial | Click en menú → se abre el wizard en paso 1 |
| AC-02 | Los 6 pasos navegan correctamente con Anterior/Siguiente | Click siguiente 5 veces → llega a paso 6. Click anterior → regresa |
| AC-03 | Paso 1 guarda datos en res.company | Llenar paso 1 → siguiente → verificar en Ajustes → Empresas |
| AC-04 | Paso 2 crea vehículo en fleet.vehicle | Llenar paso 2 → siguiente → verificar en Flota → Vehículos |
| AC-05 | Paso 3 guarda seguros en res.company | Llenar paso 3 → siguiente → verificar en config empresa |
| AC-06 | Paso 4 crea chofer en hr.employee | Llenar paso 4 → siguiente → verificar en Empleados |
| AC-07 | Paso 5 crea cliente en res.partner | Llenar paso 5 → siguiente → verificar en Contactos |
| AC-08 | Paso 6 muestra resumen y botón crear viaje | Llegar a paso 6 → ver resumen → click "Crear mi primer viaje" → abre wizard cotización |
| AC-09 | No hay errores en log al actualizar módulo | `grep -n "WARNING\|ERROR" odoo.log \| tail -20` |

---

## QA — Validación

```bash
# Compilar Python
python3 -m py_compile wizard/tms_onboarding_wizard.py

# Verificar que no hay campos duplicados
grep -rn "tms_regimen_fiscal\|tms_csd_cer\|tms_insurance_rc" models/res_company.py | sort

# Update módulo
python3 odoo-bin -c odoo.conf -u tms -d tms_dev --stop-after-init

# Verificar logs
grep -n "WARNING\|ERROR" odoo.log | tail -20
```

---

## COMMIT — Solo commit, NO push

```bash
git add -A
git commit -m "feat(2.1.5): onboarding wizard 6 pasos — empresa, vehículo, seguros, chofer, cliente, resumen"
```

⚠️ **NO ejecutar git push — Mois lo hace manualmente.**

## Actualizar CLAUDE.md

Marcar etapa 2.1.5 como ✅ en la sección de roadmap.

---

*FIN DEL SDD — Etapa 2.1.5*
