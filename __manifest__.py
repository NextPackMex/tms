# -*- coding: utf-8 -*-
{
    # Nombre del módulo
    'name': "TMS & Carta Porte 3.1 (SaaS Multi-Empresa)",

    # Resumen corto
    'summary': """
        Base de datos completa de catálogos oficiales del SAT para Carta Porte 3.1
        11 catálogos + Wizard de importación Excel
    """,

    # Descripción detallada
    'description': """
        TMS - Base de Catálogos SAT (Carta Porte 3.1)
        ==============================================

        Módulo independiente con TODOS los catálogos oficiales del SAT
        necesarios para Carta Porte 3.1.

        📦 CATÁLOGOS INCLUIDOS (11):

        Productos y Mercancías:
        • c_ClaveProdServCP - Clave Producto/Servicio
        • c_ClaveUnidad - Unidades de Medida
        • c_TipoEmbalaje - Tipos de Embalaje
        • c_MaterialPeligroso - Materiales Peligrosos

        Ubicaciones Geográficas:
        • c_CodigoPostal - Códigos Postales
        • c_Colonia - Colonias
        • c_Localidad - Localidades
        • c_Municipio - Municipios

        Configuración de Transporte:
        • c_ConfigAutotransporte - Configuración Vehicular
        • c_TipoPermiso - Tipos de Permiso SCT
        • c_FiguraTransporte - Figuras de Transporte

        🚀 CARACTERÍSTICAS:
        - Importación masiva desde Excel (.xlsx)
        - Wizard universal con dropdown de 11 catálogos
        - Batch create optimizado (1,000 registros/lote)
        - Índices en BD para búsquedas ultra-rápidas
        - Catálogos globales (sin company_id)
        - Búsqueda avanzada por código y descripción

        💡 USO:
        1. Descargar catálogos del SAT
        2. Usar wizard de importación
        3. Listo para usar en Carta Porte
    """,

    # Autor
    'author': "nextpack.mx",

    # Sitio web
    'website': "https://www.nextpack.mx",

    # Categoría
    'category': 'Logistics',

    # Versión
    'version': '19.0.1.0.0',

    # Dependencias para Fase 2: Flota y Dashboard
    # sale_management: Para reutilizar estética de portal de Sales (sin convertir waybill en sale.order)
    'depends': ['base', 'fleet', 'account', 'contacts', 'board', 'mail', 'portal', 'web', 'website', 'sale_management', 'hr'],
    # NOTA: Los catálogos SAT están en este mismo módulo, no necesitamos dependencia externa

    # Archivos de datos (orden estricto de carga)
    'data': [
        # 1. Seguridad Multi-Empresa (SIEMPRE PRIMERO)
        # IMPORTANTE: tms_security.xml ANTES que ir.model.access.csv
        # porque el CSV usa los grupos definidos en el XML
        'security/tms_security.xml',          # Define grupos (group_tms_user, group_tms_manager)
        'security/ir.model.access.csv',       # USA los grupos (debe cargar después)

        # 2. Datos iniciales (secuencias)
        'data/tms_sequence_data.xml',
        'data/tms_data.xml',


        # 3. Wizard de importación
        'wizard/sat_import_wizard_views.xml',
        'wizard/partner_assign_company_wizard_views.xml',

        # 3. Vistas de Catálogos SAT (orden alfabético)
        'views/sat_clave_prod_views.xml',
        'views/sat_clave_unidad_views.xml',
        'views/sat_codigo_postal_views.xml',
        'views/sat_colonia_views.xml',
        'views/sat_config_autotransporte_views.xml',
        'views/sat_embalaje_views.xml',
        'views/sat_figura_transporte_views.xml',
        'views/sat_localidad_views.xml',
        'views/sat_material_peligroso_views.xml',
        'views/sat_municipio_views.xml',
        'views/sat_tipo_permiso_views.xml',

        # 3.1 Extensiones de modelos base SAT
        'views/res_partner_tms_view.xml',
        'views/res_partner_tms_modals_view.xml',
        'views/hr_employee_views.xml',

        # 4. Vistas de Flota (extensión de módulo nativo)
        'views/tms_vehicle_type_view.xml',
        'views/tms_fleet_vehicle_views.xml',

        # 5. Vistas de Destinos/Rutas
        'views/tms_destination_views.xml',

        # 6. Vistas de Viajes (Dashboard Kanban - MODELO MAESTRO)
        'views/tms_waybill_views.xml',
        'views/tms_fuel_history_views.xml',

        # 7. Dashboard
        'views/tms_dashboard_views.xml',

        # 8. Plantillas del Portal Web (Firma Digital)
        'views/tms_portal_templates.xml',

        # 9. Reportes PDF
        'reports/tms_waybill_report.xml',
        'data/mail_template_data.xml',

        # 10. Menús (AL FINAL para que todas las acciones estén disponibles)
        # IMPORTANTE: tms_menus.xml ANTES de sat_menus.xml
        # porque sat_menus.xml usa action_tms_dashboard que se define en tms_menus.xml
        'views/tms_menus.xml',               # Define action_tms_dashboard y menús operativos
        'views/res_config_settings_views.xml', # Depende de menu_tms_config
        'views/sat_menus.xml',               # Usa menu_tms_root y action_tms_dashboard
    ],

    'assets': {
        'web.assets_backend': [
            'tms/static/src/js/tms_portal_link_handler.js',
        ],
        # Assets para portal: JS y CSS para vista moderna estilo Sales
        'web.assets_frontend': [
            'tms/static/src/js/tms_portal_signature_modal.js',
            'tms/static/src/css/tms_portal_signature_modal.css',
        ],
    },

    # Datos demo (vacío por ahora)
    'demo': [],

    # Es una aplicación independiente
    'application': True,

    # Se puede instalar
    'installable': True,

    # No se auto-instala
    'auto_install': False,

    # Licencia
    'license': 'LGPL-3',
}
