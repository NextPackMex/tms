# 🚚 Guía Maestra de Pruebas - TMS (QA Server)

Bienvido al ambiente de pruebas del TMS. Esta guía está diseñada para que cualquier persona, incluso sin conocimientos previos de logística, pueda validar las funcionalidades críticas del sistema.

---

## 🏁 Antes de Empezar: Preparación de la Instancia

Para que los datos de prueba funcionen, asegúrate de haber actualizado el módulo con los demos:
`python3 odoo-bin -u tms -d BASE_QA --demo`

---

## 🎬 1. El Tour Interactivo (Auto-entrenamiento)

Al entrar al módulo **TMS**, busca un globo de ayuda o ve al menú de Odoo (ícono de interrogación) y activa el tour: **"Configuración Integral de Viaje"**. El sistema te llevará de la mano por cada botón.

---

## 📋 2. Catálogos Base (Datos Dummy)

Hemos precargado elementos listos para "conectar y usar":

| Elemento     | Identificador        | Dato Clave                                       |
| :----------- | :------------------- | :----------------------------------------------- |
| **Tractor**  | `T-001`              | Tiene póliza `POL-12345` y Configuración `T3S2`. |
| **Remolque** | `R-501`              | Placas `RE-99-88`.                               |
| **Chofer**   | `Juan Chofer`        | RFC `PERJ800101XYZ` (Válido para Carta Porte).   |
| **Cliente**  | `LOGISTICA INTEGRAL` | RFC `LIA121212ABC`.                              |
| **Rutas**    | `Mty -> CDMX`        | Distancia: 920km, Casetas: $4,500.               |

---

## 🚀 3. Escenarios de Prueba (Test Cases)

### Escenario A: El "Happy Path" (Crear un viaje perfecto)

1.  **Nuevo Viaje**: Ve a **Viajes / Tablero** y haz clic en **Nuevo**.
2.  **Actores**: Selecciona a `LOGISTICA INTEGRAL` en los 3 campos (Facturación, Origen, Destino).
3.  **Llenado Rápido**: En la pestaña **Información de Ruta**, selecciona el vehículo `T-001`.
    - _Tip_: Activa el switch "Lleva Caja" y selecciona el remolque `R-501`.
4.  **Carga**: En la pestaña **Mercancías**, agrega: "Clave SAT: 50131702", "Descripción: Leche", "Peso: 25000 kg".
5.  **Confirmación**: Haz clic en **Confirmar Pedido**. Verás que el estado cambia a **Por Asignar**.
6.  **Finalización**: Haz clic en **Generar Carta Porte**. ¡Listo! Ya puedes imprimir el PDF.

### Escenario B: Validación de Seguridad (Provocar error)

1.  Crea un viaje nuevo pero **NO pongas peso** en la mercancía.
2.  Intenta hacer clic en **Confirmar Pedido**.
3.  **Resultado esperado**: El sistema debe detenerte con una alerta roja diciendo que el peso es obligatorio para Carta Porte 3.1.

### Escenario C: Dashboard Kanban (Gestión de Flota)

1.  Arrastra un viaje de la columna **Solicitud** a **En Trayecto**.
2.  Entra al viaje y verifica que la **Fecha de Inicio de Ruta** se haya llenado automáticamente (Plan B manual).

---

## 🛠 4. Solución de Problemas Comunes (FAQ)

**¿Por qué no puedo generar la Carta Porte?**

> Revisa el RFC del chofer o del cliente. El SAT requiere 12 o 13 caracteres exactos. El sistema te avisará en una caja amarilla si falta información.

**¿Las casetas no se calculan?**

> Usa el botón **"Calcular Ruta (Smart)"**. Si el servidor tiene internet y la API Key de Google configurada, traerá la distancia real y el costo de peajes actual.

**¿Cómo firmo el documento?**

> Ve a la pestaña **Firma Digital**. Si el chofer usa la App, aparecerá ahí su firma con coordenadas GPS. Si es manual, puedes subir una imagen de firma.

---

## 📊 5. Qué revisar en el Dashboard

El Dashboard de TMS te dará gráficas de:

- **Margen de Utilidad**: ¿Cuánto estamos ganando por viaje?
- **Diesel**: Compara el precio del diesel en el historial contra lo que se cotizó.
- **Ubicación**: Mira en el mapa dónde están tus viajes "En Trayecto".

---

_Desarrollado por Nextpack.mx para el ambiente de QA Odoo 19._
