"""
Meta reklam kreatifleri (Instagram gonderileri dahil).

Graph API'de 'creative' diye bir breakdown yok; dogru yol iki adim:
  1) act_{id}/insights  level=ad   -> reklam bazli harcama/gelir/tiklama
  2) /?ids=<ad_id,...>&fields=creative{...} -> gorsel, aciklama, instagram baglantisi

Kucuk resimler Meta CDN'inde suresi dolan adreslerde duruyor, bu yuzden
bir kez indirilip data/icerik/ altina kaydediliyor ve rapor oradan okuyor.
"""
import os
import json
import time
from collections import defaultdict

import requests
from dotenv import load_dotenv

load_dotenv('.env')

TOKEN = os.getenv('META_LONG_TOKEN')
HESAP = os.getenv('META_AD_ACCOUNT_ID')
SURUM = 'v19.0'
GORSEL_KLASOR = os.path.join('data', 'icerik')
YIGIN = 50  # tek istekte sorgulanacak reklam sayisi

def _get(url, **kwargs):
    """Gecici ag hatalarinda birkac kez yeniden dener."""
    import time as _time
    son_hata = None
    for deneme in range(4):
        try:
            r = requests.get(url, timeout=kwargs.pop('timeout', 120), **kwargs)
            if r.status_code == 429:
                _time.sleep(2 + deneme * 2)
                continue
            return r
        except Exception as e:
            son_hata = e
            _time.sleep(1.5 * (deneme + 1))
    raise son_hata




def _istek(yol, params, timeout=120):
    r = _get(f"https://graph.facebook.com/{SURUM}/{yol}", params=params, timeout=timeout)
    veri = r.json()
    if isinstance(veri, dict) and "error" in veri:
        raise RuntimeError(f"Meta hata: {veri['error'].get('message')}")
    return veri


def reklam_metrikleri(baslangic, bitis):
    """Gun x reklam kiriliminda harcama/gelir/tiklama/gosterim."""
    gunluk = defaultdict(lambda: defaultdict(lambda: {"spend": 0.0, "gelir": 0.0, "clicks": 0, "impr": 0}))

    url = f"https://graph.facebook.com/{SURUM}/act_{HESAP}/insights"
    params = {
        "access_token": TOKEN,
        "time_range": json.dumps({"since": str(baslangic), "until": str(bitis)}),
        "time_increment": 1,
        "level": "ad",
        "fields": "ad_id,ad_name,spend,clicks,impressions,action_values",
        "limit": 500,
    }

    while True:
        r = _get(url, params=params, timeout=180)
        veri = r.json()
        if "error" in veri:
            raise RuntimeError(f"Meta hata: {veri['error'].get('message')}")

        for d in veri.get("data", []):
            harcama = float(d.get("spend", 0))
            if harcama <= 0:
                continue
            gelir = 0.0
            for a in d.get("action_values", []) or []:
                if a["action_type"] == "purchase":
                    gelir = float(a["value"])
            k = gunluk[d.get("date_start")][d.get("ad_id")]
            k["spend"] += harcama
            k["gelir"] += gelir
            k["clicks"] += int(d.get("clicks", 0))
            k["impr"] += int(d.get("impressions", 0))
            k["ad_name"] = d.get("ad_name", "")

        sonraki = (veri.get("paging") or {}).get("next")
        if not sonraki:
            break
        url, params = sonraki, {}

    return gunluk


def kreatif_bilgileri(reklam_idleri):
    """Reklam id -> kreatif (gorsel adresi, aciklama, instagram baglantisi)."""
    sonuc = {}
    idler = list(reklam_idleri)
    alanlar = ("creative{id,name,body,title,thumbnail_url,image_url,object_story_id,"
               "effective_object_story_id,instagram_permalink_url,effective_instagram_media_id,"
               "object_story_spec,asset_feed_spec}")
    for i in range(0, len(idler), YIGIN):
        parca = idler[i:i + YIGIN]
        veri = _istek("", {"access_token": TOKEN, "ids": ",".join(parca), "fields": alanlar})
        for ad_id, govde in (veri or {}).items():
            k = (govde or {}).get("creative") or {}
            if not k:
                continue
            sonuc[ad_id] = {
                "cid": k.get("id"),
                "aciklama": _aciklama_bul(k),
                "gorsel_url": k.get("image_url") or k.get("thumbnail_url") or "",
                "permalink": k.get("instagram_permalink_url", ""),
                "ig": bool(k.get("instagram_permalink_url") or k.get("effective_instagram_media_id")),
            }
        time.sleep(0.2)
    return sonuc


