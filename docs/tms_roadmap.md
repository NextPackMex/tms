# Checklist: TMS "Hombre Camión" vs Odoo Actual

Este listado compara las necesidades típicas de un "Hombre Camión" (basado en el video y mejores prácticas) contra lo que tenemos desarrollado en el módulo `tms` actual.

## 1. Gestión de Viajes y Carta Porte (Core)

| Estado | Característica            | Descripción                                                                                                                      |
| :----: | :------------------------ | :------------------------------------------------------------------------------------------------------------------------------- |
|  [x]   | **Registro de Viaje**     | Origen, Destino, Cliente, Chofer, Vehículo. (Ya existe en `tms.waybill`).                                                        |
|  [/]   | **Carta Porte 3.1**       | Tenemos los campos de captura (tms.waybill), pero **falta la generación del XML** y la conexión con el PAC.                      |
|  [x]   | **Rutas Frecuentes**      | Guardado de rutas repetitivas para llenado rápido.                                                                               |
|  [/]   | **Cálculo de Distancias** | Integración con Google Maps para kms y tiempos (Implementado). Falta validar si incluye "Casetas" en costos reales vs estimados. |
|  [ ]   | **Bitácora de Estatus**   | Registro automático de "Cargando", "En Ruta", "Descargando" (Simple o por App móvil).                                            |

## 2. Gestión de Flota (Vehículos)

| Estado | Característica             | Descripción                                                                                                               |
| :----: | :------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
|  [x]   | **Expediente Digital**     | Placas, Marca, Modelo, Pólizas de Seguro. (Heredado de `fleet.vehicle`).                                                  |
|  [x]   | **Configuración SAT**      | Claves de configuración vehicular (C2, T3S2) y permisos SCT.                                                              |
|  [/]   | **Mantenimiento**          | Uso del módulo nativo de Odoo (`fleet`). Falta vincularlo al viaje (ej. no iniciar viaje si hay mantenimiento pendiente). |
|  [ ]   | **Gestión de Llantas**     | (CRÍTICO) Control de posición, vida útil, renovado y desgaste de llantas. No existe actualmente.                          |
|  [ ]   | **Alertas de Vencimiento** | Alertas visuales para vencimiento de Seguros, Licencias y Verificaciones.                                                 |

## 3. Gastos y Liquidaciones (Dinero)

| Estado | Característica                 | Descripción                                                                                                                                       |
| :----: | :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
|  [/]   | **Control de Combustible**     | Odoo nativo tiene logs de combustible, pero no está enlazado directo al Viaje (`tms.waybill`) para deducir del pago al chofer.                    |
|  [ ]   | **Control de Gastos de Viaje** | Registro de Maniobras, Viáticos, Comidas, Reparaciones en ruta. Solo tenemos `cost_tolls` (Casetas).                                              |
|  [ ]   | **Liquidación al Chofer**      | Cálculo de cuánto se le paga al operador (por % del flete, por KM o sueldo fijo) menos sus gastos/anticipos. Esto es vital para el hombre camión. |
|  [ ]   | **Anticipos**                  | Registro de dinero entregado al chofer antes de salir.                                                                                            |

## 4. Facturación

| Estado | Característica          | Descripción                                                                                                   |
| :----: | :---------------------- | :------------------------------------------------------------------------------------------------------------ |
|  [/]   | **Factura de Ingreso**  | Se puede facturar desde el pedido, pero falta automatizar que el `tms.waybill` genere la factura con un clic. |
|  [ ]   | **Factura de Traslado** | Generación automática de CFDI de Traslado para mercancía propia (sin venta).                                  |

---

## Resumen de Prioridades Faltantes

1.  **Llantas**: El gasto #2 más grande después del Diesel.
2.  **Liquidación**: Saber cuánto ganó realmente en el viaje (Ingreso - Diesel - Casetas - Pago Chofer).
3.  **Conexión PAC**: Sin timbrado real, no cumple el SAT.
