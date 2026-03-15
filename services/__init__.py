# -*- coding: utf-8 -*-
"""
Servicios de timbrado CFDI 4.0 + Carta Porte 3.1 (V2.2)

Arquitectura:
  xml_builder.py    → construye XML CFDI 4.0 + Complemento CP 3.1
  xml_signer.py     → firma el XML con el CSD del emisor
  pac_manager.py    → orquesta el timbrado con failover entre PACs
  formas_digitales.py → wrapper REST para Formas Digitales
  sw_sapien.py       → wrapper REST para SW Sapien (token JWT cacheado)
"""
from . import xml_builder
from . import xml_signer
from . import pac_manager
from . import formas_digitales
from . import sw_sapien
