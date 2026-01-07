# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from psycopg2 import IntegrityError

import base64
import io
import logging

# Importamos openpyxl para leer archivos Excel modernos (.xlsx)
try:
    import openpyxl
except ImportError:
    openpyxl = None

# Importamos xlrd para leer archivos Excel antiguos (.xls)
try:
    import xlrd
except ImportError:
    xlrd = None

_logger = logging.getLogger(__name__)

# =======================================================
# MAPEO ESTRUCTURAL Y DE LLAVES ÚNICAS (AUDITADO)
# =======================================================
CATALOG_MAP = {
    # --- GEOGRÁFICOS ---

    # 1. Códigos Postales (Archivo c_CP.xls)
    # Estructura verificada: Col 0=CP, 1=Estado, 2=Municipio, 3=Localidad
    'zip': {
        'model': 'tms.sat.codigo.postal',
        'cols': {'code': 0, 'estado': 1, 'municipio': 2, 'localidad': 3},
        'keys': ['code', 'estado', 'municipio']  # Llave compuesta según SQL constraint
    },

    # 2. Localidades (c_Localidad.csv)
    # Estructura: 0=Clave, 1=Estado, 2=Descripción
    'localidad': {
        'model': 'tms.sat.localidad',
        'cols': {'code': 0, 'estado': 1, 'name': 2},
        'keys': ['code', 'estado']  # Único por Clave + Estado
    },

    # 3. Municipios (c_Municipio.csv)
    # Estructura: 0=Clave, 1=Estado, 2=Descripción
    'municipio': {
        'model': 'tms.sat.municipio',
        'cols': {'code': 0, 'estado': 1, 'name': 2},
        'keys': ['code', 'estado']  # Único por Clave + Estado
    },

    # 4. Colonias (c_Colonia_*.csv)
    # Estructura: 0=Clave, 1=CP, 2=Nombre
    'colonia': {
        'model': 'tms.sat.colonia',
        'cols': {'code': 0, 'zip_code': 1, 'name': 2},
        'keys': ['code', 'zip_code']  # Único por Clave + CP
    },

    # --- OTROS ---
    'prod': {
        'model': 'tms.sat.clave.prod',
        'cols': {'code': 0, 'name': 1, 'material_peligroso': 3},  # Col D
        'keys': ['code']
    },
    'uom': {
        'model': 'tms.sat.clave.unidad',
        'cols': {'code': 0, 'name': 1},
        'keys': ['code']
    },
    'config_auto': {
        'model': 'tms.sat.config.autotransporte',
        'cols': {
            'code': 0,
            'name': 1,
            'total_axles': 2,
            'total_tires': 3,
            'remolque': 4,
            'vigencia_inicio': 5,
            'vigencia_fin': 6
        },
        'keys': ['code']
    },
    'permiso': {
        'model': 'tms.sat.tipo.permiso',
        'cols': {'code': 0, 'name': 1, 'clave_transporte': 2},
        'keys': ['code']
    },
    'packaging': {
        'model': 'tms.sat.embalaje',
        'cols': {'code': 0, 'name': 1},
        'keys': ['code']
    },
    'material': {
        'model': 'tms.sat.material.peligroso',
        'cols': {'code': 0, 'name': 1, 'clase': 2},
        'keys': ['code']
    },
    'figura': {
        'model': 'tms.sat.figura.transporte',
        'cols': {'code': 0, 'name': 1},
        'keys': ['code']
    },
}


