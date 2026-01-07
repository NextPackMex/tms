# Investigación y Análisis de Carta Porte 3.1

## 1. Resumen General

El **Complemento Carta Porte (CCP) versión 3.1** fue publicado por el SAT y es obligatorio a partir del **17 de julio de 2024**. Reemplaza a la versión 3.0.

- **Objetivo**: Mejorar la trazabilidad del transporte de mercancías en México.
- **Mandato**: Requerido para todos los contribuyentes que transporten bienes (propietarios o intermediarios) vía federal, férrea, aérea o marítima.

## 2. Cambios Técnicos Clave (v3.0 -> v3.1)

Basado en documentación técnica y anuncios del SAT:

### A. Cambios de Régimen

- **Atributo `RegimenAduanero` Eliminado**: El atributo simple ha desaparecido.
- **Nuevo Nodo `RegimenesAduanerosCCP`**: Un nuevo nodo hijo permite especificar **hasta 10** regímenes aduaneros diferentes para la misma carta porte.
  - Útil para envíos con regímenes mixtos (ej. importación definitiva + importación temporal).

### B. Fracción Arancelaria

- **Ahora Opcional (Condicional)**: El campo `Fracción Arancelaria` ahora es opcional cuando el atributo `TranspInternac` (Transporte Internacional) es "Sí".
- **Validación Relajada**: Previamente se verificaba contra un catálogo estricto para todos los movimientos transfronterizos; ahora esta validación es condicional.

### C. Marítimo

- **RemolquesCCP**: Agregado como sub-nodo de `Contenedor` para transporte marítimo, permitiendo detalles como `SubTipoRemCCP` y `PlacaCCP`.

### D. Materiales Peligrosos

- **Actualización NOM**: Referencia actualizada a `NOM-002-SCTSEMAR-ARTF/2023`.
- **Actualización de Catálogo**: 60 nuevas claves añadidas al catálogo de materiales peligrosos.

### E. Otras Mejoras Técnicas

- **Código QR**: Longitud de cadena fijada a 36 caracteres para mejor escaneo.
- **Descripciones de Campos**: Definiciones más claras para `CveMaterialPeligroso`, `PesoBrutoVehicular`, etc.

## 3. Estado de la Implementación en Odoo (Espacio de Trabajo Actual)

### Hallazgos

1.  **Módulo personalizado `tms`** (`proyectos/tms`):

    - **No se encontraron referencias** a `Carril`, `CartaPorte`, `CCP`, o lógica específica de versiones (3.0/3.1).
    - Este módulo probablemente maneja la _logística_ (Talón de embarque, Ruta, Viaje) pero depende de otra capa para la generación del XML fiscal.

2.  **Addons Nativos de Odoo** (`odoo-18.0/addons`):
    - Se encontraron `l10n_mx` (Contabilidad básica) y `l10n_mx_hr` (Nómina).
    - **Falta `l10n_mx_edi`**: El módulo estándar para Facturación Electrónica (y timbrado de Carta Porte) no está presente o instalado en esta ruta. Esto es común en Odoo Community Edition (CE) a menos que se usen librerías de terceros.

### Recomendaciones para Odoo 18

Para implementar Carta Porte 3.1 en este entorno:

1.  **Determinar el Proveedor EDI**:
    - Si usa **Odoo Enterprise**: Instalar `l10n_mx_edi_stock` (not visible currently).
    - Si usa **Odoo Community**: Necesitará un conector de terceros (ej. OCA o proveedor privado) que soporte CCP 3.1.
2.  **Actualizar Módulo `tms`**:
    - Necesitará mapear los campos del Talón de Embarque TMS (`tms.waybill`) a las estructuras del proveedor EDI.
    - **Nuevos Campos Requeridos**: Agregar campos para `RegimenesAduanerosCCP` (One2many) en el Talón o líneas relacionadas.
