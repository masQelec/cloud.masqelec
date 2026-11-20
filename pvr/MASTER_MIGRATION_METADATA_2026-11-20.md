# IPTV playlist — adopción inicial en master (20-11-2026)

**Rama:** develop. **Estado:** fuente de migración, no certificación de instalación. Los clientes no deben modificar la playlist ni regenerarla desde este documento.

Referencia del contenido `pvr/playlist.m3u` inspeccionado: blob Git SHA `97d728a0bbb0f325e5f8a71faa9a89eeba1fe5d7`.

Inventario sin URLs ni credenciales:
- 720 canales, 26 grupos en orden de primera aparición.
- 720 `CUID` únicos, no necesariamente consecutivos (rango 1–11464).
- 720 `tvh-chnum` y `tvg-chno` únicos y concordantes (1–720).
- 209 `tvg-id` no vacíos, 198 valores distintos, 11 valores repetidos; no utilizar para identidad.
- Vieja generación: 865 entradas, `CUID` posicional. **No comparar directamente CUID de generaciones diferentes como identidad.**

El addon en `masQelec/service.cloud.masqelec:develop` conserva actualmente el mantenimiento histórico. Nueva planificación: lectura M3U estricta y `diff_same_generation` sin borrados autorizados, evidencias de `TV46.db` del master y verificación posterior contra inventarios TVH y Kodi. La discrepancia 865→720 no acredita cuáles son bajas reales.

**No introducir URLs de reproducción ni datos de autenticación en fixtures, logs o PR.** No realizar migración sobre otras unidades antes de verificar master y autorizar publicación.
