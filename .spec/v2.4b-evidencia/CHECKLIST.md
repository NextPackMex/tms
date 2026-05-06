# CHECKLIST.md — V2.4b Evidencia Fotográfica

Rama: feat/v2.4b-evidencia
Modelo Claude Code: claude-sonnet-4-6

---

## [ ] 0. Preparación

- [ ] git checkout main && git pull origin main
- [ ] git checkout -b feat/v2.4b-evidencia
- [ ] Leer DESIGN.md completo antes de tocar cualquier archivo
- [ ] Verificar que tms_evidence.py NO existe:
  ```bash
  ls models/tms_evidence.py 2>&1  # debe decir "No such file"
  grep -rn "tms_evidence\|evidence_ids\|evidence_count" models/
  grep -rn "tms.evidence" security/ir.model.access.csv
  ```

---

## [ ] 1. Modelo tms.evidence.photo

Archivo: `models/tms_evidence.py` (NUEVO)

- [ ] Clase TmsEvidencePhoto con _name = 'tms.evidence.photo'
- [ ] Campo waybill_id — Many2one tms.waybill, required=True, ondelete='cascade'
- [ ] Campo photo — Binary, required=True
- [ ] Campo photo_filename — Char
- [ ] Campo photo_type — Selection con 6 opciones, required=True
- [ ] Campo date — Datetime, default=fields.Datetime.now, readonly=True
- [ ] Campo user_id — Many2one res.users, default=lambda self: self.env.user, readonly=True
- [ ] Campo notes — Text
- [ ] Campo company_id — Many2one res.company, related='waybill_id.company_id', store=True
- [ ] _order = 'date desc'
- [ ] Docstring en español en la clase y en cada método

---

## [ ] 2. Campos nuevos en tms.waybill

Archivo: `models/tms_waybill.py`

- [ ] Buscar con grep que evidence_ids no existe antes de agregar
- [ ] Agregar evidence_ids — One2many('tms.evidence.photo', 'waybill_id')
- [ ] Agregar evidence_count — Integer compute='_compute_evidence_count', store=True
- [ ] Método _compute_evidence_count: cuenta len(self.evidence_ids)
- [ ] Método action_view_evidences: retorna ir.actions.act_window a tms.evidence.photo
- [ ] Docstring en español en ambos métodos

---

## [ ] 3. Vista tms_evidence_views.xml

Archivo: `views/tms_evidence_views.xml` (NUEVO)

- [ ] Vista list con columnas: date, photo_type, user_id, notes
- [ ] Vista form con: photo (widget image), photo_type, date, user_id, notes
- [ ] ir.actions.act_window para abrir desde smart button
- [ ] XML ids con prefijo tms_

---

## [ ] 4. Modificar tms_waybill_views.xml

Archivo: `views/tms_waybill_views.xml`

- [ ] Smart button con icon fa-camera, invisible si evidence_count == 0
- [ ] Pestaña "Evidencias 📷" con field evidence_ids en modo kanban
  - Kanban: miniatura foto + tipo + fecha
- [ ] Pestaña visible en todos los estados (sin invisible)

---

## [ ] 5. Seguridad

Archivo: `security/ir.model.access.csv`

- [ ] access_tms_evidence_photo_user → group_tms_user: 1,1,1,0
- [ ] access_tms_evidence_photo_manager → group_tms_manager: 1,1,1,1
- [ ] access_tms_evidence_photo_driver → group_tms_driver: 1,1,1,0

---

## [ ] 6. Actualizar __init__.py y __manifest__.py

- [ ] Agregar `from . import tms_evidence` en models/__init__.py
- [ ] Agregar `'views/tms_evidence_views.xml'` en __manifest__.py data
- [ ] Verificar que tms_evidence.py NO se duplica en __init__.py

---

## [ ] 7. Validación

```bash
# Verificar sintaxis Python
python3 -m py_compile models/tms_evidence.py
python3 -m py_compile models/tms_waybill.py

# Actualizar módulo (hay campos nuevos)
cd /Users/macbookpro/odoo/odoo19ce
odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin \
  -c proyectos/tms/odoo.conf -u tms -d tms_v2 --stop-after-init

# Verificar log limpio
grep -n "WARNING\|ERROR" proyectos/tms/odoo.log | tail -20
```

---

## [ ] 8. Revisión final

- [ ] AC-01 al AC-06 cubiertos
- [ ] Smart button visible con fotos, oculto sin fotos
- [ ] Usuario TMS no ve botón eliminar en evidencias
- [ ] Manager sí puede eliminar
- [ ] Estados del waybill NO modificados
- [ ] CLAUDE.md NO modificado (lo hace Claude Web al cerrar etapa)
- [ ] NO push sin orden de Mois
