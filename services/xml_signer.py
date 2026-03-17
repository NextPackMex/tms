# -*- coding: utf-8 -*-
"""
Firmado del XML CFDI con el Certificado de Sello Digital (CSD) del emisor.

Proceso de firmado:
  1. Decodificar .cer (base64 → DER) → obtener NoCertificado + certificado b64
  2. Decodificar .key (base64 → DER) → desencriptar con contraseña
  3. Aplicar XSLT SAT para obtener la cadena original del XML
  4. Firmar cadena original con SHA256withRSA usando la llave privada
  5. Codificar sello en base64
  6. Insertar Sello, Certificado y NoCertificado en el nodo Comprobante
  7. Retornar XML sellado como bytes

El .key del SAT está en formato PKCS#8 encriptado con 3DES.
El .cer del SAT está en formato DER (binario).
"""
import base64
import logging
import os

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

_logger = logging.getLogger(__name__)

# Ruta local del XSLT del SAT (incluido en el módulo para no depender de internet)
# Fuente: phpcfdi/resources-sat-xml (espejo oficial de los archivos del SAT)
_MODULE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XSLT_LOCAL_PATH = os.path.join(
    _MODULE_PATH, 'static', 'xslt',
    '4', 'cadenaoriginal_4_0', 'cadenaoriginal_4_0.xslt'
)


