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
import tempfile
from io import BytesIO

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

_logger = logging.getLogger(__name__)

# URL del XSLT oficial del SAT para cadena original CFDI 4.0
XSLT_CFDI40_URL = (
    'http://www.sat.gob.mx/sitio_internet/cfd/4/cadenaoriginal_TFD_1_1.xslt'
)

# Directorio para caché local del XSLT (evitar descarga en cada timbrado)
XSLT_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'tms_xslt_cache')


class CfdiSigner:
    """
    Firma un XML CFDI 4.0 con el CSD (Certificado de Sello Digital) del SAT.

    Uso:
        signer = CfdiSigner()
        xml_sellado = signer.sign(xml_bytes, company.tms_csd_cer,
                                  company.tms_csd_key, company.tms_csd_password)
    """

    def sign(self, xml_bytes, csd_cer_b64, csd_key_b64, password):
        """
        Firma el XML con el CSD.

        Args:
            xml_bytes   : XML sin sellar como bytes
            csd_cer_b64 : contenido del .cer en base64 (campo Binary de Odoo)
            csd_key_b64 : contenido del .key en base64 (campo Binary de Odoo)
            password    : contraseña del .key como string

        Returns:
            bytes: XML sellado, listo para enviar al PAC
        """
        if not csd_cer_b64 or not csd_key_b64 or not password:
            raise ValueError(
                'Faltan datos del CSD en la empresa: certificado, llave privada '
                'o contraseña. Configúralos en Ajustes → TMS → Certificados SAT.'
            )

        # Decodificar desde base64 de Odoo Binary
        cer_der = base64.b64decode(csd_cer_b64)
        key_der = base64.b64decode(csd_key_b64)

        # Extraer datos del certificado
        no_cert    = self._get_no_certificado(cer_der)
        cert_b64   = self._get_certificado_b64(cer_der)
        private_key = self._load_private_key(key_der, password)

        # Parsear XML y obtener cadena original
        tree = etree.fromstring(xml_bytes)
        cadena = self._generate_cadena_original(tree)

        # Firmar con SHA256withRSA
        sello_bytes = private_key.sign(
            cadena.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        sello_b64 = base64.b64encode(sello_bytes).decode('ascii')

        # Insertar Sello, NoCertificado y Certificado en el nodo raíz
        root = tree
        root.set('Sello',         sello_b64)
        root.set('NoCertificado', no_cert)
        root.set('Certificado',   cert_b64)

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
        Extrae el número de serie del certificado como string de 20 dígitos.
        El serial es un entero hexadecimal en el certificado DER X.509.
        """
        cert = x509.load_der_x509_certificate(cer_bytes, default_backend())
        # El serial SAT es un entero; convertir a hex y tomar solo dígitos
        serial_hex = format(cert.serial_number, 'x').upper()
        # SAT usa la representación decimal del serial en parejas de bytes
        no_cert = ''.join(
            str(int(serial_hex[i:i+2], 16))
            for i in range(0, len(serial_hex), 2)
        )
        # SAT espera exactamente 20 caracteres
        return no_cert[:20].zfill(20)

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
            password  : contraseña como string

        Returns:
            RSAPrivateKey para firmar con SHA256withRSA
        """
        try:
            private_key = serialization.load_der_private_key(
                key_bytes,
                password=password.encode('utf-8'),
                backend=default_backend(),
            )
            return private_key
        except Exception as e:
            raise ValueError(
                f'No se pudo cargar la llave privada CSD. '
                f'Verifica que la contraseña sea correcta. '
                f'Detalle técnico: {type(e).__name__}'
            ) from e

    # ------------------------------------------------------------------
    # Cadena original (XSLT SAT)
    # ------------------------------------------------------------------

    def _generate_cadena_original(self, xml_tree):
        """
        Aplica el XSLT del SAT para obtener la cadena original del CFDI.

        Intenta cargar el XSLT desde caché local. Si no existe,
        lo descarga del SAT con timeout de 10s y lo guarda en caché.

        Args:
            xml_tree: elemento raíz del XML (lxml.etree._Element)

        Returns:
            str: cadena original lista para firmar
        """
        xslt_bytes = self._get_xslt_cached()
        xslt_tree  = etree.fromstring(xslt_bytes)
        transform  = etree.XSLT(xslt_tree)
        resultado  = transform(xml_tree)
        return str(resultado)

    def _get_xslt_cached(self):
        """
        Retorna los bytes del XSLT SAT.
        Usa caché en disco para no descargar en cada timbrado.
        """
        os.makedirs(XSLT_CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(XSLT_CACHE_DIR, 'cadenaoriginal_cfdi40.xslt')

        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return f.read()

        # Descargar con timeout para no colgar el proceso
        _logger.info('Descargando XSLT SAT para cadena original CFDI 4.0...')
        try:
            resp = requests.get(XSLT_CFDI40_URL, timeout=10)
            resp.raise_for_status()
            xslt_bytes = resp.content
        except Exception as e:
            raise RuntimeError(
                f'No se pudo descargar el XSLT del SAT para la cadena original. '
                f'Verifica la conexión a internet. Detalle: {type(e).__name__}'
            ) from e

        with open(cache_path, 'wb') as f:
            f.write(xslt_bytes)

        return xslt_bytes
