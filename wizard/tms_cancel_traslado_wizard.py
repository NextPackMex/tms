# -*- coding: utf-8 -*-
"""
Wizard de Cancelación de CFDI Traslado TMS.

Permite cancelar ante el SAT el CFDI Carta Porte (Traslado) timbrado de un viaje,
seleccionando el motivo correcto según la situación:

  Motivo 01 — Errores con relación:
    Error en RFC, monto u otro dato. Se corrige timbrado un Traslado sustituto primero.
    El waybill permanece en el mismo estado — el sustituto cubre la operación.

  Motivo 02 — Errores sin relación:
    Error sin factura sustituta (ej: datos del vehículo incorrectos, waybill duplicado).
    El waybill regresa a 'aprobado' para corregir y re-timbrar.

  Motivo 03 — Operación no realizada:
    El viaje fue cancelado o no se ejecutó.
    El waybill regresa a 'aprobado' para decidir qué hacer.

IMPORTANTE: Motivo 01 requiere que exista un Traslado sustituto ya timbrado antes
de proceder con la cancelación. El wizard bloquea si no se proporciona el UUID sustituto.
"""
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TmsCancelTrasladoWizard(models.TransientModel):
    """
    Wizard de cancelación de CFDI Traslado con selección de motivo SAT.
    Llama a PacManager.cancelar() tras validar y actualiza el waybill según el motivo.
    """
    _name        = 'tms.cancel.traslado.wizard'
    _description = 'Cancelar CFDI Traslado TMS'

    # ============================================================
    # CAMPOS
    # ============================================================

    waybill_id = fields.Many2one(
        'tms.waybill',
        string='Viaje',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    cfdi_uuid = fields.Char(
        string='UUID a Cancelar',
        related='waybill_id.cfdi_uuid',
        readonly=True,
    )

    waybill_name = fields.Char(
        string='Folio Viaje',
        related='waybill_id.name',
        readonly=True,
    )

    motivo = fields.Selection([
        ('01', '01 — Comprobante emitido con errores con relación'),
        ('02', '02 — Comprobante emitido con errores sin relación'),
        ('03', '03 — No se llevó a cabo la operación'),
    ],
        string='Motivo de Cancelación',
        required=True,
        help='Seleccione el motivo SAT. Para el motivo 01 debe proporcionar el UUID del Traslado sustituto.'
    )

    uuid_sustituta = fields.Char(
        string='UUID Traslado Sustituto',
        size=36,
        copy=False,
        help='Requerido para motivo 01. UUID del nuevo CFDI Traslado que reemplaza a este.'
    )

    # ============================================================
    # ACCIONES
    # ============================================================

    def action_confirm_cancel(self):
        """
        Ejecuta la cancelación del CFDI Traslado ante el SAT.

        Flujo:
          1. Validar motivo 01: exige UUID sustituto con formato correcto
          2. Enviar solicitud de cancelación al PAC
          3. Marcar cfdi_status = 'cancelado' en el waybill
          4. Si motivo 02/03: regresar waybill al estado anterior para re-timbrar
          5. Registrar mensaje en el chatter del viaje
        """
        self.ensure_one()
        waybill = self.waybill_id

        # Validación motivo 01: requiere UUID del Traslado sustituto
        if self.motivo == '01':
            if not self.uuid_sustituta:
                raise UserError(_(
                    'El motivo 01 (errores con relación) requiere proporcionar el UUID del '
                    'CFDI Traslado sustituto ya timbrado. Timbre primero el viaje corregido '
                    'y luego proceda con la cancelación.'
                ))
            # Validar formato UUID básico: 36 caracteres con 4 guiones
            if len(self.uuid_sustituta) != 36 or self.uuid_sustituta.count('-') != 4:
                raise UserError(_(
                    'El UUID del Traslado sustituto no tiene el formato correcto. '
                    'Debe ser: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
                ))

        try:
            # Cancelar ante el PAC
            from ..services.pac_manager import PacManager
            manager = PacManager(self.env)
            manager.cancelar(waybill.cfdi_uuid, self.motivo, waybill.company_id)

            # Marcar el CFDI como cancelado
            waybill.write({'cfdi_status': 'cancelado'})

            # Motivo 02/03: revertir el estado del viaje para poder corregir y re-timbrar
            if self.motivo in ('02', '03'):
                estado_previo = self._get_estado_previo(waybill.state)
                if estado_previo:
                    waybill.write({'state': estado_previo})

            # Registrar en el chatter del viaje
            waybill.message_post(
                body=_(
                    'CFDI Traslado cancelado ante el SAT.<br/>'
                    'Motivo: <strong>%s</strong><br/>'
                    'UUID cancelado: %s%s'
                ) % (
                    dict(self._fields['motivo'].selection).get(self.motivo, self.motivo),
                    waybill.cfdi_uuid,
                    ('<br/>UUID sustituto: %s' % self.uuid_sustituta) if self.motivo == '01' and self.uuid_sustituta else '',
                ),
                subject=_('CFDI Traslado Cancelado'),
            )

            _logger.info(
                'CFDI Traslado cancelado — waybill %s, motivo %s, UUID sustituto %s',
                waybill.name, self.motivo, self.uuid_sustituta or 'N/A'
            )

        except UserError:
            raise
        except Exception as exc:
            raise UserError(
                _('Error al cancelar el CFDI Traslado:\n%s') % str(exc)
            )

    def _get_estado_previo(self, estado_actual):
        """
        Determina el estado al que debe regresar el waybill tras cancelar con motivo 02/03.

        La lógica sigue el flujo inverso del workflow:
          in_transit → waybill  (estaba en ruta, vuelve a Carta Porte lista)
          arrived    → waybill  (llegó a destino, vuelve a Carta Porte lista)
          waybill    → aprobado (tenía CP validada, vuelve a Aprobado para re-validar)

        Cualquier otro estado no requiere rollback (no debería tener CFDI timbrado).
        """
        mapa = {
            'in_transit': 'waybill',
            'arrived':    'waybill',
            'waybill':    'aprobado',
        }
        return mapa.get(estado_actual)
