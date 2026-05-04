# REQUIREMENTS.md — V2.5.1 Tour Guide TMS

## Criterios de Aceptación

### AC-01 — Tooltips en el onboarding wizard
```gherkin
Dado que soy usuario nuevo y abro el wizard de onboarding
Cuando estoy en el Paso 1 (Empresa)
Entonces veo un banner azul informativo que explica:
  "Necesitas tu RFC, razón social y Código Postal fiscal.
   Estos datos van en todas tus facturas y Cartas Porte."
Y cada paso siguiente tiene su propio banner con contexto
```

| Paso | Mensaje del banner |
|------|-------------------|
| 1 - Empresa | RFC, razón social y CP fiscal. Van en todas las facturas. |
| 2 - CSD | Tus archivos .cer y .key del SAT. Sin ellos no puedes timbrar. |
| 3 - Vehículo | Placa, config SAT (ej. T3S2) y póliza de seguro obligatoria. |
| 4 - Chofer | RFC y número de licencia federal vigente. |
| 5 - Cliente | El RFC del cliente va en la factura. Puedes agregar más después. |
| 6 - Resumen | ¡Listo! Ahora te mostramos cómo crear tu primera Carta Porte. |

### AC-02 — Tour automático post-onboarding
```gherkin
Dado que acabo de completar el Paso 6 del onboarding
Cuando hago clic en "🚛 Crear mi primer viaje"
Entonces el popup se cierra
Y automáticamente inicia el tour tms_tour_carta_porte
Y el primer tooltip aparece sobre el botón "Nueva Cotización"
```

### AC-03 — Tour Carta Porte completo (9 pasos)
```gherkin
Dado que el tour tms_tour_carta_porte está corriendo
Entonces me guía por estos pasos en orden:
  1. Click "Nueva Cotización" en la lista de viajes
  2. Ingresar CP origen y destino
  3. Click "Calcular Ruta" → tooltip explica TollGuru
  4. Seleccionar propuesta de precio
  5. Agregar cliente y mercancía con Clave SAT
  6. Click "Crear Viaje" → waybill en estado cotizado
  7. Click "Aprobar Cotización" → estado aprobado
  8. Asignar vehículo y chofer en el formulario
  9. Click "Timbrar Carta Porte" → tooltip explica el UUID
```

### AC-04 — Botón flotante siempre visible
```gherkin
Dado que estoy en cualquier pantalla del TMS
Entonces veo un círculo azul con ❓ en esquina inferior derecha
Y está posicionado a bottom:24px, right:24px
Y no tapa el chatter ni otros botones de Odoo
Cuando hago clic
Entonces se abre el panel de ayuda
```

### AC-05 — Panel con 8 micro-tours
```gherkin
Dado que el panel de ayuda está abierto
Entonces veo el título "❓ ¿En qué necesitas ayuda?"
Y veo 8 filas, cada una con emoji + pregunta + botón "Ver cómo →"
Cuando hago clic en cualquier "Ver cómo →"
Entonces el panel se cierra
Y el micro-tour correspondiente inicia inmediatamente
```

### AC-06 — Micro-tours de 3-5 pasos cada uno
```gherkin
Dado que inicio el micro-tour "¿Dónde subo mis certificados CSD?"
Entonces el tour tiene exactamente estos pasos:
  1. Navega a Configuración (tooltip en el menú)
  2. Click en Ajustes (tooltip explicando la sección)
  3. Tooltip sobre los campos CSD con instrucciones claras
  4. Tooltip final: "Aquí subes tu .cer y .key del SAT"
Y el tour termina con un mensaje de confirmación
```

### AC-07 — Tours reiniciables sin error
```gherkin
Dado que ya completé el tour "¿Cómo creo una cotización?"
Cuando abro el panel ❓ y selecciono la misma pregunta
Entonces el tour inicia desde el paso 1 sin error
Y no hay estado acumulado del tour anterior
```

### AC-08 — Sin interferencia con uso normal
```gherkin
Dado que no he iniciado ningún tour
Cuando uso el TMS normalmente (crear viajes, timbrar, etc.)
Entonces el botón ❓ existe pero no interrumpe el flujo
Y no aparecen tooltips automáticos (excepto el primer post-onboarding)
```

## Casos límite

- Usuario cierra el tour a la mitad → puede reiniciarlo desde el panel ❓
- Usuario no completó el onboarding → tour Carta Porte disponible igualmente desde panel
- Panel abierto en pantalla pequeña → scroll vertical en el panel
- Tour iniciado desde menú que está oculto para group_tms_user → el tour debe saltar ese paso o usar ruta alternativa
- Trigger no encuentra elemento → tour falla con mensaje claro, no crash silencioso

## Escenarios de testing (mínimo 8)

1. `test_banners_onboarding` → cada paso del wizard muestra su banner informativo
2. `test_tour_post_onboarding` → action_create_first_trip lanza tour después de cerrar popup
3. `test_tour_carta_porte_9_pasos` → tour completo sin fallar en ningún trigger
4. `test_boton_flotante_visible` → componente OWL renderiza el botón ❓ en la UI
5. `test_panel_8_preguntas` → panel muestra exactamente 8 preguntas con botones
6. `test_micro_tour_csd` → micro-tour CSD navega a la sección correcta en Ajustes
7. `test_micro_tour_cotizacion` → micro-tour cotización abre el wizard correctamente
8. `test_tours_reiniciables` → iniciar el mismo tour dos veces no lanza error
