# -*- coding: utf-8 -*-
"""
Construcción del XML CFDI 4.0 con Complemento Carta Porte 3.1.

Usa lxml para construir el árbol XML con los namespaces correctos del SAT.
NO depende de l10n_mx_edi — implementación propia completa.

Namespaces:
  cfdi:         http://www.sat.gob.mx/cfd/4
  cartaporte31: http://www.sat.gob.mx/CartaPorte31
  xsi:          http://www.w3.org/2001/XMLSchema-instance
"""
import logging
from datetime import datetime

from lxml import etree

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de namespace y esquema
# ---------------------------------------------------------------------------
NS_CFDI = 'http://www.sat.gob.mx/cfd/4'
NS_CP31 = 'http://www.sat.gob.mx/CartaPorte31'
NS_XSI  = 'http://www.w3.org/2001/XMLSchema-instance'

SCHEMA_LOCATION = (
    'http://www.sat.gob.mx/cfd/4 '
    'http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd '
    'http://www.sat.gob.mx/CartaPorte31 '
    'http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd'
)

NSMAP = {
    'cfdi':         NS_CFDI,
    'cartaporte31': NS_CP31,
    'xsi':          NS_XSI,
}


class CartaPorteXmlBuilder:
    """
    Construye el XML CFDI 4.0 con Complemento Carta Porte 3.1
    a partir de un registro tms.waybill.

    Uso:
        builder = CartaPorteXmlBuilder()
        xml_bytes = builder.build(waybill)
        # Pasar xml_bytes a CfdiSigner.sign()
    """

    def build(self, waybill):
        """
        Construye el XML sin sellar.

        Args:
            waybill: registro tms.waybill con todos los datos

        Returns:
            bytes: XML serializado, listo para firmar con CfdiSigner
        """
        _logger.info('Construyendo XML CFDI 4.0 para waybill %s', waybill.name)

        # Nodo raíz con namespaces
        comprobante = self._build_comprobante(waybill)

        # Subnodos obligatorios CFDI 4.0
        comprobante.append(self._build_emisor(waybill.company_id))
        comprobante.append(self._build_receptor(waybill))
        comprobante.append(self._build_conceptos(waybill))
        comprobante.append(self._build_impuestos(waybill))

        # Complemento Carta Porte 3.1
        complemento = etree.SubElement(
            comprobante, etree.QName(NS_CFDI, 'Complemento'))
        complemento.append(self._build_complemento_carta_porte(waybill))

        xml_bytes = etree.tostring(
            comprobante,
            xml_declaration=True,
            encoding='UTF-8',
            pretty_print=False,
        )
        return xml_bytes

    # ------------------------------------------------------------------
    # Nodo raíz: cfdi:Comprobante
    # ------------------------------------------------------------------

    def _build_comprobante(self, waybill):
        """
        Construye el nodo raíz cfdi:Comprobante con atributos CFDI 4.0.
        TipoDeComprobante='T' (Traslado) porque Carta Porte no es ingreso.
        """
        company = waybill.company_id
        fecha = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        comp = etree.Element(
            etree.QName(NS_CFDI, 'Comprobante'),
            nsmap=NSMAP,
        )

        comp.set(etree.QName(NS_XSI, 'schemaLocation'), SCHEMA_LOCATION)
        comp.set('Version',             '4.0')
        comp.set('Fecha',               fecha)
        comp.set('Sello',               '')          # se rellena al firmar
        comp.set('NoCertificado',       '')          # se rellena al firmar
        comp.set('Certificado',         '')          # se rellena al firmar
        comp.set('SubTotal',            '0')
        comp.set('Total',               '0')
        comp.set('Moneda',              'XXX')       # XXX = no aplica (traslado)
        comp.set('TipoDeComprobante',   'T')         # T = Traslado
        comp.set('Exportacion',         '01')        # 01 = No aplica
        comp.set('LugarExpedicion',     company.zip or '00000')

        return comp

    # ------------------------------------------------------------------
    # cfdi:Emisor
    # ------------------------------------------------------------------

    def _build_emisor(self, company):
        """
        Construye cfdi:Emisor con RFC, Nombre y RegimenFiscal de la empresa.
        RFC se toma de company.vat (campo estándar Odoo).
        """
        emisor = etree.Element(etree.QName(NS_CFDI, 'Emisor'))
        emisor.set('Rfc',            (company.vat or '').upper().strip())
        emisor.set('Nombre',         (company.name or '').upper()[:254])
        # tms_regimen_fiscal tiene solo el código (ej. '612')
        emisor.set('RegimenFiscal',  company.tms_regimen_fiscal or '612')
        return emisor

    # ------------------------------------------------------------------
    # cfdi:Receptor
    # ------------------------------------------------------------------

    def _build_receptor(self, waybill):
        """
        Construye cfdi:Receptor con los datos del cliente factura.
        UsoCFDI siempre CP01 para Carta Porte.
        DomicilioFiscalReceptor: CP del cliente (tms.sat.codigo.postal).
        """
        partner = waybill.partner_invoice_id
        receptor = etree.Element(etree.QName(NS_CFDI, 'Receptor'))
        receptor.set('Rfc',                      (partner.vat or 'XAXX010101000').upper().strip())
        receptor.set('Nombre',                   (partner.name or '').upper()[:254])
        receptor.set('DomicilioFiscalReceptor',  partner.zip or '00000')
        receptor.set('RegimenFiscalReceptor',    partner.l10n_mx_edi_fiscal_regime or '616')
        receptor.set('UsoCFDI',                  'CP01')
        return receptor

    # ------------------------------------------------------------------
    # cfdi:Conceptos — servicio de autotransporte de carga
    # ------------------------------------------------------------------

    def _build_conceptos(self, waybill):
        """
        Construye cfdi:Conceptos.
        Para Carta Porte (TipoDeComprobante=T) se usa un concepto único
        que representa el servicio de autotransporte de carga.
        ClaveProdServ: 78101800 (Servicios de transporte de carga por carretera)
        ClaveUnidad:   E48 (Unidad de servicio)
        Importe: 0 porque en Traslado el valor fiscal es 0.
        """
        conceptos = etree.Element(etree.QName(NS_CFDI, 'Conceptos'))
        concepto  = etree.SubElement(conceptos, etree.QName(NS_CFDI, 'Concepto'))

        concepto.set('ClaveProdServ',  '78101800')
        concepto.set('Cantidad',       '1')
        concepto.set('ClaveUnidad',    'E48')
        concepto.set('Descripcion',    'SERVICIO DE AUTOTRANSPORTE DE CARGA')
        concepto.set('ValorUnitario',  '0')
        concepto.set('Importe',        '0')
        concepto.set('ObjetoImp',      '01')  # 01 = No objeto de impuesto (traslado)

        return conceptos

    # ------------------------------------------------------------------
    # cfdi:Impuestos — para Traslado son vacíos pero el nodo es requerido
    # ------------------------------------------------------------------

    def _build_impuestos(self, waybill):
        """
        Para TipoDeComprobante='T' (Traslado), Impuestos va vacío.
        El nodo es requerido por el esquema XSD pero sin subnodos.
        """
        impuestos = etree.Element(etree.QName(NS_CFDI, 'Impuestos'))
        impuestos.set('TotalImpuestosTrasladados', '0')
        return impuestos

    # ------------------------------------------------------------------
    # Complemento Carta Porte 3.1
    # ------------------------------------------------------------------

    def _build_complemento_carta_porte(self, waybill):
        """
        Construye el nodo cartaporte31:CartaPorte Version='3.1'.
        Incluye: Ubicaciones, Mercancias, Autotransporte, FiguraTransporte.
        """
        cp = etree.Element(etree.QName(NS_CP31, 'CartaPorte'))
        cp.set('Version',              '3.1')
        cp.set('TranspInternac',       'No')
        cp.set('TotalDistRec',         str(int(waybill.distance_loaded_km or 0)))

        cp.append(self._build_ubicaciones(waybill))
        cp.append(self._build_mercancias(waybill))
        cp.append(self._build_autotransporte(waybill))
        cp.append(self._build_figura_transporte(waybill))

        return cp

    # ------------------------------------------------------------------
    # Ubicaciones
    # ------------------------------------------------------------------

    def _build_ubicaciones(self, waybill):
        """
        Construye Ubicaciones con Origen y Destino.
        IDUbicacion: OR000001 (origen) / DE000001 (destino).
        Domicilio requiere: CodigoPostal + Estado + Pais='MEX'.
        """
        ubicaciones = etree.Element(etree.QName(NS_CP31, 'Ubicaciones'))

        # Origen
        origen = etree.SubElement(ubicaciones, etree.QName(NS_CP31, 'Ubicacion'))
        origen.set('TipoUbicacion',    'Origen')
        origen.set('IDUbicacion',      'OR000001')
        origen.set('RFCRemitenteDestinatario',
                   (waybill.partner_origin_id.vat or 'XAXX010101000').upper())
        origen.set('NombreRemitenteDestinatario',
                   (waybill.partner_origin_id.name or '').upper()[:254])
        origen.set('FechaHoraSalidaLlegada',
                   datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

        dom_origen = etree.SubElement(origen, etree.QName(NS_CP31, 'Domicilio'))
        dom_origen.set('CodigoPostal', waybill.origin_zip.cp if waybill.origin_zip else '00000')
        dom_origen.set('Estado',       (waybill.origin_zip.estado or 'CDMX') if waybill.origin_zip else 'CDMX')
        dom_origen.set('Pais',         'MEX')

        # Destino
        destino = etree.SubElement(ubicaciones, etree.QName(NS_CP31, 'Ubicacion'))
        destino.set('TipoUbicacion',   'Destino')
        destino.set('IDUbicacion',     'DE000001')
        destino.set('RFCRemitenteDestinatario',
                    (waybill.partner_dest_id.vat or 'XAXX010101000').upper())
        destino.set('NombreRemitenteDestinatario',
                    (waybill.partner_dest_id.name or '').upper()[:254])
        destino.set('DistanciaRecorrida', str(int(waybill.distance_loaded_km or 0)))
        destino.set('FechaHoraSalidaLlegada',
                    datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

        dom_destino = etree.SubElement(destino, etree.QName(NS_CP31, 'Domicilio'))
        dom_destino.set('CodigoPostal', waybill.dest_zip.cp if waybill.dest_zip else '00000')
        dom_destino.set('Estado',       (waybill.dest_zip.estado or 'JAL') if waybill.dest_zip else 'JAL')
        dom_destino.set('Pais',         'MEX')

        return ubicaciones

    # ------------------------------------------------------------------
    # Mercancias
    # ------------------------------------------------------------------

    def _build_mercancias(self, waybill):
        """
        Construye el nodo Mercancias con una Mercancia por cada línea del waybill.
        Campos requeridos por CP 3.1: BienesTransp, Descripcion, Cantidad,
        ClaveUnidad, PesoEnKg, Dimensiones.
        """
        peso_total = sum(
            (line.weight_kg or 0) * (line.quantity or 1)
            for line in waybill.line_ids
        )
        mercancias = etree.Element(etree.QName(NS_CP31, 'Mercancias'))
        mercancias.set('PesoBrutoTotal',  '{:.3f}'.format(peso_total or 0))
        mercancias.set('UnidadPeso',      'KGM')
        mercancias.set('NumTotalMercancias', str(len(waybill.line_ids) or 1))

        for line in waybill.line_ids:
            merc = etree.SubElement(mercancias, etree.QName(NS_CP31, 'Mercancia'))
            merc.set('BienesTransp',
                     line.product_sat_id.code if line.product_sat_id else '47131500')
            merc.set('Descripcion',   (line.description or 'MERCANCIA GENERAL')[:100])
            merc.set('Cantidad',      '{:.3f}'.format(line.quantity or 1))
            merc.set('ClaveUnidad',
                     line.uom_sat_id.code if line.uom_sat_id else 'KGM')
            merc.set('PesoEnKg',      '{:.3f}'.format((line.weight_kg or 0) * (line.quantity or 1)))
            merc.set('Dimensiones',   line.dimensions or '000/000/000cm')

            if line.is_dangerous:
                merc.set('MaterialPeligroso', 'Sí')

        return mercancias

    # ------------------------------------------------------------------
    # Autotransporte
    # ------------------------------------------------------------------

    def _build_autotransporte(self, waybill):
        """
        Construye cartaporte31:Autotransporte con vehículo, seguros y remolques.
        PermSCT: tipo de permiso SCT del vehículo.
        NumPermisoSCT: número de permiso SCT.
        Seguros: RC obligatorio, Carga si hay mercancías, Ambiental si peligroso.
        """
        vehicle = waybill.vehicle_id
        company = waybill.company_id

        auto = etree.Element(etree.QName(NS_CP31, 'Autotransporte'))
        auto.set('PermSCT',
                 vehicle.tms_tipo_permiso_id.code if (vehicle and vehicle.tms_tipo_permiso_id) else 'TPAF10')
        auto.set('NumPermisoSCT',
                 vehicle.tms_num_permiso_sct or '000000')

        # IdentificacionVehicular
        id_veh = etree.SubElement(auto, etree.QName(NS_CP31, 'IdentificacionVehicular'))
        id_veh.set('ConfigVehicular',
                   vehicle.tms_config_autotransporte_id.code if (vehicle and vehicle.tms_config_autotransporte_id) else 'C2')
        id_veh.set('PlacaVM',    (vehicle.license_plate or 'XXX000').upper() if vehicle else 'XXX000')
        id_veh.set('AnioModeloVM', str(vehicle.model_year or '2020') if vehicle else '2020')

        # Seguros
        seguros = etree.SubElement(auto, etree.QName(NS_CP31, 'Seguros'))
        seguros.set('AseguraRespCivil',  company.tms_insurance_rc_company or 'NO INFORMADO')
        seguros.set('PolizaRespCivil',   company.tms_insurance_rc_policy  or '0000000')
        if company.tms_insurance_cargo_policy:
            seguros.set('AseguraMedAmbiente', company.tms_insurance_cargo_company or '')
            seguros.set('PolizaMedAmbiente',  company.tms_insurance_cargo_policy  or '')

        # Remolques (si aplica)
        if waybill.trailer1_id:
            remolques_node = etree.SubElement(auto, etree.QName(NS_CP31, 'Remolques'))
            rem1 = etree.SubElement(remolques_node, etree.QName(NS_CP31, 'Remolque'))
            rem1.set('SubTipoRem', waybill.trailer1_id.tms_subtipo_remolque or 'CTR007')
            rem1.set('Placa',     (waybill.trailer1_id.license_plate or 'REM000').upper())

            if waybill.trailer2_id:
                rem2 = etree.SubElement(remolques_node, etree.QName(NS_CP31, 'Remolque'))
                rem2.set('SubTipoRem', waybill.trailer2_id.tms_subtipo_remolque or 'CTR007')
                rem2.set('Placa',     (waybill.trailer2_id.license_plate or 'REM001').upper())

        return auto

    # ------------------------------------------------------------------
    # FiguraTransporte
    # ------------------------------------------------------------------

    def _build_figura_transporte(self, waybill):
        """
        Construye cartaporte31:FiguraTransporte con el operador (chofer).
        TipoFigura='01' (Operador).
        RFC, Nombre y NumLicencia son obligatorios.
        """
        driver = waybill.driver_id
        figura_root = etree.Element(etree.QName(NS_CP31, 'FiguraTransporte'))

        if driver:
            figura = etree.SubElement(figura_root, etree.QName(NS_CP31, 'TiposFigura'))
            figura.set('TipoFigura', '01')
            figura.set('RFCFigura',   (driver.rfc or 'XEXX010101000').upper().strip())
            figura.set('NombreFigura', (driver.name or '').upper()[:254])
            figura.set('NumLicencia',  driver.tms_licencia_federal or '000000000000')
        else:
            # Figura vacía de relleno para cumplir XSD
            figura = etree.SubElement(figura_root, etree.QName(NS_CP31, 'TiposFigura'))
            figura.set('TipoFigura', '01')
            figura.set('RFCFigura',   'XEXX010101000')
            figura.set('NombreFigura', 'OPERADOR NO ASIGNADO')
            figura.set('NumLicencia',  '000000000000')

        return figura_root
