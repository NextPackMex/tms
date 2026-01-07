# Carta Porte 3.1 y el Régimen "Hombre Camión" (2024-2025)

## 1. Contexto del Video Proporcionado

El video "GM Transport, Hombre-Camión (DEMO)" referenciado es de **2012**.

- **Relevancia**: Muestra el concepto general de gestión transporte para pequeños transportistas.
- **Obsolescencia**: La normativa técnica mostrada es obsoleta. Hoy rige la **Carta Porte 3.1** (obligatoria desde julio 2024), con reglas fiscales y digitales (CFDI 4.0) muy diferentes operativamente a lo que existía en 2012.

## 2. Definición "Hombre Camión" ante el SAT

Se refiere comúnmente al transportista persona física o pequeño contribuyente (Régimen de Coordinados o PFAE) que cuenta con unidades propias (1 a 5 usualmente) y las opera personalmente o con pocos choferes.

## 3. Obligaciones Carta Porte 3.1 Clave

El "Hombre Camión" tiene obligaciones específicas dependiendo de si cobra por el flete o mueve mercancía propia:

### A. Si Cobra por el Servicio (Flete)

- **Tipo de CFDI**: **Ingreso**.
- **Complemento**: **Obligatorio** Carta Porte 3.1.
- **Requisito**: Debe desglosar el servicio de transporte y añadir el complemento con todos los datos de la carga, ruta y vehículo.

### B. Si Traslada Mercancia Propia (o de su Agrupación)

- **Tipo de CFDI**: **Traslado**.
- **Complemento**: **Obligatorio** Carta Porte 3.1.
- **Uso**: Para amparar la tenencia y traslado legal de los bienes en carretera federal, aunque no haya cobro explícito por ese viaje específico.

### C. Excepciones Comunes (Facilidades Administrativas)

No están obligados a emitir el complemento (pero sí la factura de ingreso por el servicio) si:

1.  **Transporte Local**: No transitan por carreteras federales (solo calles locales/estatales).
2.  **Tramo Federal Menor**: Usan vehículos ligeros (tipo C2 o menor) y el tramo federal recorrido no excede los **30 km**.

## 4. Detalles Técnicos Específicos (Nodos Relevantes)

En el llenado del XML 3.1, el "Hombre Camión" debe prestar atención a:

- **FiguraTransporte (TiposFigura)**:
  - Clave `01`: Operador (si él mismo maneja).
  - Clave `05`: **Integrante de Coordinados** (Nueva clave relevante si pertenece a una agrupación de transportistas).
- **Vehículo**: Debe tener sus permisos SCT vigentes (aunque sea hombre camión, requiere permiso de carga general o privada).
- **Seguros**: Póliza de responsabilidad civil vigente y capturada en el nodo `Seguros`.

## 5. Resumen

Aunque el software del video es antiguo, la necesidad de gestión es la misma. Para Odoo, el "Hombre Camión" requiere un flujo simplificado donde pueda emitir rápidamente su CFDI (Ingreso o Traslado) cumpliendo con los 180+ requisitos de la versión 3.1.
