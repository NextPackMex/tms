# Análisis XSD Carta Porte 3.1

**Fuente**: [CartaPorte31.xsd](http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd)
**Target Namespace**: `http://www.sat.gob.mx/CartaPorte31`

## 1. Elemento Raíz: `CartaPorte`

- **Prefijo**: `cartaporte31`
- **Versión**: 3.1

### Atributos Globales Clave

- `Version`: Fijo a "3.1"
- `TranspInternac`: "Sí" o "No". Determina validaciones condicionales.
- `RegimenAduanero`: (Eliminado en 3.1 - reemplazado por nodo).
- `EntradaSalidaMerc`: 'Entrada' o 'Salida' (Requerido si `TranspInternac`="Sí").
- `PaisOrigenDestino`: Código de país (Requerido si `TranspInternac`="Sí").
- `ViaEntradaSalida`: Código de medio de transporte (Requerido si `TranspInternac`="Sí").
- `TotalDistRec`: Suma total de distancia de todos los segmentos.
- `RegistroISTMO`: Opcional (Sí/No).
- `UbicacionPoloOrigen`: Opcional.
- `UbicacionPoloDestino`: Opcional.

## 2. Estructura Principal

### A. `RegimenesAduaneros` (Nuevo en 3.1)

_Condicional (MinOccurs: 0, MaxOccurs: 1)_

- Contenedor para regímenes aduaneros.
- **Hijos**:
  - `RegimenAduaneroCCP` (MaxOccurs: 10)
    - `RegimenAduanero`: Atributo, catálogo `c_RegimenAduanero`.

### B. `Ubicaciones`

_Requerido_

- **Hijos**:
  - `Ubicacion` (MinOccurs: 2, MaxOccurs: Ilimitado)
    - `TipoUbicacion`: "Origen" o "Destino".
    - `IDUbicacion`: Patrón `(OR|DE)[0-9]{6}`.
    - `RFCRemitenteDestinatario`: RFC Requerido.
    - `FechaHoraSalidaLlegada`: Requerido.
    - `DistanciaRecorrida`: Opcional (Requerido para Destino excepto local/marítimo).
    - **Domicilio**: Nodo hijo, atributos de dirección estándar (Calle, Estado, País, CódigoPostal, etc.).

### C. `Mercancias`

_Requerido_

- **Atributos**:
  - `PesoBrutoTotal`: Suma de todo el peso de mercancías.
  - `unidadPeso`: Catálogo `c_ClaveUnidadPeso`.
  - `NumTotalMercancias`: Conteo.
  - `LogisticaInversaRecoleccionDevolucion`: Opcional (Sí/No).
- **Hijos**:

  - `Mercancia` (MinOccurs: 1, MaxOccurs: Ilimitado)

    - **Atributos Clave**:
      - `BienesTransp`: Clave producto (`c_ClaveProdServCP`).
      - `Descripcion`: Texto descriptivo.
      - `Cantidad`: Decimal.
      - `ClaveUnidad`: Catálogo `c_ClaveUnidad`.
      - `PesoEnKg`: Decimal requerido.
      - `MaterialPeligroso`: "Sí" o "No".
      - `CveMaterialPeligroso`: Requerido si MaterialPeligroso="Sí" (Catálogo).
      - `FraccionArancelaria`: Opcional/Condicional (`c_FraccionArancelaria`).
    - **Sub-elementos**:
      - `Pedimentos` (Lista de documentos aduaneros válidos).
      - `GuiasIdentificacion`.
      - `CantidadTransporta` (Distribución de cantidad a ID destino).
      - `DetalleMercancia`.

  - `Autotransporte` (Condicional)

    - `PermSCT`: Tipo de permiso.
    - `NumPermisoSCT`: Número de permiso.
    - `IdentificacionVehicular`: ConfigVehicular (`c_ConfigAutotransporte`), PlacaVM, AnioModeloVM.
    - `Seguros`: AseguraRespCivil, PolizaRespCivil.
    - `Remolques`:
      - `Remolque`: SubTipoRem, Placa.

  - `TransporteMaritimo` (Actualizado en 3.1)
  - `TransporteAereo`
  - `TransporteFerroviario`

## 3. Tipos de Datos Notables

- **Decimales**: La mayoría de campos de peso y cantidad usan `xs:decimal` con dígitos de fracción específicos (usualmente 3 o 6).
- **Catálogos**: Fuerte dependencia de catálogos externos (ej. `catCartaPorte`, `catComExt`, `catCFDI`).
