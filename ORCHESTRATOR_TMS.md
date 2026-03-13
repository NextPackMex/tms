# ORCHESTRATOR.md — TMS Hombre Camión
> Ubicación: `/tms/ORCHESTRATOR.md` (raíz del repo, junto a AGENTS.md y CLAUDE.md)
> Uso: Claude Code CLI lee este archivo para dividir una etapa en sub-agentes paralelos

---

## CÓMO ACTIVAR EL ORQUESTADOR

Cuando quieras implementar una etapa completa con sub-agentes paralelos, lanza Claude Code CLI con este comando desde la raíz del repo:

```bash
claude "Lee ORCHESTRATOR.md y el SDD en docs/etapa-X.X.X.md, luego ejecuta el flujo multi-agente completo"
```

Claude Code leerá este archivo, dividirá el SDD en 4 contratos y lanzará los agentes en paralelo usando Git Worktrees.

---

## ROL DEL ORQUESTADOR

El orquestador **NUNCA escribe código directamente**. Su único trabajo es:
1. Leer el SDD de la etapa (`docs/etapa-X.X.X.md`)
2. Extraer los contratos de cada agente
3. Crear las ramas Git con Worktrees
4. Lanzar los 4 sub-agentes en paralelo
5. Esperar sus outputs
6. Reportar al humano para aprobación

---

## SETUP DE GIT WORKTREES

El orquestador ejecuta esto antes de lanzar los agentes:

```bash
# Asegurarse de estar en main actualizado
git checkout main && git pull origin main

# Crear 4 worktrees independientes (uno por agente)
git worktree add ../tms-models feat/etapa-X.X.X-models
git worktree add ../tms-views  feat/etapa-X.X.X-views
git worktree add ../tms-tests  feat/etapa-X.X.X-tests
# El agente de seguridad NO necesita worktree — solo audita, no escribe código

# Verificar worktrees activos
git worktree list
```

Cada carpeta (`../tms-models`, `../tms-views`, `../tms-tests`) es independiente. Los agentes trabajan en paralelo sin colisiones.

---

## LOS 4 SUB-AGENTES

### AGENTE A — Modelos Python
**Rama:** `feat/etapa-X.X.X-models`
**Carpeta de trabajo:** `../tms-models/models/`
**Archivos que puede tocar:** SOLO `models/*.py` y `models/__init__.py`

**Contrato de entrada (lo que recibe del SDD):**
```
- Nombre del modelo nuevo o a extender (_name / _inherit)
- Lista de campos con tipo, string, required, help
- Métodos compute y sus dependencias (@api.depends)
- Restricciones de negocio (@api.constrains)
- Reglas company_id (si el modelo es operativo o catálogo SAT)
```

**Contrato de salida (lo que entrega):**
```
- Archivo models/nombre_modelo.py completo y validado
- Sin campos ni métodos duplicados (verificado con grep)
- Docstrings en español en cada clase y método
- Sin required=True en campos heredados
- company_id presente si es modelo operativo
- Validado con: python3 -m py_compile models/nombre_modelo.py
```

**Restricciones absolutas:**
- NO modificar `tms_waybill.py` sin grep previo de duplicados
- NO poner company_id en catálogos SAT
- NO usar _sql_constraints — usar models.Constraint()
- NO usar name_search override — usar _rec_names_search

---

### AGENTE B — Vistas XML
**Rama:** `feat/etapa-X.X.X-views`
**Carpeta de trabajo:** `../tms-views/views/`
**Archivos que puede tocar:** SOLO `views/*.xml` y `views/tms_menus.xml`

**Contrato de entrada (lo que recibe del Agente A):**
```
- Lista exacta de campos del modelo (nombre, tipo, string)
- Nombre del modelo (_name)
- Grupos de seguridad aplicables (group_tms_user / manager / driver)
- Tipo de vista requerida (list, form, kanban, search)
```

**Contrato de salida (lo que entrega):**
```
- Archivo views/nombre_modelo_views.xml con list + form + search
- XML IDs únicos (verificado con grep -rn "record id=" views/)
- Usa <list> (NUNCA <tree>)
- Usa invisible="condicion" (NUNCA attrs="{...}")
- Menú agregado en tms_menus.xml si aplica
- Sin vistas duplicadas
```

**Restricciones absolutas:**
- NO inventar campos — solo usar los del contrato del Agente A
- NO usar <tree> — siempre <list>
- NO usar attrs="{...}" — deprecated en Odoo 19
- NO duplicar XML IDs existentes — verificar con grep primero
- NO tocar sat_menus.xml ni menús existentes sin instrucción explícita

---

### AGENTE C — Tests Unitarios
**Rama:** `feat/etapa-X.X.X-tests`
**Carpeta de trabajo:** `../tms-tests/tests/`
**Archivos que puede tocar:** SOLO `tests/test_*.py` y `tests/__init__.py`

**Contrato de entrada (lo que recibe del Agente A):**
```
- Modelo a testear (_name)
- Campos críticos del negocio
- Workflow de estados (si aplica)
- Reglas de validación (@api.constrains)
- Grupos de seguridad
```