class SatImportWizard(models.TransientModel):
    """
    Importador de Catálogos SAT con soporte para archivos c_CP.xls y llaves compuestas.

    CARACTERÍSTICAS:
    - Soporte para archivos Excel (.xlsx y .xls)
    - Manejo de llaves compuestas para catálogos geográficos
    - Auto-creación de Códigos Postales al importar Colonias
    - Normalización agresiva de datos para evitar duplicados
    """

    _name = 'sat.import.wizard'
    _description = 'Importador de Catálogos SAT'

    catalog_type = fields.Selection([
        ('prod', 'Productos y Servicios'),
        ('uom', 'Unidades de Medida'),
        ('zip', 'Códigos Postales (c_CP.xls)'),
        ('colonia', 'Colonias'),
        ('localidad', 'Localidades'),
        ('municipio', 'Municipios'),
        ('config_auto', 'Config. Autotransporte'),
        ('permiso', 'Tipos Permiso SCT'),
        ('packaging', 'Tipos Embalaje'),
        ('material', 'Materiales Peligrosos'),
        ('figura', 'Figuras Transporte'),
    ], string='Tipo de Catálogo', required=True, default='prod')

    excel_file = fields.Binary(string='Archivo Excel', required=True)
    file_name = fields.Char(string='Nombre Archivo')
    sheet_index = fields.Integer(
        string='Número de Hoja (base 0)',
        default=0,
        help="0 para la primera hoja, 1 para la segunda..."
    )
    data_start_row = fields.Integer(
        string='Fila de Datos (Inicio)',
        default=2,
        help="Fila donde comienzan los datos reales (ej. 2 para saltar cabecera)"
    )

    def _clean_str(self, val):
        """
        Normalización agresiva: String, sin espacios, sin .0

        CRÍTICO: Este método garantiza que 'AGU' == 'AGU ' == 'AGU.0'
        y que '01' == '1' (ambos se convierten a string limpio).

        :param val: valor crudo (int, float, str, None)
        :return: string limpio sin decimales .0 ni espacios
        """
        if not val:
            return ''

        s = str(val).strip()

        # Eliminar .0 al final (problema de Excel con formato numérico)
        if s.endswith('.0'):
            s = s[:-2]

        return s

    def _clean_hazardous(self, val):
        """
        Normaliza el campo Material Peligroso.

        :param val: valor crudo del Excel
        :return: string válido ('0', '1' o '0,1')
        """
        s = self._clean_str(val)

        if s in ['0', '1', '0,1']:
            return s

        if s.lower() in ['si', 'sí', 'yes']:
            return '1'

        return '0'

    def action_import(self):
        """
        Procesa el archivo Excel con normalización de llaves para evitar duplicados.

        Lógica:
        1. Lee archivo (XLSX o XLS)
        2. Normaliza todos los campos con _clean_str
        3. Auto-crea Códigos Postales si se importan Colonias
        4. Construye llaves compuestas normalizadas
        5. Compara con existentes también normalizados
        6. Crea solo registros nuevos
        """
        self.ensure_one()

        if not self.excel_file:
            raise UserError(_('Debe subir un archivo Excel antes de importar.'))

        # 1. Leer Archivo (Híbrido)
        decoded = base64.b64decode(self.excel_file)
        rows = []

        try:
            # Intento 1: Excel Moderno (.xlsx)
            if openpyxl:
                wb = openpyxl.load_workbook(io.BytesIO(decoded), data_only=True, read_only=True)
                sheet = wb.worksheets[self.sheet_index]
                for row in sheet.iter_rows(min_row=self.data_start_row, values_only=True):
                    rows.append(row)
            else:
                raise ImportError('openpyxl no disponible')
        except Exception:
            # Intento 2: Excel Antiguo (.xls)
            try:
                if xlrd:
                    wb = xlrd.open_workbook(file_contents=decoded)
                    sheet = wb.sheet_by_index(self.sheet_index)
                    for row_idx in range(self.data_start_row - 1, sheet.nrows):
                        rows.append(sheet.row_values(row_idx))
                else:
                    raise ImportError('xlrd no disponible')
            except Exception as e:
                raise UserError(_("No se pudo leer el archivo. Asegúrese de que es un Excel válido (.xls o .xlsx). Error: %s") % e)

        if not rows:
            raise UserError(_("No se encontraron datos en la hoja seleccionada."))

        # 2. Configuración
        cfg = CATALOG_MAP.get(self.catalog_type)
        if not cfg:
            raise UserError(_("Configuración no encontrada para este catálogo."))

        model = self.env[cfg['model']]
        cols_map = cfg['cols']
        keys_def = cfg['keys']
        primary_key = keys_def[0]  # Ej. 'code'

        vals_list = []

        # 3. Procesamiento
        for i, row in enumerate(rows):
            vals = {}
            try:
                # Extraer y limpiar datos
                for field, col_idx in cols_map.items():
                    if col_idx < len(row):
                        raw = row[col_idx]

                        if field == 'material_peligroso':
                            vals[field] = self._clean_hazardous(raw)
                        elif field in ['numero_ejes_remolque', 'total_axles']:
                            # Campo numérico
                            try:
                                vals[field] = int(float(str(raw).replace(',', ''))) if raw else 0
                            except (ValueError, TypeError):
                                vals[field] = 0
                        elif field in ['vigencia_inicio', 'vigencia_fin']:
                            # Parsing de fecha (DD/MM/YYYY)
                            s = self._clean_str(raw)
                            if s:
                                try:
                                    # Convertir DD/MM/YYYY a YYYY-MM-DD (Formato Odoo)
                                    from datetime import datetime
                                    dt = datetime.strptime(s, '%d/%m/%Y')
                                    vals[field] = dt.strftime('%Y-%m-%d')
                                except ValueError:
                                    vals[field] = False
                            else:
                                vals[field] = False
                        else:
                            # APLICAR LIMPIEZA A TODOS LOS CAMPOS
                            vals[field] = self._clean_str(raw)
                    else:
                        # Campo opcional, usar valor por defecto
                        if field == 'material_peligroso':
                            vals[field] = '0'
                        elif field in ['numero_ejes_remolque', 'total_axles']:
                            vals[field] = 0
                        else:
                            vals[field] = False

                # Validar que la llave primaria tenga dato
                if not vals.get(primary_key):
                    continue

                vals_list.append(vals)

            except Exception as e:
                _logger.warning(f"Error en fila {i + self.data_start_row}: {e}")
                continue

        if not vals_list:
            raise UserError(_('No se encontraron registros válidos para importar.'))

        # ELIMINAR DUPLICADOS DENTRO DEL MISMO LOTE
        unique_vals_list = []
        seen_keys = set()

        for val in vals_list:
            # Crear una firma única para este registro basada en las llaves
            # Ej: ('20126', 'AGU', '001')
            key_signature = tuple(val.get(k) for k in keys_def)

            if key_signature in seen_keys:
                continue # Ya está en este lote, saltar

            seen_keys.add(key_signature)
            unique_vals_list.append(val)

        vals_list = unique_vals_list # Reemplazar con la lista limpia

        # 3.5. Auto-creación de Códigos Postales (Solo para Colonias)
        # CRÍTICO: Si importamos colonias y el CP no existe, lo creamos automáticamente
        if self.catalog_type == 'colonia':
            # Extraer todos los zip_code únicos del archivo Excel
            zip_codes_from_file = set()
            for vals in vals_list:
                zip_code = vals.get('zip_code')
                if zip_code:  # Solo agregar si tiene valor
                    zip_codes_from_file.add(zip_code)

            if zip_codes_from_file:
                # Buscar cuáles CPs ya existen en la BD
                # Usamos la llave compuesta (code, estado, municipio) para buscar
                zip_model = self.env['tms.sat.codigo.postal']
                existing_zips = zip_model.search([('code', 'in', list(zip_codes_from_file))])
                existing_zip_codes = set(existing_zips.mapped('code'))

                # Encontrar CPs faltantes
                missing_zips = zip_codes_from_file - existing_zip_codes

                # Crear CPs faltantes en masa (solo con código, sin datos geográficos detallados)
                if missing_zips:
                    zip_records_to_create = []
                    for zip_code in missing_zips:
                        zip_records_to_create.append({
                            'code': zip_code,
                            'estado': '',  # Vacío por ahora
                            'municipio': '',  # Vacío por ahora
                            'localidad': '',  # Vacío por ahora
                        })

                    try:
                        zip_model.create(zip_records_to_create)
                        _logger.info(f"Auto-creados {len(zip_records_to_create)} códigos postales faltantes.")
                    except Exception as e:
                        _logger.warning(f"Error al auto-crear códigos postales: {e}")
                        # No fallar la importación completa si hay error en auto-creación

        # 4. Upsert (Evitar Duplicados)
        # Paso A: Obtener todas las claves primarias del archivo para buscar en BD
        batch_codes = set(v[primary_key] for v in vals_list if v.get(primary_key))

        if not batch_codes:
            raise UserError(_('No se encontraron valores válidos para la llave primaria.'))

        # Paso B: Buscar candidatos en BD
        candidates = model.search([(primary_key, 'in', list(batch_codes))])

        # Paso C: Indexar existentes por LLAVE COMPUESTA NORMALIZADA
        # CRÍTICO: Normalizar también los datos de BD antes de indexar
        # Esto evita duplicados como '01-AGU' vs '01-BCN' o 'AGU ' vs 'AGU'
        existing_map = {}
        for rec in candidates:
            # Construir tupla única normalizada: ej ('01', 'AGU')
            # Importante: Asegurar que los datos de BD también se traten como string limpio
            key_tuple = tuple(self._clean_str(rec[k]) for k in keys_def)
            existing_map[key_tuple] = rec

        to_create = []
        updated_count = 0

        for vals in vals_list:
            # Construir la misma tupla normalizada con los datos del Excel
            # CRÍTICO: Los valores ya están normalizados por _clean_str en el paso 3
            row_key_tuple = tuple(vals[k] for k in keys_def)

            if row_key_tuple in existing_map:
                # YA EXISTE LA COMBINACIÓN EXACTA (Ej: 01 + AGU)
                # Opcional: Actualizar nombre si cambió
                # rec = existing_map[row_key_tuple]
                # rec.write({'name': vals['name']})
                updated_count += 1
            else:
                # NO EXISTE (Es nuevo o es otro estado con la misma clave)
                to_create.append(vals)

        # 5. Crear Nuevos
        records_created = 0
        if to_create:
            try:
                # Intento masivo (Rápido)
                model.create(to_create)
                records_created = len(to_create)
            except IntegrityError:
                # Fallback: Si hay error de integridad, insertar uno por uno
                self.env.cr.rollback() # Importante: Rollback de la transacción fallida
                for val in to_create:
                    try:
                        with self.env.cr.savepoint(): # Savepoint para aislar cada error
                            model.create(val)
                            records_created += 1
                    except IntegrityError:
                        pass # Ignorar duplicados que la BD rechace
            except Exception as e:
                raise UserError(f"Error al crear registros: {e}")

        # Preparar mensaje de resultado
        message = _(
            'Procesados: %s. Nuevos: %s. Existentes/Ignorados: %s.'
        ) % (len(vals_list), records_created, updated_count)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Importación Completada'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_clear_catalog(self):
        """Elimina todos los registros del catálogo seleccionado."""
        self.ensure_one()

        if self.catalog_type not in CATALOG_MAP:
            raise UserError(_('Tipo de catálogo no reconocido.'))

        model_name = CATALOG_MAP[self.catalog_type]['model']
        model = self.env[model_name]

        # Contar registros antes de eliminar
        count = model.search_count([])

        # Eliminar todos
        model.search([]).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Catálogo Limpiado'),
                'message': _('Se eliminaron %s registros del catálogo.') % count,
                'type': 'success',
                'sticky': False,
            }
        }
