# -*- coding: utf-8 -*-
"""
Wizard de Cancelación de CFDI Ingreso TMS.

Permite cancelar una factura de flete (account.move) timbrada ante el SAT,
seleccionando el motivo correcto según la situación:

  Motivo 01 — Errores con relación:
    Error en RFC, monto u otro dato. Se corrige timbrado una factura sustituta primero.
    Waybills siguen en 'closed' — la sustituta cubre el cobro.

  Motivo 02 — Errores sin relación:
    Error pero no hay factura sustituta (ej: factura duplicada, cliente equivocado).
    Waybills regresan a 'arrived' para refacturar.

  Motivo 03 — Operación no realizada:
    El cliente rechazó el cobro o el viaje fue cancelado.
    Waybills regresan a 'arrived' para refacturar o cancelar.

IMPORTANTE: Motivo 01 requiere que exista una factura sustituta ya timbrada antes
de proceder con la cancelación. El wizard bloquea si no se proporciona el UUID sustituto.
"""
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TmsCancelInvoiceWizard(models.TransientModel):
    """
    Wizard de cancelación de CFDI Ingreso con selección de motivo SAT.
    Llama a account_move_tms.action_tms_confirm_cancellation() tras validar.
    """
    _name        = 'tms.cancel.invoice.wizard'
    _description = 'Cancelar CFDI Ingreso TMS'

    # ============================================================
    # CAMPOS
    # ============================================================

    move_id = fields.Many2one(
        'account.move',
        string='Factura',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    motivo = fields.Selection([
        ('01', '01 — Comprobante emitido con errores con relación'),
        ('02', '02 — Comprobante emitido con errores sin relación'),
        ('03', '03 — No se llevó a cabo la operación'),
    ],
        string='Motivo de Cancelación',
        required=True,
        help='Seleccione el motivo SAT. Para el motivo 01 debe proporcionar el UUID de la factura sustituta.'
    )

    uuid_sustituta = fields.Char(
        string='UUID Factura Sustituta',
        size=36,
        copy=False,
        help='Requerido para motivo 01. UUID de la nueva factura que reemplaza a esta.'
    )

    # Información de contexto (readonly — para que el usuario vea qué está cancelando)
    move_name = fields.Char(
        string='Folio Factura',
        related='move_id.name',
        readonly=True,
    )
    move_uuid = fields.Char(
        string='UUID a Cancelar',
        related='move_id.tms_cfdi_uuid',
        readonly=True,
    )
    waybill_names = fields.Char(
        string='Viajes incluidos',
        compute='_compute_waybill_names',
        readonly=True,
    )

    # ============================================================
    # CÓMPUTOS
    # ============================================================

    @api.depends('move_id', 'move_id.tms_waybill_ids')
    def _compute_waybill_names(self):
        """Genera string con los nombres de los viajes para mostrar en el wizard."""
        for wiz in self:
            if wiz.move_id and wiz.move_id.tms_waybill_ids:
                wiz.waybill_names = ', '.join(
                    wiz.move_id.tms_waybill_ids.mapped('name')
                )
            else:
                wiz.waybill_names = '—'

    # ============================================================
    # ACCIONES
    # ============================================================

    def action_confirm_cancel(self):
        """
        Ejecuta la cancelación del CFDI Ingreso ante el SAT.

        Flujo:
          1. Validar motivo y UUID sustituta (si motivo 01)
          2. Enviar solicitud de cancelación al PAC
          3. Llamar a move.action_tms_confirm_cancellation() con el motivo
          4. Si motivo 02/03: liberar waybills a 'arrived' automáticamente
        """
        self.ensure_one()
        move = self.move_id

        # Validación motivo 01: requiere UUID sustituta
        if self.motivo == '01':
            if not self.uuid_sustituta:
                raise UserError(_(
                    'El motivo 01 (errores con relación) requiere proporcionar el UUID de la '
                    'factura sustituta ya timbrada. Timbre primero la factura corregida y luego '
                    'proceda con la cancelación.'
                ))
            # Validar formato UUID básico
            if len(self.uuid_sustituta) != 36 or self.uuid_sustituta.count('-') != 4:
                raise UserError(_(
                    'El UUID de la factura sustituta no tiene el formato correcto. '
                    'Debe ser: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
                ))

        try:
            # Cancelar ante el PAC
            from ..services.pac_manager import PacManager
            manager = PacManager(self.env)
            manager.cancelar(move.tms_cfdi_uuid, self.motivo, move.company_id)

            # Confirmar la cancelación en el modelo (actualiza estado y libera waybills)
            move.action_tms_confirm_cancellation(
                motivo=self.motivo,
                uuid_sustituta=self.uuid_sustituta if self.motivo == '01' else None,
            )

            _logger.info(
                'CFDI Ingreso cancelado — move %s, motivo %s, UUID sustituta %s',
                move.name, self.motivo, self.uuid_sustituta or 'N/A'
            )

        except UserError:
            raise
        except Exception as exc:
            raise UserError(
                _('Error al cancelar el CFDI Ingreso:\n%s') % str(exc)
            )
