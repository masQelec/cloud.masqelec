# Candidato `two-fuse-v1` — manifiesto no operativo

**Repositorio:** `masQelec/cloud.masqelec` · **rama:** `develop` · **creado:** 17-11-2026. Este directorio contiene `manifest.json`, **NO** contiene unidades systemd, clientes instalables ni credenciales.

## Objetivo

Preparar una futura migración *por dispositivo* desde 4 procesos `rclone mount` (películas y series por cada una de dos cuentas OneDrive) a 2 procesos `rclone mount` con 4 bind del kernel. Kodi debe seguir utilizando:

```text
/storage/.mnt/videos/1
/storage/.mnt/videos/2
/storage/.mnt/tvshows/1
/storage/.mnt/tvshows/2
```

La configuración canónica MQC2 y los dos wrappers `crypt` deben seguir siendo compatibles con los CLIENTES legacy. Los datos están cifrados; los nombres, no.

## Qué significa el manifiesto

- `schema=1`, `layout=two-fuse-v1`: formato de propuesta.
- `candidate_id=2026-11-17-two-fuse-v1`: identificador de compatibilidad de ese candidato.
- `update_mode=stage_only`: **solo preparación/ensayo**.
- `activation=operator_only`, `auto_apply=false`, `production_authorized=false`: **NO autorizar instalación**.
- `credential_source=local_mqc2_verified`: las credenciales solo pueden derivarse localmente tras validar el MQC2; este manifiesto no las contiene.
- `legacy_units_unchanged=true`, `stage_artifacts_in_production_systemd=false`: nunca sustituir unidades legacy desde este piloto.

**El addon NO tiene un instalador automático de esta migración.** El manifiesto no significa que la versión del addon se distribuya a todos los CLIENTES.

## Validaciones y estado

- Laboratorio de generación de 2 configuraciones, 2 unidades FUSE y 4 bind **PASS**, sin instalar ni reiniciar servicios (operador).
- Política OAuth v2 en memoria **PASS**; suite última del addon **228/228 OK**.
- Faltan: preflight GitHub SHA/MQC2, FUSE/bind reales con rutas alternativas, integración OAuth concurrente, mecanismo de actualización del addon CLIENTE, cutover y rollback.
- Ninguna bandera activada; ninguna modificación a `system.d`.

## Regla para siguientes cambios

Un nuevo candidato debe usar versión/candidate ID nueva cuando el contrato de migración cambie. No modificar este manifiesto para instalar servicios. Conservar su semántica `stage_only` hasta que exista proceso de release explícito con gates y rollback validados.

Consultar la documentación central del addon: [CLIENT_ROLLOUT.md](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/CLIENT_ROLLOUT.md), [SECURITY_AUDIT.md](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/SECURITY_AUDIT.md), [HANDOFF_2026-11-17.md](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/HANDOFF_2026-11-17.md).