def _aciklama_bul(k):
    """Gonderi aciklamasini bulunabilecek yerlerden sirayla dener."""
    if k.get("body"):
        return k["body"]
    spec = k.get("object_story_spec") or {}
    for anahtar in ("link_data", "video_data", "photo_data"):
        alt = spec.get(anahtar) or {}
        if alt.get("message"):
            return alt["message"]
        if alt.get("name"):
            return alt["name"]
    feed = k.get("asset_feed_spec") or {}
    metinler = feed.get("bodies") or []
    if metinler and metinler[0].get("text"):
        return metinler[0]["text"]
    return k.get("title") or k.get("name") or ""


def gorsel_indir(cid, url):
    """Kucuk resmi bir kez indirip repoya kaydeder, geri donen yol rapora yazilir."""
    if not url or not cid:
        return ""
    os.makedirs(GORSEL_KLASOR, exist_ok=True)
    hedef = os.path.join(GORSEL_KLASOR, f"{cid}.jpg")
    if os.path.exists(hedef) and os.path.getsize(hedef) > 0:
        return f"icerik/{cid}.jpg"
    try:
        r = _get(url, timeout=60)
        if r.status_code == 200 and r.content:
            with open(hedef, 'wb') as f:
                f.write(r.content)
            return f"icerik/{cid}.jpg"
    except Exception as e:
        print(f"    gorsel indirilemedi ({cid}): {e}")
    return ""


def gunluk_icerik(baslangic, bitis, gun_basi_limit=10):
    """
    Bir tarih araligi icin:
      gunler   -> {gun: [[cid, harcama, gelir, tiklama, gosterim], ...]}
      icerikler-> {cid: {aciklama, gorsel, permalink, ig}}
    """
    metrikler = reklam_metrikleri(baslangic, bitis)
    tum_reklamlar = set()
    for gun in metrikler.values():
        tum_reklamlar.update(gun.keys())
    if not tum_reklamlar:
        return {}, {}

    print(f"    {len(tum_reklamlar)} reklam icin kreatif bilgisi cekiliyor...", flush=True)
    kreatifler = kreatif_bilgileri(tum_reklamlar)

    icerikler = {}
    gunler = {}
    for gun, reklamlar in metrikler.items():
        toplam = defaultdict(lambda: [0.0, 0.0, 0, 0])
        for ad_id, m in reklamlar.items():
            k = kreatifler.get(ad_id)
            if not k or not k.get("cid"):
                continue
            cid = k["cid"]
            t = toplam[cid]
            t[0] += m["spend"]; t[1] += m["gelir"]; t[2] += m["clicks"]; t[3] += m["impr"]
            if cid not in icerikler:
                icerikler[cid] = {
                    "aciklama": (k["aciklama"] or "")[:300],
                    "gorsel": gorsel_indir(cid, k["gorsel_url"]),
                    "permalink": k["permalink"],
                    "ig": k["ig"],
                }
        sirali = sorted(toplam.items(), key=lambda x: x[1][0], reverse=True)[:gun_basi_limit]
        gunler[gun] = [[cid, round(v[0], 2), round(v[1], 2), v[2], v[3]] for cid, v in sirali]

    return gunler, icerikler


if __name__ == "__main__":
    import sys
    from datetime import date, timedelta
    gun = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    bit = date.today() - timedelta(days=1)
    bas = bit - timedelta(days=gun - 1)
    print(f"Test araligi: {bas} -> {bit}")
    g, i = gunluk_icerik(bas, bit)
    print(f"\n{len(g)} gun, {len(i)} farkli icerik")
    for cid, bilgi in list(i.items())[:5]:
        print(f"  {cid} | ig={bilgi['ig']} | gorsel={bilgi['gorsel'] or 'YOK'}")
        print(f"     {bilgi['aciklama'][:90]}")
