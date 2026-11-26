# Publicador Tvheadend — cloud.masqelec

Herramienta independiente, Python 3.8+ y Git. No requiere Kodi, rclone ni el checkout del addon. Ejecutar desde el repositorio local `masQelec/cloud.masqelec`, en una rama numérica de Kodi (por ejemplo `21`). El esquema y las comprobaciones del ZIP se basan en `service.cloud.masqelec` commit `4f7eb2fe770462d4771b856b0f9095093d5b6680`.

## Publicar

1. Sin cambios locales, sincronizar la rama: `git switch 21 && git pull --ff-only origin 21`.
2. Copiar ZIP originales a `pvr/tvheadend/Amlogic-ng.arm/` o `pvr/tvheadend/Amlogic-ne.aarch64/`. El nombre debe ser `service.tvheadend43-X.Y.Z.zip`.
3. Probar físicamente la compilación en cada build de CoreELEC que se desea autorizar. Consultar `VERSION_ID` y `VERSION` de `/etc/os-release` en el dispositivo. La aprobación es una declaración del operador, no una prueba física ejecutada por esta herramienta.
4. Ejemplo (versiones y build de ejemplo; sustituir por los reales):

```sh
python3 -B tools/update_tvheadend/update_tvheadend.py --dry-run \
  --approve Amlogic-ng.arm 21.2.9 21.2.5 21.2.5-Omega_devel_20250919152246
```

Si es correcto, ejecutar sin `--dry-run`. **Se publica automáticamente**, sin confirmación adicional:

```sh
python3 -B tools/update_tvheadend/update_tvheadend.py \
  --approve Amlogic-ng.arm 21.2.9 21.2.5 21.2.5-Omega_devel_20250919152246
```

Repetir `--approve TARGET TVH_VERSION VERSION_ID BUILD` en la misma ejecución para varias arquitecturas o builds. La autorización se guarda en `compatibility.json` vinculada al SHA256 exacto del ZIP seleccionado. No se hereda la autorización de un release anterior. No editar ese archivo a mano en el flujo normal. Sin argumentos, el programa usa las autorizaciones ya registradas y publica solo si existen cambios válidos y autorizados.

## Comportamiento y seguridad

- Una entrada por arquitectura en `pvr/tvheadend/manifest.json`. Selección numérica de la versión más alta, no alfabética. Si no hay ZIP ni manifiesto, no hace nada.
- Rechaza downgrade, reemplazo de una misma versión con bytes distintos, nombres inválidos, ZIP corruptos, metadatos/ELF incompatibles y builds sin autorización explícita. No elimina una arquitectura del manifiesto automáticamente.
- Los ZIP antiguos se conservan por defecto. Si el operador elimina ZIP antiguos, acepta sus bajas únicamente junto a una versión superior autorizada de la misma arquitectura. El historial Git conserva los bytes anteriores. ZIP nuevos de menor versión que el seleccionado no se incorporan al commit.
- Bloquea cambios ajenos, cambios ya staged y diferencias entre HEAD y la rama remota. Solo publica ZIP seleccionados, bajas elegibles, manifiesto y registro de autorizaciones. Verifica hashes de los blobs del índice y del commit antes de hacer push. No fuerza push ni actualiza otras ramas.
- `--dry-run` no escribe, ni crea commit, ni consulta la rama remota. El modo normal consulta la punta remota y vuelve a comprobarla antes de publicar. No publicar simultáneamente desde dos procesos de este repositorio; el MASTER puede avanzar la rama con su mantenimiento habitual, provocando un rechazo seguro.
- Ante un error después de escribir o preparar archivos, o ante push rechazado, conserva los cambios/commit local para revisión. No ejecuta reset ni rebase automáticamente. Revisar `git status`, `git log` y `git ls-remote origin refs/heads/21` antes de reintentar. Si se ha creado un commit válido y no se ha publicado, sincronizar/revisar manualmente antes de un push; no volver a ejecutar a ciegas.
- Verifica la punta de la rama Git después del push; no confirma la propagación de CDN RAW ni la descarga/instalación real de dispositivos.
- El ZIP debe caber en el límite de 100 MiB del actualizador. No utilizar Git LFS para los ZIP de distribución.

## Pruebas

```sh
python3 -B -m unittest discover -s tools/update_tvheadend -p 'test_*.py' -q
```

Las pruebas usan ZIP sintéticos, ELF sintético y repositorios Git locales temporales. Se comprueban selección, primera publicación, actualización, idempotencia, bloqueo, `--dry-run` y push real contra un remoto local. No ejecutan Tvheadend ni publican en GitHub.
