# -*- coding: utf-8 -*-
"""
Traducción de códigos de error SAT/PAC a mensajes en lenguaje
del transportista (Modo Hombre Camión).

Uso:
    from .cfdi_errors import traducir_error
    mensaje_humano = traducir_error(str(excepcion))
"""

# Diccionario de traducción: clave técnica → mensaje comprensible
ERRORES_SAT = {
    # --- Estructura del Complemento Carta Porte ---
    'IdCCP': (
        "El ID de Carta Porte está vacío o tiene formato incorrecto. "
        "Contacta al administrador."
    ),
    'FiguraTransporte': (
        "Falta información del chofer (RFC, nombre o número de licencia)."
    ),
    'Autotransporte': (
        "Falta información del vehículo (configuración SCT, permiso o peso)."
    ),
    'PermSCT': (
        "Falta el tipo de permiso SCT del vehículo. "
        "Configúralo en Flota → vehículo → pestaña TMS."
    ),
    'NumPermisoSCT': (
        "Falta el número de permiso SCT del vehículo. "
        "Configúralo en Flota → vehículo → pestaña TMS."
    ),
    'ConfigVehicular': (
        "Falta la configuración vehicular SCT (ej: C2, T3S2). "
        "Configúrala en Flota → vehículo → pestaña TMS."
    ),
    'AnioModeloVM': (
        "Falta el año del modelo del vehículo. "
        "Configúralo en Flota → vehículo."
    ),
    'PesoBrutoVehicular': (
        "Falta el peso bruto del vehículo en toneladas. "
        "Configúralo en Flota → vehículo → pestaña TMS."
    ),
    'Seguros': (
        "Faltan datos de seguros del vehículo (aseguradora o póliza RC). "
        "Configúralos en Ajustes → Empresa → pestaña Fiscal TMS."
    ),
    'AseguraRespCivil': (
        "Falta la aseguradora de Responsabilidad Civil. "
        "Configúrala en Ajustes → Empresa → pestaña Fiscal TMS."
    ),
    'PolizaRespCivil': (
        "Falta el número de póliza de Responsabilidad Civil. "
        "Configúrala en Ajustes → Empresa → pestaña Fiscal TMS."
    ),

    # --- Figura Transporte (chofer) ---
    'RFCFigura': (
        "Falta el RFC del chofer. "
        "Configúralo en Empleados → chofer → pestaña TMS."
    ),
    'NombreFigura': (
        "Falta el nombre del chofer. "
        "Verifica en Empleados → chofer."
    ),
    'NumLicencia': (
        "Falta el número de licencia federal del chofer. "
        "Configúralo en Empleados → chofer → pestaña TMS."
    ),

    # --- Datos del CFDI (emisor/receptor) ---
    'RFC': (
        "El RFC del emisor o receptor no es válido. "
        "Verifica en Ajustes → Empresa o en el contacto del cliente."
    ),
    'RegimenFiscal': (
        "Falta el régimen fiscal del emisor o receptor. "
        "Verifica en Ajustes → Empresa o en el contacto del cliente."
    ),
    'DomicilioFiscalReceptor': (
        "Falta el código postal fiscal del cliente (receptor). "
        "Configúralo en el contacto del cliente."
    ),
    'LugarExpedicion': (
        "Falta el código postal de la empresa emisora. "
        "Configúralo en Ajustes → Empresa → Dirección."
    ),

    # --- Mercancías ---
    'BienesTransp': (
        "Una mercancía no tiene la Clave SAT asignada. "
        "Verifica las mercancías del viaje."
    ),
    'PesoEnKg': (
        "Una mercancía no tiene el peso capturado. "
        "Verifica las mercancías del viaje."
    ),

    # --- Ubicaciones ---
    'Ubicaciones': (
        "Faltan las ubicaciones de origen o destino del viaje."
    ),
    'CodigoPostal': (
        "El código postal de origen o destino no es válido o está vacío."
    ),

    # --- Códigos de error PAC Formas Digitales / SW Sapien ---
    'CFDI40999': (
        "El XML tiene un error de estructura. "
        "Revisa que todos los datos del viaje estén completos."
    ),
    'CFDI33111': (
        "El RFC del emisor no está en la lista de contribuyentes activos del SAT."
    ),
    'CFDI33112': (
        "El RFC del receptor no está en la lista de contribuyentes activos del SAT."
    ),
    'CFDI33196': (
        "El certificado CSD está vencido o no es válido. "
        "Actualiza el CSD en Ajustes → Empresa → Fiscal TMS."
    ),
    'CFDI33193': (
        "La contraseña del CSD es incorrecta. "
        "Verifica en Ajustes → Empresa → Fiscal TMS."
    ),

    # --- Errores de conexión/red ---
    '404': (
        "No se pudo conectar al servidor del PAC (error 404). "
        "Verifica que la URL del servicio esté configurada correctamente."
    ),
    '401': (
        "Credenciales incorrectas del PAC (error 401). "
        "Verifica usuario y contraseña en Ajustes → Empresa → PAC."
    ),
    '500': (
        "El servidor del PAC tuvo un error interno (error 500). "
        "Intenta de nuevo en unos minutos."
    ),
    'timeout': (
        "El servidor del PAC tardó demasiado en responder. "
        "Intenta de nuevo en unos minutos."
    ),
    'Timeout': (
        "El servidor del PAC tardó demasiado en responder. "
        "Intenta de nuevo en unos minutos."
    ),
    'Incorrect password': (
        "La contraseña del certificado CSD es incorrecta. "
        "Verifica en Ajustes → Empresa → Fiscal TMS."
    ),
    'agotado': (
        "El servidor del PAC tardó demasiado en responder. "
        "Intenta de nuevo en unos minutos."
    ),
    'ConnectionError': (
        "No se pudo establecer conexión con el PAC. "
        "Verifica tu conexión a internet."
    ),
    'acuseCFDI': (
        "El PAC no devolvió el XML timbrado. "
        "Revisa que el CFDI tenga todos los campos obligatorios."
    ),
}


def traducir_error(mensaje_tecnico: str) -> str:
    """
    Traduce un mensaje técnico del SAT/PAC a lenguaje comprensible
    para el transportista.

    Busca coincidencias parciales de las claves del diccionario dentro
    del mensaje técnico (orden de prioridad: primero encontrado, primero usado).

    Args:
        mensaje_tecnico: str con el error original del SAT o PAC

    Returns:
        str: mensaje traducido, o el mensaje original si no hay traducción
    """
    for clave, traduccion in ERRORES_SAT.items():
        if clave in mensaje_tecnico:
            return traduccion
    return (
        f"Error técnico del SAT/PAC: {mensaje_tecnico}\n"
        f"Si el problema persiste, contacta al administrador."
    )
