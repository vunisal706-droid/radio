"""Comprueba cada día las emisoras de VicRadio y genera emisoras.json.
- Prueba cada dirección: ¿responde y manda audio de verdad?
- Pone primero las que funcionan (respetando tu orden).
- Si una emisora se queda sin ninguna que funcione, busca direcciones nuevas
  en Radio Browser (directorio público de radios).
- Nunca borra direcciones: solo las reordena. Si el servidor de GitHub no
  puede oír casi nada (bloqueo por país), no toca el orden."""
import json, re, ssl, sys, time, urllib.request, urllib.parse, datetime

UA = 'VicRadio/1.0 (comprobador de emisoras)'

# Emisoras y direcciones de la app (mismo orden que en index.html)
EMISORAS = {
  'marca': {'buscar': ['Radio Marca'], 'urls': [
      'https://playerservices.streamtheworld.com/api/livestream-redirect/RADIOMARCA_NACIONAL.mp3',
      'https://25603.live.streamtheworld.com/RADIOMARCA_NACIONAL.mp3',
      'https://playerservices.streamtheworld.com/api/livestream-redirect/RADIOMARCA_NACIONALAAC.aac']},
  'ser': {'buscar': ['SER Granada', 'Radio Granada SER', 'Cadena SER'], 'urls': [
      'https://playerservices.streamtheworld.com/api/livestream-redirect/SER_ASO_GRANADA.mp3',
      'https://playerservices.streamtheworld.com/api/livestream-redirect/SER_ASO_GRANADAAAC.aac',
      'https://playerservices.streamtheworld.com/api/livestream-redirect/CADENASER.mp3']},
  'cope': {'buscar': ['COPE Granada', 'COPE'], 'urls': [
      'https://granada-copesedes-rrcast.flumotion.com/copesedes/granada-low.mp3',
      'https://wecast-bl02.flumotion.com/copesedes/granada.mp3',
      'https://wecast-b02-01.flumotion.com/copesedes/granada.mp3',
      'https://wecast-b02-02.flumotion.com/copesedes/granada.mp3',
      'https://flucast13-h-cloud.flumotion.com/cope/net1.mp3']},
  'canalsur': {'buscar': ['Canal Sur Radio'], 'urls': [
      'https://rtva-live-radio.flumotion.com/rtva/csr.mp3',
      'https://cdnlive.shooowit.net/rtvalive/channel01.isml/index.m3u8']},
  'canalsurgr': {'buscar': ['Canal Sur Radio Granada'], 'urls': [
      'https://rtva-live-radio.flumotion.com/rtva/csrgra.mp3']},
  'ondacero': {'buscar': ['Onda Cero'], 'urls': [
      'https://radio-atres-live.ondacero.es/api/livestream-redirect/OCAAC.aac',
      'https://atres-live.ondacero.es/api/livestream-redirect/OCRAAC.aac',
      'https://icecast-streaming.nice264.com/ondacero']},
}

def prueba(url, segundos=12):
    """True si la dirección manda audio (o una lista HLS válida)."""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Icy-MetaData': '0'})
    try:
        with urllib.request.urlopen(req, timeout=segundos, context=ctx) as r:
            tipo = (r.headers.get('Content-Type') or '').lower()
            t0, datos = time.time(), b''
            while len(datos) < 16000 and time.time() - t0 < segundos:
                trozo = r.read(4096)
                if not trozo:
                    break
                datos += trozo
            if 'mpegurl' in tipo or url.split('?')[0].endswith('.m3u8') or datos.startswith(b'#EXTM3U'):
                return datos.lstrip().startswith(b'#EXTM3U')
            if 'text/html' in tipo:
                return False
            return len(datos) >= 8000   # al menos ~0,5 s de audio
    except Exception as e:
        print(f'    ✗ {url[:70]} → {str(e)[:60]}')
        return False

def radio_browser(nombre):
    """Busca direcciones nuevas en Radio Browser (España, no rotas, más votadas)."""
    q = urllib.parse.urlencode({'name': nombre, 'countrycode': 'ES', 'hidebroken': 'true',
                                'order': 'votes', 'reverse': 'true', 'limit': 8})
    for host in ('de1', 'fi1', 'at1', 'nl1'):
        try:
            req = urllib.request.Request(f'https://{host}.api.radio-browser.info/json/stations/search?{q}', headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read())
            return [x.get('url_resolved') or x.get('url') for x in res
                    if (x.get('url_resolved') or x.get('url', '')).startswith('https://')]
        except Exception:
            continue
    return []

def main():
    anterior = {}
    try:
        anterior = json.load(open('emisoras.json', encoding='utf-8')).get('emisoras', {})
    except Exception:
        pass
    resultado, total, buenas = {}, 0, 0
    for eid, e in EMISORAS.items():
        print(f'· {eid}')
        # direcciones extra encontradas otros días
        extra = [u for u in anterior.get(eid, {}).get('urls', []) if u not in e['urls']]
        urls = e['urls'] + extra
        estado = {}
        for u in urls:
            estado[u] = prueba(u); total += 1; buenas += estado[u]
            print(f'    {"✓" if estado[u] else "✗"} {u[:80]}')
        if not any(estado.values()):
            print('    sin ninguna que funcione → buscando en Radio Browser')
            for nombre in e['buscar']:
                for u in radio_browser(nombre):
                    if u in estado or len(estado) > 12:
                        continue
                    estado[u] = prueba(u)
                    print(f'    {"✓" if estado[u] else "✗"} (nueva) {u[:80]}')
                    if estado[u]:
                        break
                if any(estado.values()):
                    break
        orden = [u for u in estado if estado[u]] + [u for u in estado if not estado[u]]
        # solo se guardan como extra las nuevas que funcionan
        orden = [u for u in orden if u in urls or estado[u]]
        resultado[eid] = {'urls': orden, 'ok': [u for u in orden if estado.get(u)]}
    fiable = total and buenas / total >= 0.3
    if not fiable:
        print(f'Solo {buenas}/{total} direcciones responden: parece un bloqueo del servidor de GitHub. No se cambia nada.')
        return
    with open('emisoras.json', 'w', encoding='utf-8') as f:
        json.dump({'comprobado': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes'),
                   'emisoras': resultado}, f, ensure_ascii=False, indent=1)
    print(f'emisoras.json: {buenas}/{total} direcciones funcionan')

if __name__ == '__main__':
    main()
