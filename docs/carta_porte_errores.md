# Matriz de Errores Carta Porte 3.1 (Resumen)

El documento oficial "Matriz de Errores" lista los códigos de validación que el SAT y los PACs utilizan para rechazar un CFDI si no cumple con las reglas. A continuación, los errores más comunes y críticos:

## 1. Errores Generales del CFDI (CP100 - CP110)

| Código    | Error Común           | Explicación                                                   |
| :-------- | :-------------------- | :------------------------------------------------------------ |
| **CP101** | Versión Incorrecta    | La versión del CFDI debe ser **4.0**.                         |
| **CP102** | Subtotal no Cero      | Si es **Traslado**, el Subtotal debe ser **0**.               |
| **CP103** | Moneda en Traslado    | Si es **Traslado**, Moneda debe ser **XXX**.                  |
| **CP104** | Moneda en Ingreso     | Si es **Ingreso**, Moneda **NO** puede ser XXX.               |
| **CP105** | Total no Cero         | Si es **Traslado**, el Total debe ser **0**.                  |
| **CP108** | RFC Receptor Inválido | En Ingreso, el RFC receptor debe estar activo y no cancelado. |

## 2. Errores de Ubicación (CP130 - CP150)

| Código    | Error Común         | Explicación                                                                            |
| :-------- | :------------------ | :------------------------------------------------------------------------------------- |
| **CP138** | Estación Extranjera | Si la estación es extranjera, se debe registrar el `NombreEstacion` y no "Extranjera". |
| **CP141** | Falta Distancia     | Se requiere `DistanciaRecorrida` en destinos (excepto local/marítimo).                 |
| **CP142** | Código Postal       | El Código Postal debe coincidir con el catálogo de `c_Colonia`.                        |

## 3. Errores de Mercancías y Figuras (CP190+)

| Código    | Error Común          | Explicación                                                                                      |
| :-------- | :------------------- | :----------------------------------------------------------------------------------------------- |
| **CP194** | Falta Operador       | Debe existir al menos una figura tipo `01` (Operador) si hay autotransporte.                     |
| **CP202** | Peso Bruto Vehicular | El `PesoBrutoVehicular` debe estar dentro del rango permitido para la `ConfigVehicular` elegida. |
| **CP203** | Placa Inválida       | El formato de la `PlacaVM` no coincide con el patrón esperado de la SCT.                         |

## 4. Recomendación para Desarrollo

- **Pre-Validación**: Implementar validaciones en Odoo (Python constraints) que "atrapen" estos errores antes de intentar timbrar.
- **Mapeo de Errores**: Cuando el PAC regrese un error (ej. "Error CP102"), mostrar al usuario un mensaje amigable: "Tu CFDI de Traslado tiene un monto mayor a cero, por favor corrígelo".

> [!NOTE]
> La matriz completa es un archivo Excel vivo que el SAT actualiza. Es vital revisar la versión más reciente en el portal del SAT ante rechazos desconocidos.
