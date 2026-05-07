# SDD — Etapa V2.7: Limpieza Final + QA

**Módulo:**   tms  
**Fecha:**    2026-05-07  
**Branch:**   feat/v2.7-limpieza-qa  
**Estado:**   En progreso  
**Modelo IA:** claude-sonnet-4-6

---

## 1. GIT

```bash
git checkout main && git pull origin main
git checkout -b feat/v2.7-limpieza-qa
```

---

## 2. Problema

El módulo TMS tiene:
- Archivos de verificación/debug en raíz (prohibido por Regla 12 de CLAUDE.md)
- Documentación de etapas anteriores como archivos sueltos (clutter)
- __manifest__.py con descripción genérica, no refleja el producto real
- Portal templates con t-esc (inseguro) en lugar de t-out
- Tests de portal faltantes (HttpCase, no TransactionCase)
- Posible falta de `.sudo()` en portal controller para permisos

---

## 3. Solución

**Limpieza de archivos:** Eliminar todos los verify_*.py, fix_*.py, *.md históricos de raíz.  
**Actualizar manifest:** Versión 2.7.0, descripción real del producto.  
**Tests portal:** HttpCase con 5 tests HTTP (no lógica Python).  
**Seguridad templates:** Reemplazar t-esc por t-out, agregar .sudo() en portal.py.  
**Verificación:** Grep y compilación de Python al terminar cada tarea.

---

## 4. Modelos afectados

| Modelo | Acción | Archivo |
|--------|--------|---------|
| tms.waybill | No aplica | controllers/portal.py — agregar .sudo() |
| tests | Create | tests/test_portal_tms.py |

---

## 5. File Manifest

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| **Eliminar** | verify_*.py (11 archivos) | Scripts de verificación históricos |
| **Eliminar** | fix_*.py (3 archivos) | Scripts de fix históricos |
| **Eliminar** | check_modules.py, find_duplicates.py, load_demo.py, reset_admin.py, reset_pass.py | Utilidades de desarrollo |
| **Eliminar** | run_verify.sh, test_write.py, update_list.py | Scripts auxiliares |
| **Eliminar** | *.md históricos (8 archivos) | Documentación de etapas anteriores |
| **Eliminar** | verification_result.txt, *.log | Logs de verificación |
| **Modify** | __manifest__.py | Versión 2.7.0, descripción real |
| **Create** | tests/test_portal_tms.py | 5 HttpCase tests |
| **Modify** | views/tms_portal_templates.xml | Reemplazar t-esc por t-out |
| **Modify** | controllers/portal.py | Agregar .sudo() en portal_my_waybills_list |
| **Modify** | tests/__init__.py | Importar test_portal_tms |
| **Modify** | .gitignore | Agregar odoo.log si falta |

---

## 6. Campos nuevos

N/A — Solo limpieza y tests, sin nuevos campos.

---

## 7. Flujo funcional

1. **Desarrollador:** Clona rama feat/v2.7-limpieza-qa
2. **Python compiler:** Verifica que controllers/portal.py compila sin errores
3. **Pytest:** Corre tests HttpCase — 5 tests pasan
4. **Grep:** Verifica t-esc = 0 en templates, verify_*.py = 0 en raíz
5. **User:** Navega a `/my` (GET 200), `/my/waybills` (GET 200), `/my/waybills/999999` (GET 302/404)
6. **Portal user:** Descarga XML CFDI si existe (GET 200 con archivo)

---

## 8. Criterios de aceptación

- [ ] AC-01: Todos los verify_*.py, fix_*.py eliminados de raíz (git ls-files grep = 0)
- [ ] AC-02: Todos los *.md históricos (ERRORES_CORREGIDOS, FASE_2, etc.) eliminados
- [ ] AC-03: __manifest__.py versión 2.7.0, descripción real del TMS
- [ ] AC-04: 5 HttpCase tests en tests/test_portal_tms.py, todos pasan
- [ ] AC-05: 0 ocurrencias t-esc en views/tms_portal_templates.xml (verificado con grep)
- [ ] AC-06: controllers/portal.py compila sin SyntaxError, .sudo() agregado en portal_my_waybills_list
- [ ] AC-07: GET /my = 200 (portal user), GET /my/waybills = 200, GET /my/waybills/999999 = 302 o 404
- [ ] AC-08: odoo.log en .gitignore
- [ ] AC-09: Sin warnings en `python3 -m py_compile` ni logs de Odoo
- [ ] AC-10: Documentación limpia — CLAUDE.md, AGENTS.md, STATUS.md no requieren cambios en V2.7

---

## 9. Tests requeridos

**HttpCase — tests/test_portal_tms.py:**

