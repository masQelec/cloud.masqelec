# cloud.masqelec — datos y configuración de Cloud masQelec

Repositorio de configuración y artefactos consumidos por el addon **[service.cloud.masqelec](https://github.com/masQelec/service.cloud.masqelec)** en Kodi/KodiELEC. **No es el repositorio del código del addon.**

> **Aviso operativo (17-11-2026):** este repositorio contiene archivos que el addon de los dispositivos puede consultar **durante el arranque**. Un cambio en `develop/system.d/` puede provocar sustitución de unidades systemd y `try-restart`. No utilizar esa ruta para distribuir el piloto 2 FUSE + 4 bind.

## Estructura de `develop`

| Ruta | Contenido / consumidor | Precaución |
| --- | --- | --- |
| `rclone/rclone.conf.crypt` | Configuración rclone canónica cifrada con MQC2, autenticada | No sustituir sin un protocolo seguro de OAuth y versionado |
| `system.d/` | Cuatro unidades `rclone mount` legacy + `zerotier.service` | `lib/cloud_storage.py` puede descargarlas y reiniciarlas si cambian |
| `catalog/catalog.zip` y `catalog/catalog.version` | Publicación y descarga de catálogo `.strm` | Actualización con integridad/versionado |
| `userdata/database.master/` | BD Kodi MyVideos para MASTER | No reemplazar BD sin las validaciones del addon |
| `userdata/database.client/` | BD Kodi MyVideos para CLIENTES | No sustituir BD mientras Kodi la tenga abierta |
| `pvr/playlist.m3u` y `pvr/tv_grab_file` | Playlist y grabber PVR/Tvheadend | Pueden incluir información de acceso; no reproducir su contenido en incidencias |
| `rollouts/rclone-two-mount/v1/manifest.json` | **Solo metadatos de candidato de migración** | `stage_only` / `auto_apply=false` / `production_authorized=false` |

**Ramas:**
- `develop`: entorno actual de trabajo del addon en pruebas y manifiesto no operativo.
- `master`: configuración estable; no modificar durante este piloto.
- En el repo del addon, la rama estable se llama **`main`**. El término **MASTER** (rol de equipo) no guarda relación con la rama `master` de este repositorio.

## Montajes legacy vigentes

Las unidades existentes en `system.d` comparten `/storage/.config/rclone/rclone.conf` y usan `crypt` para cifrar datos, manteniendo nombres de archivos sin cifrar. Los destinos de Kodi no pueden cambiar:

```text
rclone_videos_1.service  -> /storage/.mnt/videos/1
rclone_videos_2.service  -> /storage/.mnt/videos/2
rclone_tvshows_1.service -> /storage/.mnt/tvshows/1
rclone_tvshows_2.service -> /storage/.mnt/tvshows/2
```

Cada cuenta OneDrive tiene actualmente dos procesos montados (películas y series) que pueden renovar OAuth en el mismo archivo. El addon `develop` dispone de un **fence** que bloquea sustituciones peligrosas de `rclone.conf` mientras existen escritores activos; **la sincronización automática continúa desactivada**.

## Piloto de dos montajes (no operativo)

Propuesta en el addon: un `rclone mount` por cuenta a `/storage/.mnt/cloud/1` y `/storage/.mnt/cloud/2`; cuatro `bind` locales mantienen las rutas anteriores. La propuesta se genera en `/tmp` privado, **no** en este repositorio.

Solo se publicó un **manifiesto de fase** en [`rollouts/rclone-two-mount/v1/`](rollouts/rclone-two-mount/v1/README.md). No es un script ni un instalador: no detiene ni inicia montajes, no distribuye tokens y no migra CLIENTES.

La arquitectura v2 debe conservar para CLIENTES antiguos el backup MQC2 **de seis secciones** (dos `crypt`, dos OneDrive, dos Google Drive). No se deben publicar `account1.conf` ni `account2.conf` en claro.

## Flujo de trabajo y cambios permitidos

1. Los cambios del addon se hacen en **`service.cloud.masqelec/develop`**, con pruebas sin Kodi y documentación en [`docs/`](https://github.com/masQelec/service.cloud.masqelec/tree/develop/service.cloud.masqelec/docs).
2. En este repo `cloud/develop`, **solo** actualizar documentos/metadatos del piloto si no cambian configuraciones usadas en vivo.
3. **No modificar** `system.d/`, `rclone/rclone.conf.crypt`, `pvr/`, `userdata/` ni `catalog/` durante las pruebas OAuth v2 sin analizar el efecto en equipos conectados y autorización específica.
4. Para cualquier cambio futuro de servicios, exigir snapshot/rollback, verificación de Kodi inactivo, pruebas en rutas alternativas, gating de versiones y control de actualizaciones de CLIENTES.
5. Ninguna autorización de release se deriva de un manifiesto descargado ni de una suite unitaria aprobada.

### Evidencia a 17-11-2026

El operador confirmó **228/228 pruebas unitarias OK** en el addon y laboratorios de solo lectura **PASS** para concurrencia, dependencias `crypt`, propuesta 2 FUSE+4 bind y política OAuth v2. **Pendiente:** `rclone_two_mount_real_probe_lab.py --preflight` (GitHub blob SHA, MQC2 y comparación de tokens). **No ejecutar `--real-probe` con montajes activos.**

## Documentación de mantenimiento

- [README principal del addon](https://github.com/masQelec/service.cloud.masqelec/blob/develop/README.md)
- [Arquitectura y modos MASTER/CLIENT](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/ARCHITECTURE_AND_MODES.md)
- [Seguridad y auditoría](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/SECURITY_AUDIT.md)
- [CLIENTES: actualizaciones y migración](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/CLIENT_ROLLOUT.md)
- [Pruebas y operaciones](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/OPERATIONS_AND_TESTING.md)
- [Progreso y decisiones](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/ROADMAP_AND_PROGRESS.md)
- [Handoff para otro chat](https://github.com/masQelec/service.cloud.masqelec/blob/develop/service.cloud.masqelec/docs/HANDOFF_2026-11-17.md)

**Estado:** `NO_DEPLOY`, `NO_LIVE_MOUNT_RESTART`, `NO_CREDENTIAL_UPLOAD`. `develop` no concede permiso de despliegue.
