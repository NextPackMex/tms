# -*- coding: utf-8 -*-
"""
Wizard de Facturación TMS — CFDI Ingreso.

Permite crear una factura (account.move) vinculada a uno o varios viajes (tms.waybill),
timbrar el CFDI Ingreso y cerrar automáticamente los viajes facturados.

Flujo (4 pasos):
  Paso 1 — Modo: simple (1 viaje) o consolidado (N viajes del mismo cliente)
  Paso 2 — Cliente + selección de viajes + resumen de montos en tiempo real
  Paso 3 — Datos fiscales: UsoCFDI, diario contable, confirmación
  Paso 4 — Resultado: UUID, PDF, Email

El wizard crea el account.move, vincula los waybills y llama a
account_move_tms.action_tms_stamp_ingreso() para timbrar.
"""
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TmsInvoiceWizard(models.TransientModel):
    """
    Wizard de 4 pasos para generar facturas de flete con CFDI Ingreso.
    El wizard soporta modo simple (1 viaje) y consolidado (N viajes mismo cliente).
    """
    _name        = 'tms.invoice.wizard'
    _description = 'Wizard de Facturación TMS (CFDI Ingreso)'

    # ============================================================
    # PASO 1 — MODO DE FACTURACIÓN
    # ============================================================

    modo = fields.Selection([
        ('simple',      'Un viaje — Factura individual'),
        ('consolidado', 'Varios viajes — Factura consolidada'),
    ],
        string='Modo de Facturación',
        default='simple',
        required=True,
        help='Simple: una factura por viaje. Consolidado: una factura para N viajes del mismo cliente.'
    )

    step = fields.Integer(
        string='Paso actual',
        default=1,
    )

    # ============================================================
    # PASO 2 — CLIENTE Y SELECCIÓN DE VIAJES
    # ============================================================

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        domain="[('type', 'in', ['invoice', 'contact'])]",
        help='Cliente al que se facturarán los viajes seleccionados'
    )

    waybill_ids = fields.Many2many(
        'tms.waybill',
        'tms_invoice_wizard_waybill_rel',
        'wizard_id',
        'waybill_id',
        string='Viajes a facturar',
        help='Viajes (en estado "En Destino") que se incluirán en la factura'
    )

    available_waybill_ids = fields.Many2many(
        'tms.waybill',
        'tms_invoice_wizard_avail_rel',
        'wizard_id',
        'waybill_id',
        string='Viajes disponibles',
        compute='_compute_available_waybills',
        help='Viajes del cliente seleccionado en estado arrived sin facturar'
    )

    # Advertencia para consolidado con distintos vehículos
    vehicle_warning = fields.Char(
        string='Advertencia vehículos',
        compute='_compute_vehicle_warning',
        help='Aviso si los viajes seleccionados tienen distintos vehículos'
    )

    # ============================================================
    # RESUMEN DE MONTOS (actualización en tiempo real)
    # ============================================================

    subtotal_total = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    iva_total = fields.Monetary(
        string='IVA (16%)',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    retencion_total = fields.Monetary(
        string='Retención (4%)',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    total_factura = fields.Monetary(
        string='Total Factura',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ============================================================
    # PASO 3 — DATOS FISCALES
    # ============================================================

    uso_cfdi_id = fields.Many2one(
        'tms.sat.uso.cfdi',
        string='Uso CFDI',
        default=lambda self: self.env['tms.sat.uso.cfdi'].search([('code', '=', 'G03')], limit=1),
        help='Uso CFDI del receptor (c_UsoCFDI). G03 = Gastos en General es el default para flete.'
    )
    forma_pago_id = fields.Many2one(
        'tms.sat.forma.pago',
        string='Forma de Pago',
        default=lambda self: self.env['tms.sat.forma.pago'].search([('code', '=', '99')], limit=1),
        help='Forma de pago CFDI (c_FormaPago). 99 = Por definir es el default para flete.'
    )
    metodo_pago_id = fields.Many2one(
        'tms.sat.metodo.pago',
        string='Método de Pago',
        default=lambda self: self.env['tms.sat.metodo.pago'].search([('code', '=', 'PUE')], limit=1),
        help='Método de pago CFDI (c_MetodoPago). PUE = Pago en una sola exhibición.'
    )

    journal_id = fields.Many2one(
        'account.journal',
        string='Diario Contable',
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
        help='Diario de ventas TMS. Pre-llenado con el diario configurado en Ajustes → TMS.'
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    # ============================================================
    # PASO 4 — RESULTADO (después de timbrar)
    # ============================================================

    result_uuid = fields.Char(
        string='UUID',
        readonly=True,
        copy=False,
    )
    result_move_id = fields.Many2one(
        'account.move',
        string='Factura Creada',
        readonly=True,
        copy=False,
    )
    result_error = fields.Text(
        string='Error',
        readonly=True,
        copy=False,
    )

    # ============================================================
    # CÓMPUTOS
    # ============================================================

    @api.depends('partner_id')
    def _compute_available_waybills(self):
        """
        Carga los viajes disponibles para facturar del cliente seleccionado.
        Criterios: estado 'arrived' + invoice_status='no_invoice' + mismo cliente.
        """
        for wiz in self:
            if wiz.partner_id:
                wiz.available_waybill_ids = self.env['tms.waybill'].search([
                    ('partner_invoice_id', '=', wiz.partner_id.id),
                    ('state',             '=', 'arrived'),
                    ('invoice_status',    '=', 'no_invoice'),
                    ('company_id',        '=', wiz.company_id.id),
                ])
            else:
                wiz.available_waybill_ids = False

    @api.depends('waybill_ids', 'waybill_ids.vehicle_id')
    def _compute_vehicle_warning(self):
        """
        Genera advertencia si los viajes seleccionados tienen distintos vehículos.
        No bloquea — el SAT permite el Ingreso con múltiples vehículos pero
        el nodo Autotransporte del XML solo incluye el del primer waybill.
        """
        for wiz in self:
            if len(wiz.waybill_ids) > 1:
                vehiculos = wiz.waybill_ids.mapped('vehicle_id')
                if len(vehiculos) > 1:
                    placas = ', '.join(v.license_plate or '' for v in vehiculos)
                    wiz.vehicle_warning = (
                        '⚠ Los viajes seleccionados tienen distintos vehículos: %s. '
                        'El XML usará el vehículo del primer viaje en Autotransporte.' % placas
                    )
                else:
                    wiz.vehicle_warning = False
            else:
                wiz.vehicle_warning = False

    @api.depends('waybill_ids', 'waybill_ids.amount_untaxed',
                 'waybill_ids.amount_tax', 'waybill_ids.amount_retention',
                 'waybill_ids.amount_total', 'partner_id', 'partner_id.is_company')
    def _compute_totals(self):
        """
        Calcula subtotal, IVA y retención consolidados de los viajes seleccionados.
        La retención 4% aplica solo si el cliente es persona moral (is_company=True).
        """
        for wiz in self:
            subtotal  = sum(wiz.waybill_ids.mapped('amount_untaxed'))
            iva       = sum(wiz.waybill_ids.mapped('amount_tax'))
            retencion = sum(wiz.waybill_ids.mapped('amount_retention'))
            total     = subtotal + iva - retencion
            wiz.subtotal_total  = subtotal
            wiz.iva_total       = iva
            wiz.retencion_total = retencion
            wiz.total_factura   = total

    # ============================================================
    # ONCHANGES
    # ============================================================

    @api.onchange('modo')
    def _onchange_modo(self):
        """Limpia la selección de viajes al cambiar de modo."""
        self.waybill_ids = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Limpia viajes seleccionados cuando cambia el cliente."""
        self.waybill_ids = False

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Pre-llena el diario TMS configurado en Ajustes cuando cambia la empresa."""
        if self.company_id:
            self.journal_id = self.company_id.tms_sales_journal_id or False

    # ============================================================
    # ACCIONES DEL WIZARD
    # ============================================================

    def action_next_step(self):
        """Avanza al siguiente paso del wizard."""
        self.ensure_one()
        if self.step == 1:
            self._validate_step1()
        elif self.step == 2:
            self._validate_step2()
        elif self.step == 3:
            return self.action_create_and_stamp()
        self.step += 1
        return self._reopen()

    def action_prev_step(self):
        """Regresa al paso anterior del wizard."""
        self.ensure_one()
        if self.step > 1:
            self.step -= 1
        return self._reopen()

    def _get_tax_ids_for_partner(self, partner):
        """
        Devuelve la lista de IDs de impuestos SAT a aplicar según el tipo de receptor.

        Regla fiscal (Art. 1-A LIVA + Art. 3 RLIVA):
          - Persona Física  (RFC 13 chars, is_company=False) → solo IVA 16%
          - Persona Moral   (RFC 12 chars, is_company=True)  → IVA 16% + Retención 4%

        Busca los impuestos por amount en la compañía activa. Si no encuentra la
        retención 4% en el catálogo contable, la omite con un warning en el log
        (no bloquea la facturación — el impuesto puede añadirse después).
        """
        company = self.company_id
        Tax = self.env['account.tax']

        # IVA 16% — impuesto de traslado estándar para flete
        tax_iva = Tax.search([
            ('amount',        '=', 16.0),
            ('amount_type',   '=', 'percent'),
            ('type_tax_use',  '=', 'sale'),
            ('active',        '=', True),
            ('company_id',    '=', company.id),
        ], limit=1)

        if not tax_iva:
            raise UserError(_(
                'No se encontró el impuesto IVA 16%% en el catálogo contable. '
                'Verifique que exista un impuesto de venta con monto 16%% activo.'
            ))

        tax_ids = [tax_iva.id]

        # Retención 4% — solo personas morales (is_company=True)
        if partner.is_company:
            tax_ret = Tax.search([
                ('type_tax_use', '=', 'sale'),
                ('active',       '=', True),
                ('company_id',   '=', company.id),
                '|',
                ('name',   'ilike', 'retenci'),
                ('amount', '=',     -4.0),
            ], limit=1)

            if tax_ret:
                tax_ids.append(tax_ret.id)
            else:
                _logger.warning(
                    'Retención 4%% no encontrada en catálogo contable para empresa %s. '
                    'El CFDI se generará sin retención. Agregue el impuesto en Contabilidad → Impuestos.',
                    company.name,
                )

        return tax_ids

    def action_create_and_stamp(self):
        """
        Paso final: crea el account.move, vincula los viajes y timbra el CFDI Ingreso.

        Flujo:
          1. Validar datos completos
          2. Resolver impuestos IVA/Retención según tipo de receptor
          3. Crear account.move en borrador con líneas de factura + tax_ids
          4. Vincular tms_waybill_ids al move
          5. Llamar a action_tms_stamp_ingreso() en el move
          6. Mostrar paso 4 con UUID o error

        Regla de impuestos:
          - Persona Física  → IVA 16%
          - Persona Moral   → IVA 16% + Retención 4% (si existe en catálogo)
        """
        self.ensure_one()
        self._validate_step3()

        # Verificar que el diario sea el TMS
        journal = self.journal_id or self.company_id.tms_sales_journal_id
        if not journal:
            raise UserError(_(
                'No hay un diario TMS configurado. '
                'Configure el diario en Ajustes → TMS → Facturación.'
            ))

        try:
            # Resolver impuestos según tipo de receptor (PF o PM)
            tax_ids = self._get_tax_ids_for_partner(self.partner_id)

            # Crear líneas del account.move — una por waybill, con tax_ids
            invoice_lines = []
            for waybill in self.waybill_ids:
                invoice_lines.append((0, 0, {
                    'name':       'Flete — %s' % (waybill.name or waybill.route_name or ''),
                    'quantity':   1.0,
                    'price_unit': waybill.amount_untaxed,
                    'tax_ids':    [(6, 0, tax_ids)],
                }))

            # Crear account.move en borrador con datos fiscales del wizard
            move = self.env['account.move'].create({
                'move_type':           'out_invoice',
                'journal_id':          journal.id,
                'partner_id':          self.partner_id.id,
                'invoice_line_ids':    invoice_lines,
                'tms_waybill_ids':     [(6, 0, self.waybill_ids.ids)],
                'tms_uso_cfdi_id':     self.uso_cfdi_id.id or False,
                'tms_forma_pago_id':   self.forma_pago_id.id or False,
                'tms_metodo_pago_id':  self.metodo_pago_id.id or False,
            })

            # Timbrar
            move.action_tms_stamp_ingreso()

            # Guardar resultado para el paso 4
            self.write({
                'result_uuid':    move.tms_cfdi_uuid,
                'result_move_id': move.id,
                'result_error':   False,
                'step':           4,
            })

        except UserError as exc:
            self.write({
                'result_error': str(exc),
                'step':         4,
            })

        return self._reopen()

    def action_view_invoice(self):
        """Abre la factura creada en el formulario nativo de Odoo."""
        self.ensure_one()
        if not self.result_move_id:
            return
        return {
            'type':      'ir.actions.act_window',
            'name':      _('Factura TMS'),
            'res_model': 'account.move',
            'res_id':    self.result_move_id.id,
            'view_mode': 'form',
            'target':    'current',
        }

    # ============================================================
    # VALIDACIONES INTERNAS
    # ============================================================

    def _validate_step1(self):
        """Valida que se haya seleccionado un modo."""
        if not self.modo:
            raise UserError(_('Seleccione el modo de facturación.'))

    def _validate_step2(self):
        """Valida cliente y viajes seleccionados según el modo."""
        if not self.partner_id:
            raise UserError(_('Seleccione el cliente a facturar.'))
        if not self.waybill_ids:
            raise UserError(_('Seleccione al menos un viaje para facturar.'))
        if self.modo == 'simple' and len(self.waybill_ids) > 1:
            raise UserError(_(
                'En modo "Un viaje" solo se puede seleccionar un viaje. '
                'Para facturar varios viajes use el modo "Varios viajes".'
            ))
        # Verificar que todos los viajes sean del mismo cliente
        clientes = self.waybill_ids.mapped('partner_invoice_id')
        if len(clientes) > 1:
            raise ValidationError(_(
                'Todos los viajes deben ser del mismo cliente. '
                'Clientes detectados: %s'
            ) % ', '.join(c.name for c in clientes))
        # Verificar que todos estén en estado arrived o posterior
        no_disponibles = self.waybill_ids.filtered(
            lambda w: w.state not in ('arrived', 'waybill', 'in_transit', 'aprobado')
        )
        if no_disponibles:
            raise UserError(_(
                'Los siguientes viajes no están listos para facturar: %s'
            ) % ', '.join(no_disponibles.mapped('name')))

    def _validate_step3(self):
        """Valida datos fiscales antes de crear la factura."""
        if not self.uso_cfdi_id:
            raise UserError(_('Seleccione el Uso CFDI.'))
        if not self.forma_pago_id:
            raise UserError(_('Seleccione la Forma de Pago.'))
        if not self.metodo_pago_id:
            raise UserError(_('Seleccione el Método de Pago.'))

    # ============================================================
    # HELPER INTERNO
    # ============================================================

    def _reopen(self):
        """Reabre el wizard en el mismo registro para mostrar el paso actualizado."""
        return {
            'type':      'ir.actions.act_window',
            'res_model': self._name,
            'res_id':    self.id,
            'view_mode': 'form',
            'target':    'new',
        }
