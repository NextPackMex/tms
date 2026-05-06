# _archive/ — Features completados

Cada feature archivado sigue el patrón: `YYYY-MM-DD-[nombre]/`

## Cómo se archiva

El comando `/archive [nombre]` en Claude Web:
1. Mueve `.spec/[nombre]/` → `.spec/_archive/FECHA-[nombre]/`
2. Agrega sección `## Post-mortem` al PROPOSAL.md archivado
3. Actualiza `STATUS.md` en la raíz → feature marcado COMPLETADO

## Ejemplo de estructura archivada

```
_archive/
└── 2026-05-10-tour-guide/
    ├── PROPOSAL.md          ← incluye post-mortem al final
    ├── REQUIREMENTS.md
    ├── DESIGN.md
    └── CHECKLIST.md         ← con todas las tareas ✅
```

## Features archivados hasta ahora

_(ninguno — estructura recién inicializada 2026-05-04)_
