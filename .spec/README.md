# .spec/ — Flujo Spec-Driven TMS Hombre Camión

Directorio de especificaciones activas del proyecto.

## Estructura

```
.spec/
├── README.md                        ← este archivo
├── _archive/                        ← features completados
│   ├── README.md
│   └── YYYY-MM-DD-[nombre]/         ← archivados por /archive
│       ├── PROPOSAL.md  (+ post-mortem)
│       ├── REQUIREMENTS.md
│       ├── DESIGN.md
│       └── CHECKLIST.md
└── [nombre-feature]/                ← feature activo (uno a la vez)
    ├── PROPOSAL.md
    ├── REQUIREMENTS.md
    ├── DESIGN.md
    └── CHECKLIST.md
```

## Comandos (desde Claude Web/Desktop)

| Comando | Qué hace |
|---------|----------|
| `/status` | Estado real del proyecto (lee archivos del repo) |
| `/us [descripción]` | Refina historia de usuario → ACs, riesgos, complejidad |
| `/ff [nombre]` | Crea los 4 artefactos en `.spec/[nombre]/` |
| `/apply [nombre]` | Genera prompt exacto para Claude Code terminal |
| `/verify [nombre]` | Valida implementación vs REQUIREMENTS.md |
| `/archive [nombre]` | Mueve a `_archive/FECHA-[nombre]/` + post-mortem |
| `/commit [versión]` | Genera mensaje conventional commit listo para copiar |
| `/correview [nombre]` | Code review checklist TMS antes de merge |
| `/sdd [versión]` | Genera SDD completo + escribe en `docs/` |

## Regla de oro

**Un feature activo a la vez.**
No usar `/ff` hasta que el anterior esté archivado.

## Ciclo completo

```
/ff nombre
  ↓
Claude Code ejecuta CHECKLIST.md
  ↓
/verify nombre  →  ¿pasa? → /archive nombre → /commit X.X.X → PR a main
                         ↘  ¿falla? → fix → /verify de nuevo
```
