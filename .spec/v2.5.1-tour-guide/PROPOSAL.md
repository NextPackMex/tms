# PROPOSAL.md — V2.5.1 Tour Guide TMS

Fecha: 2026-05-04
Proyecto: TMS Hombre Camión
Estimación: L
Branch: feat/v2.5.1-tour-guide

## Problema que resuelve

Un usuario nuevo no sabe qué hacer al abrir el sistema por primera vez.
El onboarding wizard existe pero no explica el propósito de cada campo.
Después del onboarding, el usuario queda solo sin saber cómo crear su
primera Carta Porte. No hay ayuda contextual disponible en ningún momento.

Objetivo: usuario nuevo completa su primera Carta Porte en < 14 minutos
sin capacitación externa.

## Solución — 3 componentes independientes

### Componente 1: Tour dentro del Onboarding
Tooltips explicativos en cada paso del wizard de 6 pasos.
NO usa el sistema web_tour (no funciona en modals).
Usa tooltips HTML nativos o un banner informativo en cada paso.
Explica qué datos necesita el usuario y por qué.

### Componente 2: Tour automático post-onboarding
Al terminar el Paso 6 y hacer clic en "Crear mi primer viaje",
el popup se cierra Y se lanza automáticamente el tour
"¿Cómo timbro mi primera Carta Porte?" usando odoo.startTour().
Este tour guía al usuario desde el tablero hasta el timbrado.

### Componente 3: Panel flotante de ayuda
Botón ❓ siempre visible en esquina inferior derecha.
Al hacer clic, abre un panel con 8 preguntas frecuentes.
Cada pregunta lanza un micro-tour de 3-5 pasos al tema específico.

## Las 8 preguntas del panel

| # | Pregunta | Destino del micro-tour |
|---|----------|------------------------|
| 1 | 🏢 ¿Dónde configuro mi empresa y RFC? | Configuración → Mi Empresa |
| 2 | 📜 ¿Dónde subo mis certificados CSD? | Configuración → Ajustes → CSD |
| 3 | 🚛 ¿Dónde registro mis tractores? | Operaciones → Vehículos |
| 4 | 👤 ¿Dónde agrego mis choferes? | Operaciones → Operadores |
| 5 | 📦 ¿Cómo creo una cotización? | Nueva Cotización → wizard |
| 6 | 📄 ¿Cómo timbro mi Carta Porte? | Waybill aprobado → timbrar |
| 7 | 💰 ¿Cómo genero la factura? | Waybill → Facturar |
| 8 | 📊 ¿Qué me dice el dashboard? | Dashboard → KPIs |

## Alcance IN scope

- Tooltips/banners informativos en cada paso del onboarding wizard
- Tour automático al terminar el onboarding (post-popup)
- Botón flotante ❓ permanente en la UI
- Panel con 8 micro-tours lanzables
- Todos los textos en español
- Tours reiniciables

## Alcance OUT scope

- Tours en inglés
- Tours para el portal de clientes
- Tours con video o animaciones
- Modificar la lógica de negocio del onboarding
- Tours para funciones de V2.6+ (portal, firma digital, etc.)

## Impacto técnico

- `tms_onboarding_wizard.py` — modificar action_create_first_trip()
- `tms_onboarding_wizard_views.xml` — agregar banners por paso
- `tms_tour.js` — reescribir: 8 micro-tours + 1 tour post-onboarding
- `tms_help_panel.js` — componente OWL nuevo (botón + panel)
- `tms_help_panel.xml` — template QWeb del panel
- `tms_help_panel.css` — estilos flotante
- `__manifest__.py` — registrar nuevos assets

## Criterio de éxito

Usuario nuevo: onboarding → primer viaje → Carta Porte timbrada
en ≤ 14 minutos sin ayuda externa.
Panel ❓ disponible en todo momento para usuarios existentes.