class CfdiSigner:
    """
    Firma un XML CFDI 4.0 con el CSD (Certificado de Sello Digital) del SAT.

    Uso:
        signer = CfdiSigner()
        csd_cer_bytes = base64.b64decode(company.tms_csd_cer)
        csd_key_bytes = base64.b64decode(company.tms_csd_key)
        xml_sellado = signer.sign(xml_bytes, csd_cer_bytes,
                                  csd_key_bytes, company.tms_csd_password)
    """

    def sign(self, xml_bytes, csd_cer_bytes, csd_key_bytes, password):
        """
        Firma el XML con el CSD.

        Args:
            xml_bytes     : XML sin sellar como bytes
            csd_cer_bytes : bytes DER del .cer (ya decodificados de base64 por el caller)
            csd_key_bytes : bytes DER del .key (ya decodificados de base64 por el caller)
            password      : contraseña del .key como str o bytes

        Returns:
            bytes: XML sellado, listo para enviar al PAC

        Nota: la decodificación base64 de los campos Binary de Odoo
        es responsabilidad del caller (action_stamp_cfdi en tms_waybill.py).
        """
        if not csd_cer_bytes or not csd_key_bytes or not password:
            raise ValueError(
                'Faltan datos del CSD en la empresa: certificado, llave privada '
                'o contraseña. Configúralos en Ajustes → TMS → Certificados SAT.'
            )

        # Bytes DER recibidos ya decodificados — usar directamente
        cer_der = csd_cer_bytes
        key_der = csd_key_bytes

        # Extraer datos del certificado
        no_cert    = self._get_no_certificado(cer_der)
        cert_b64   = self._get_certificado_b64(cer_der)
        private_key = self._load_private_key(key_der, password)

        # Parsear XML e insertar NoCertificado y Certificado ANTES de calcular
        # la cadena original — el XSLT del SAT incluye NoCertificado (Requerido)
        # en la cadena, por lo que debe estar presente cuando se aplica el XSLT.
        # El Sello NO forma parte de la cadena original, se inserta después.
        root = etree.fromstring(xml_bytes)
        root.set('NoCertificado', no_cert)
        root.set('Certificado',   cert_b64)

        cadena = self._generate_cadena_original(root)

        # Firmar con SHA256withRSA la cadena original ya con NoCertificado
        sello_bytes = private_key.sign(
            cadena.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        sello_b64 = base64.b64encode(sello_bytes).decode('ascii')

        # Insertar Sello al final (no forma parte de la cadena original)
        root.set('Sello', sello_b64)

        xml_sellado = etree.tostring(
            root,
            xml_declaration=True,
            encoding='UTF-8',
            pretty_print=False,
        )
        _logger.info(
            'XML firmado OK — NoCertificado: %s (primeros 4 chars: %s...)',
            no_cert, sello_b64[:4]
        )
        return xml_sellado

    # ------------------------------------------------------------------
    # Helpers de certificado
    # ------------------------------------------------------------------

    def _get_no_certificado(self, cer_bytes):
        """
        Extrae el número de serie del certificado en formato SAT (NoCertificado).

        Los CSD del SAT codifican su serial X.509 como texto ASCII dentro del
        campo INTEGER del certificado. Cada par de bytes hex representa el
        código ASCII de un dígito del número de serie.

        Ejemplo: hex '33303030...' → chr(0x33)+chr(0x30)+... → '30001000...'

        El NoCertificado resultante es exactamente lo que aparece en la sección
        'Número de Serie' del visor de certificados del SAT.
        """
        cert = x509.load_der_x509_certificate(cer_bytes, default_backend())
        serial_hex = format(cert.serial_number, 'x').upper()
        # Asegurar longitud par para leer parejas completas
        if len(serial_hex) % 2 != 0:
            serial_hex = '0' + serial_hex
        # Cada par hex es el código ASCII de un carácter del número de serie SAT
        no_cert = ''.join(
            chr(int(serial_hex[i:i+2], 16))
            for i in range(0, len(serial_hex), 2)
        )
        return no_cert

    def _get_certificado_b64(self, cer_bytes):
        """
        Retorna el certificado DER en base64 sin saltos de línea,
        tal como lo requiere el atributo Certificado del CFDI.
        """
        return base64.b64encode(cer_bytes).decode('ascii')

    # ------------------------------------------------------------------
    # Carga de llave privada
    # ------------------------------------------------------------------

    def _load_private_key(self, key_bytes, password):
        """
        Carga y desencripta la llave privada .key del SAT.

        El .key del SAT usa formato PKCS#8 encriptado con 3DES.
        La librería `cryptography` detecta automáticamente el formato
        al usar load_der_private_key().

        Args:
            key_bytes : bytes del archivo .key (ya decodificado desde b64)
            password  : contraseña como str o bytes

        Returns:
            RSAPrivateKey para firmar con SHA256withRSA
        """
        # Convertir contraseña a bytes — load_der_private_key exige bytes, no str.
        # fields.Char de Odoo devuelve str; fields.Binary puede devolver bytes.
        if isinstance(password, str):
            password_bytes = password.encode('utf-8')
        elif isinstance(password, bytes):
            password_bytes = password
        else:
            password_bytes = None  # llave sin contraseña

        try:
            private_key = serialization.load_der_private_key(
                key_bytes,
                password=password_bytes,
                backend=default_backend(),
            )
            return private_key
        except Exception as e:
            raise ValueError(
                f'No se pudo cargar la llave privada CSD. '
                f'Verifica que la contraseña sea correcta y que el archivo '
                f'.key sea el correspondiente al .cer. '
                f'Detalle técnico: {type(e).__name__}: {e}'
            ) from e

    # ------------------------------------------------------------------
    # Cadena original (XSLT SAT)
    # ------------------------------------------------------------------

    def _generate_cadena_original(self, xml_tree):
        """
        Aplica el XSLT del SAT para obtener la cadena original del CFDI 4.0.

        Usa la copia local del XSLT incluida en el módulo (static/xslt/).
        No requiere conexión a internet — el SAT bloquea descargas directas.

        Args:
            xml_tree: elemento raíz del XML (lxml.etree._Element)

        Returns:
            str: cadena original con formato ||campo1|campo2|...|
        """
        if not os.path.exists(XSLT_LOCAL_PATH):
            raise RuntimeError(
                f'No se encontró el XSLT del SAT en: {XSLT_LOCAL_PATH}\n'
                f'El módulo TMS debe incluir los archivos en static/xslt/. '
                f'Contacta al administrador del sistema.'
            )

        xslt_doc  = etree.parse(XSLT_LOCAL_PATH)
        transform = etree.XSLT(xslt_doc)
        resultado = transform(xml_tree)
        return str(resultado)