```python
test_portal_home_200:
  Verifica que GET /my retorna 200 para usuario portal autenticado
  Assertions: status_code == 200, "<h1>" en body

test_portal_waybills_list_200:
  Verifica que GET /my/waybills retorna 200, lista visible
  Assertions: status_code == 200, "Mis Viajes" o "waybills" en body

test_portal_waybill_detail_redirect:
  Verifica que GET /my/waybills/999999 (ID inexistente) retorna 302 redirect, NO 500
  Assertions: status_code == 302, redirect location

test_portal_waybill_xml_404:
  Verifica que GET /my/waybills/999999/xml (ID inexistente) retorna 404, NO 500
  Assertions: status_code == 404, sin KeyError en logs

test_portal_waybill_pdf_404:
  Verifica que GET /my/waybills/999999/pdf (ID inexistente) retorna 404, NO 500
  Assertions: status_code == 404, sin KeyError en logs
```

---

## 10. Definition of Done

- [ ] Todos los tests pasan: `python3 odoo-bin -c odoo.conf --test-enable --test-tags /tms -d tms_v2 --stop-after-init`
- [ ] Sin errores ni warnings en odoo.log (excepto deprecation warnings nativos)
- [ ] `git ls-files | grep -E "verify_|fix_"` = vacío
- [ ] `grep -c 't-esc' views/tms_portal_templates.xml` = 0
- [ ] `python3 -m py_compile controllers/portal.py` = sin errores
- [ ] Raíz limpia: solo directorios (models, views, controllers, static, etc.) y archivos permitidos (__manifest__.py, __init__.py, docs/)
- [ ] __manifest__.py: versión='19.0.2.7.0', summary y description reescritos
- [ ] No hay cambios en tms_waybill.py, tms_destination.py, ni modelos SAT

---

## 11. Restricciones

- NO modificar modelos operativos (tms.waybill, etc.) — solo limpieza
- NO cambiar workflow de estados
- NO agregar dependencias externas en __manifest__.py
- Portal templates: SOLO reemplazar t-esc → t-out, no cambiar lógica QWeb
- Tests: SOLO HttpCase para rutas HTTP, NO TransactionCase
- Archivos .gitignore: agregar odoo.log si falta, NO modificar patterns existentes

---

## 12. Para Claude Code Terminal

```
MODELO: claude-sonnet-4-6

COMANDO:
claude --model claude-sonnet-4-6 "Ejecuta etapa V2.7 según SDD..."

INPUT: Este SDD + archivos actuales en /tms
OUTPUT:
  - Archivos eliminados: verify_*.py (11), fix_*.py (3), etc.
  - Archivos creados: tests/test_portal_tms.py
  - Archivos modificados: __manifest__.py, controllers/portal.py, views/tms_portal_templates.xml, tests/__init__.py, .gitignore

VALIDACIÓN:
  - python3 -m py_compile controllers/portal.py
  - grep -c 't-esc' views/tms_portal_templates.xml (debe 0)
  - git ls-files | grep verify_ (debe vacío)
  - Tests: python3 odoo-bin -c odoo.conf --test-enable --test-tags /tms -d tms_v2 --stop-after-init
```

---

## 13. Upgrade command

```bash
cd /Users/macbookpro/odoo/odoo19ce/odoo-19.0
/Users/macbookpro/odoo/odoo19ce/odoo-19.0/.venv/bin/python odoo-bin -c /Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf -u tms -d tms_v2 --stop-after-init
```

---

## 14. Notas técnicas

- **T-esc vs T-out:** `t-esc` escapa HTML (safe por defecto), `t-out` no escapa (inseguro). En Odoo 19, templates de portal deben usar `t-out` explícitamente solo para valores seguros (ej. ID, name del partner). Para evitar issues:
  - Variables HTML-safe (partner.name, waybill.name) → `t-out`
  - Textos traducibles (`_('...')`) → `t-out`
  - Valores de BD directos (sin HTML) → `t-out`
  
- **HttpCase vs TransactionCase:** TransactionCase corre en una transacción, NO levanta servidor. No detecta KeyError en templates ni errores 500. HttpCase levanta servidor real, atrapa todos los errores HTTP. Obligatorio para tests de portal.

- **Portal .sudo():** Portal users no tienen permisos `read` en tms.waybill. El controlador debe:
  ```python
  # Domain mantiene la seguridad multiempresa
  domain = [
      ('partner_invoice_id', '=', partner.id),
      ('company_id', 'in', request.env.user.company_ids.ids)
  ]
  # .sudo() permite leer, pero domain restringe a sus propios registros
  count = request.env['tms.waybill'].sudo().search_count(domain)
  ```

---

_SDD V2.7 — Limpieza Final + QA_  
_Siguiente: V2.8 SaaS — PRIMER CLIENTE PAGA_
