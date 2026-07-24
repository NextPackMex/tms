# -*- coding: utf-8 -*-
{
    # Nombre del módulo
    'name': "TMS & Carta Porte 3.1 (SaaS Multi-Empresa)",

    # Resumen corto
    'summary': "Sistema de Gestión de Transporte (TMS) con Carta Porte 3.1 y CFDI 4.0 para México",

    # Descripción detallada
    'description': """
        TMS "Hombre Camión" — Sistema Integral de Transporte
        =====================================================

        Solución vertical completa para cotización, operación y facturación de servicios
        de transporte de carga en México, con cumplimiento fiscal y SaaS multi-empresa.

        🚚 FUNCIONALIDADES PRINCIPALES:

        1. COTIZACIÓN INTELIGENTE
           • 3 propuestas (por km, por viaje con costos, precio directo)
           • Integración TollGuru API: distancia, duración, casetas en tiempo real
           • Caché de rutas para optimizar consultas

        2. CARTA PORTE 3.1 + TIMBRADO
           • Validación automática de cumplimiento CP 3.1
           • Timbrado via PAC Formas Digitales (contrato activo)
           • UUID obtenido, PDF de 7 secciones + QR SAT

        3. FACTURACIÓN REAL (CFDI INGRESO)
           • Consolidación de N waybills en una factura
           • IVA 16% + Retención 4% (si is_company=True)
           • Zonas de Exportación Temporal (ZEDE) con IVA 0%
           • Cancelación con motivos 01/02/03 SAT, re-timbrado automático

        4. PORTAL WEB CLIENTE
           • Lista paginada de viajes con filtros y búsqueda
           • Timeline de tracking con eventos GPS y maps
           • Descarga XML CFDI Ingreso timbrado
           • Firma digital para aceptación de cotizaciones
           • Seguridad multiempresa SaaS

        5. DASHBOARD OPERATIVO + KPIs
           • Viajes activos, facturación del mes, por facturar
           • Rentabilidad por ruta (tms.route.stats)
           • Rendimiento por vehículo (km/litro real)
           • Alertas automáticas (licencias vencidas, CFDIs pendientes)

        6. TOURS INTERACTIVOS
           • Onboarding para nuevos usuarios
           • 8 micro-tours temáticos + panel ❓
           • Documentación integrada en UI

        7. ARQUITECTURA SAAS MULTI-EMPRESA
           • Catálogos SAT globales (sin company_id)
           • Datos operativos privados por empresa
           • Record rules para aislamiento total
           • Preparada para monetización en V2.8

        🎯 CASOS DE USO:
        - Transportistas pequeños/medianos: cotización + operación integral
        - Embarcadores: transparencia en flete + trazabilidad
        - Plataformas SaaS: modelo white-label con multi-tenancy

        📋 CATÁLOGOS INCLUIDOS: 12 catálogos SAT completos
        (Productos, Unidades, Embalaje, Materiales Peligrosos, Geografía, Configuración Vehicular)

        ⚙️ INTEGRACIONES:
        - TollGuru API v2: rutas y casetas
        - PAC Formas Digitales: timbrado CFDI
        - PostgreSQL 16+: BD de producción
        - OWL + QWeb: UI moderna Odoo 19 CE

        📌 VERSIÓN: 2.7 (Limpieza Final + QA)
        🏁 SIGUIENTE: V2.8 (SaaS — Primer Cliente Paga)
    """,

    # Autor
    'author': "nextpack.mx",

    # Sitio web
    'website': "https://www.nextpack.mx",

    # Categoría
    'category': 'Logistics',

    # Versión
    'version': '19.0.2.7.0',

    # Dependencias para Fase 2: Flota y Dashboard
    # sale_management: Para reutilizar estética de portal de Sales (sin convertir waybill en sale.order)
    'depends': ['base', 'fleet', 'account', 'contacts', 'board', 'mail', 'portal', 'web', 'website', 'sale_management', 'hr', 'web_tour'],
    # NOTA: Los catálogos SAT están en este mismo módulo, no necesitamos dependencia externa

    # Archivos de datos (orden estricto de carga)
    'data': [
        # 1. Seguridad Multi-Empresa (SIEMPRE PRIMERO)
        # IMPORTANTE: tms_security.xml ANTES que ir.model.access.csv
        # porque el CSV usa los grupos definidos en el XML
        'security/tms_security.xml',          # Define grupos (group_tms_user, group_tms_manager)
        'security/ir.model.access.csv',       # USA los grupos (debe cargar después)
        'views/tms_menu_skeleton.xml',   # Esqueleto de menus raiz (early, evita forward-refs)

        # 2. Datos iniciales (secuencias + catálogos SAT pequeños)
        'data/tms_sequence_data.xml',
        'data/tms_data.xml',
        'data/sat_regimen_fiscal.xml',
        'data/tms_expense_type.xml',     # Catálogo: Tipos de Gasto (V2.3.3)
        'data/tms.sat.zona.especial.csv',
        'data/tms.sat.uso.cfdi.csv',
        'data/tms.sat.forma.pago.csv',
        'data/tms.sat.metodo.pago.csv',
        'data/tms.sat.tipo.relacion.csv',
        'data/tms.sat.periodicidad.pago.csv',


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

        # 3.1 Catálogos CFDI 4.0 (Sección 4: UsoCFDI, FormaPago, MetodoPago, TipoRelacion, Periodicidad)
        'views/tms_sat_catalogos_views.xml',

        # 3.2 Extensiones de modelos base SAT
        'views/res_company_views.xml',
        'views/res_partner_tms_view.xml',
        'views/res_partner_tms_modals_view.xml',
        'views/hr_employee_views.xml',

        # 4. Vistas de Flota (extensión de módulo nativo)
        'views/tms_vehicle_type_view.xml',
        'views/tms_fleet_vehicle_views.xml',

        # 5. Vistas de Destinos/Rutas
        'views/tms_destination_views.xml',

        # 6. Wizard cotización (ANTES de tms_waybill_views para que action_tms_cotizacion_wizard exista)
        'wizard/tms_cotizacion_wizard_views.xml',
        'wizard/tms_onboarding_wizard_views.xml',
        'wizard/tms_stamp_validation_wizard_views.xml',
        'wizard/tms_invoice_wizard_views.xml',
        'wizard/tms_cancel_invoice_wizard_views.xml',
        'wizard/tms_cancel_traslado_wizard_views.xml',

        # 7. Vistas de Viajes (Dashboard Kanban - MODELO MAESTRO)
        'views/tms_waybill_views.xml',
        'views/tms_fuel_history_views.xml',
        'views/account_move_tms_views.xml',
        'views/tms_expense_type_views.xml',  # Catálogo: Tipos de Gasto (V2.3.3)
        'views/tms_expense_views.xml',      # Gasto Real del Viaje (V2.3.3)
        'views/tms_liquidacion_views.xml',  # Liquidación de Viaje (V2.3.3)
        'views/tms_evidence_views.xml',     # Evidencia Fotográfica (V2.4b)

        # 8. Dashboard y Analytics
        'views/tms_route_stats_views.xml',
        'views/tms_dashboard_views.xml',

        # 9. Plantillas del Portal Web (Firma Digital)
        'views/tms_portal_templates.xml',

        # 10. Reportes PDF
        'reports/tms_waybill_report.xml',
        'reports/tms_cotizacion_report.xml',
        'reports/tms_cotizacion_report_template.xml',
        'reports/tms_carta_porte_report.xml',
        'reports/tms_carta_porte_report_template.xml',
        'reports/tms_invoice_report.xml',
        'data/mail_template_data.xml',
        'data/mail_template_cotizacion.xml',

        # 11. Menús (AL FINAL para que todas las acciones estén disponibles)
        # IMPORTANTE: tms_menus.xml ANTES de sat_menus.xml
        # porque sat_menus.xml usa action_tms_dashboard que se define en tms_menus.xml
        'views/tms_menus.xml',               # Define action_tms_dashboard y menús operativos
        'views/res_config_settings_views.xml', # Depende de menu_tms_config
        'views/sat_menus.xml',               # Usa menu_tms_root y action_tms_dashboard
        'wizard/tms_load_demo_wizard_view.xml', # Load after menus
    ],

    'assets': {
        'web.assets_backend': [
            'tms/static/src/js/tms_portal_link_handler.js',
            'tms/static/src/js/tms_tour.js',
            'tms/static/src/js/tms_help_panel.js',
            'tms/static/src/js/tms_command.js',
            'tms/static/src/js/tms_dimensions_widget.js',
            'tms/static/src/js/tms_dashboard.js',
            'tms/static/src/xml/tms_help_panel.xml',
            'tms/static/src/xml/tms_dashboard.xml',
            'tms/static/src/css/tms_help_panel.css',
        ],
        # Assets para portal: JS y CSS para vista moderna estilo Sales
        'web.assets_frontend': [
            'tms/static/src/js/tms_portal_signature_modal.js',
            'tms/static/src/css/tms_portal_signature_modal.css',
        ],
    },

    # Datos demo
    'demo': [
        'demo/tms_demo_data.xml',
        'demo/tms_quickstart_demo.xml',
        'demo/tms_expanded_demo.xml',
    ],

    # Es una aplicación independiente
    'application': True,

    # Se puede instalar
    'installable': True,

    # No se auto-instala
    'auto_install': False,

    # Licencia
    'license': 'LGPL-3',

    # Hooks post-instalación
    'post_init_hook': 'post_init_hook',
}