**Contrato de salida (lo que entrega):**
```
- Archivo tests/test_nombre_modelo.py con mínimo:
  · Test de creación exitosa del modelo
  · Test de validación de campos requeridos
  · Test de workflow completo (si tiene estados)
  · Test de cálculos críticos (cotización, utilidad, etc.)
  · Test de permisos por grupo (user / manager / driver)
  · Test de edge cases del negocio (montos negativos, fechas inválidas, etc.)
- Usando TransactionCase de Odoo (rollback automático)
- @tagged('post_install', '-at_install', 'tms')
- Comando de ejecución documentado en el archivo
```

**Restricciones absolutas:**
- NO testear cosas triviales (getters simples, strings)
- SIEMPRE testear: auth, lógica de negocio crítica, integraciones
- SIEMPRE incluir setUpClass con datos de prueba reutilizables
- NO hacer asserts sin mensaje descriptivo

**Comando de ejecución:**
```bash
./odoo-bin -c odoo.conf -d tms_dev --test-enable --test-tags /tms --stop-after-init
```

---

### AGENTE D — Auditoría de Seguridad
**Rama:** ninguna — solo audita, NO escribe código
**Carpeta de trabajo:** trabaja sobre las 3 ramas anteriores (lee en modo lectura)

**Contrato de entrada (lo que recibe):**
```
- Output del Agente A (modelos Python)
- Output del Agente B (vistas XML)
- Output del Agente C (tests)
```

**Contrato de salida (reporte estructurado):**
```markdown
## Reporte de Seguridad — Etapa X.X.X
Fecha: YYYY-MM-DD

### 🔴 CRÍTICO (bloquea el PR)
- [ ] Item: descripción + archivo + línea + fix sugerido

### 🟡 ADVERTENCIA (revisar antes de producción)
- [ ] Item: descripción + archivo + línea + recomendación

### 🟢 OK
- Autenticación: ✅
- company_id en modelos operativos: ✅
- Sin secrets hardcodeados: ✅
- ACL en ir.model.access.csv: ✅
- Record Rules para multi-empresa: ✅
```

**Qué revisa:**
- SQL injection en métodos que construyen queries dinámicas
- Secrets o API keys hardcodeadas en el código
- Campos sin restricción de company_id en modelos operativos
- Ausencia de ACL en ir.model.access.csv para modelos nuevos
- Record Rules faltantes para aislamiento multi-empresa
- XSS en vistas XML (campos HTML sin escape)
- Auth débil (métodos públicos que deberían requerir grupo)
- Datos sensibles expuestos en logs o respuestas JSON

**Herramienta adicional (instalar una vez):**
```bash
# Revisión automática adicional con GitHub Action oficial de Anthropic
# Ver: github.com/anthropics/claude-code-security-review
```

---

## FLUJO COMPLETO PASO A PASO

```
1. Tú (Claude Web) generas docs/etapa-X.X.X.md (el SDD)
   ↓
2. Claude Code CLI lee ORCHESTRATOR.md + el SDD
   ↓
3. Orquestador crea 3 worktrees y lanza A, B, C en paralelo
   (D espera a que A y B terminen)
   ↓
4. A, B, C trabajan simultáneamente (sin colisiones por Worktrees)
   ↓
5. D audita los outputs de A, B, C
   ↓
6. Orquestador presenta reporte completo al humano (tú)
   ↓
7. Tú revisas y apruebas o rechazas cada agente
   ↓
8. Se abren 3 PRs (models, views, tests) → GitHub Actions valida
   ↓
9. Tú haces merge a main
   ↓
10. Limpiar worktrees:
    git worktree remove ../tms-models
    git worktree remove ../tms-views
    git worktree remove ../tms-tests
```

---

## CONTRATOS DE RESULTADO — FORMATO JSON

El orquestador espera que cada agente entregue su resultado en este formato antes de continuar:

```json
{
  "agente": "A_modelos",
  "etapa": "X.X.X",
  "estado": "completado",
  "archivos_creados": ["models/tms_nuevo.py"],
  "archivos_modificados": ["models/__init__.py"],
  "validacion": "python3 -m py_compile OK",
  "campos_exportados": [
    {"nombre": "campo_id", "tipo": "Many2one", "modelo": "res.partner"},
    {"nombre": "monto_total", "tipo": "Monetary", "compute": true}
  ],
  "notas": "Sin duplicados. company_id incluido. 3 constrains."
}
```

El Agente B consume `campos_exportados` del Agente A para generar las vistas correctas.

---

## CUÁNDO NO USAR EL ORQUESTADOR

El orquestador es para etapas medianas o grandes. Para tareas pequeñas, es overkill:

| Tarea | Usar orquestador | Usar directamente |
|---|---|---|
| Nueva etapa completa (modelo + vista + tests) | ✅ | |
| Refactor grande de tms_waybill.py | ✅ | |
| Fix de un bug en un archivo | | ✅ Antigravity |
| Cambio de label en una vista | | ✅ Antigravity |
| Pregunta sobre el código | | ✅ Claude Web |
| Generar SDD | | ✅ Claude Web |

---

*Actualizar este archivo si cambia la estructura del repo o los grupos de seguridad.*
*Última revisión: 2026-03-13*
