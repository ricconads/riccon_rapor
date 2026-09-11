"""
Gunluk arsiv: her gunun ozetini data/gunluk.json icinde tutar.
Ilk calistirmada gecmisi doldurur, sonraki calistirmalarda sadece eksik gunleri ekler.

Kullanim:
    python3 scripts/arsiv.py            -> eksik gunleri tamamla (varsayilan 365 gun geriye)
    python3 scripts/arsiv.py --gun 30   -> son 30 gunu kapsayacak sekilde tamamla
    python3 scripts/arsiv.py --yenile   -> kapsamdaki tum gunleri yeniden cek
"""
import sys
import os
import json
import re
import time
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, date, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from dotenv import load_dotenv

load_dotenv('.env')

TZ_OFFSET = int(os.environ.get("TZ_OFFSET", "3"))
TR = timezone(timedelta(hours=TZ_OFFSET))

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


ARSIV_YOLU = os.path.join('data', 'gunluk.json')

URUN_LIMIT = 30
REKLAM_LIMIT = 10

META_TOKEN = os.getenv('META_LONG_TOKEN')
META_ACCOUNT = os.getenv('META_AD_ACCOUNT_ID')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
SHOPIFY_STORE = os.getenv('SHOPIFY_STORE')


def bugun():
    return (datetime.utcnow() + timedelta(hours=TZ_OFFSET)).date()


def gun_araligi(baslangic, bitis):
    g = baslangic
    while g <= bitis:
        yield g
        g += timedelta(days=1)


def bos_gun():
    return {
        "meta": {"spend": 0.0, "clicks": 0, "impr": 0, "purch": 0, "pval": 0.0},
        "google": {"spend": 0.0, "clicks": 0, "impr": 0, "conv": 0.0, "cval": 0.0},
        "shopify": {"orders": 0, "gross": 0.0, "hourly": [[0, 0.0] for _ in range(24)], "products": []},
        "meta_ads": [],
        "google_ads": [],
        "icerik": [],
    }


# ---------------------------------------------------------------- META
def meta_gunluk(baslangic, bitis):
    """Hesap kirilimi: gun -> harcama, tiklama, gosterim, satis"""
    sonuc = {}
    url = f"https://graph.facebook.com/v19.0/act_{META_ACCOUNT}/insights"
    params = {
        "access_token": META_TOKEN,
        "time_range": json.dumps({"since": str(baslangic), "until": str(bitis)}),
        "time_increment": 1,
        "level": "account",
        "fields": "spend,clicks,impressions,actions,action_values",
        "limit": 500,
    }
    while True:
        r = _get(url, params=params, timeout=120)
        veri = r.json()
        if "error" in veri:
            raise RuntimeError(f"Meta hata: {veri['error'].get('message')}")
        for d in veri.get("data", []):
            gun = d.get("date_start")
            purch, pval = 0, 0.0
            for a in d.get("actions", []) or []:
                if a["action_type"] == "purchase":
                    purch = int(float(a["value"]))
            for a in d.get("action_values", []) or []:
                if a["action_type"] == "purchase":
                    pval = float(a["value"])
            sonuc[gun] = {
                "spend": round(float(d.get("spend", 0)), 2),
                "clicks": int(d.get("clicks", 0)),
                "impr": int(d.get("impressions", 0)),
                "purch": purch,
                "pval": round(pval, 2),
            }
        sonraki = (veri.get("paging") or {}).get("next")
        if not sonraki:
            break
        url, params = sonraki, {}
    return sonuc


def meta_reklam_gunluk(baslangic, bitis):
    """Reklam kirilimi: gun -> [[ad_name, spend, purchase_value], ...]"""
    toplam = defaultdict(list)
    url = f"https://graph.facebook.com/v19.0/act_{META_ACCOUNT}/insights"
    params = {
        "access_token": META_TOKEN,
        "time_range": json.dumps({"since": str(baslangic), "until": str(bitis)}),
        "time_increment": 1,
        "level": "ad",
        "fields": "ad_name,spend,action_values",
        "limit": 500,
    }
    while True:
        r = _get(url, params=params, timeout=180)
        veri = r.json()
        if "error" in veri:
            raise RuntimeError(f"Meta reklam hata: {veri['error'].get('message')}")
        for d in veri.get("data", []):
            harcama = float(d.get("spend", 0))
            if harcama <= 0:
                continue
            pval = 0.0
            for a in d.get("action_values", []) or []:
                if a["action_type"] == "purchase":
                    pval = float(a["value"])
            toplam[d.get("date_start")].append([d.get("ad_name", ""), round(harcama, 2), round(pval, 2)])
        sonraki = (veri.get("paging") or {}).get("next")
        if not sonraki:
            break
        url, params = sonraki, {}
    for gun in toplam:
        toplam[gun].sort(key=lambda x: x[1], reverse=True)
        toplam[gun] = toplam[gun][:REKLAM_LIMIT]
    return dict(toplam)


# ---------------------------------------------------------------- GOOGLE
def _google_client():
    from google.ads.googleads.client import GoogleAdsClient
    return GoogleAdsClient.load_from_storage('google-ads.yaml')


def google_gunluk(client, musteri_id, baslangic, bitis):
    servis = client.get_service("GoogleAdsService")
    sorgu = f"""
        SELECT segments.date, metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.conversions, metrics.conversions_value
        FROM customer
        WHERE segments.date BETWEEN '{baslangic}' AND '{bitis}'
    """
    sonuc = {}
    for row in servis.search(customer_id=musteri_id, query=sorgu):
        gun = row.segments.date
        sonuc[gun] = {
            "spend": round(row.metrics.cost_micros / 1_000_000, 2),
            "clicks": int(row.metrics.clicks),
            "impr": int(row.metrics.impressions),
            "conv": round(row.metrics.conversions, 2),
            "cval": round(row.metrics.conversions_value, 2),
        }
    return sonuc


def google_reklam_gunluk(client, musteri_id, baslangic, bitis):
    servis = client.get_service("GoogleAdsService")
    sorgu = f"""
        SELECT segments.date, ad_group_ad.ad.name, campaign.name,
               metrics.cost_micros, metrics.conversions_value
        FROM ad_group_ad
        WHERE segments.date BETWEEN '{baslangic}' AND '{bitis}'
        AND metrics.cost_micros > 0
    """
    toplam = defaultdict(list)
    for row in servis.search(customer_id=musteri_id, query=sorgu):
        harcama = row.metrics.cost_micros / 1_000_000
        ad = row.ad_group_ad.ad.name or row.campaign.name
        toplam[row.segments.date].append([ad, round(harcama, 2), round(row.metrics.conversions_value, 2)])
    for gun in toplam:
        toplam[gun].sort(key=lambda x: x[1], reverse=True)
        toplam[gun] = toplam[gun][:REKLAM_LIMIT]
    return dict(toplam)


# ---------------------------------------------------------------- SHOPIFY
def _sonraki_url(link_header):
    if not link_header:
        return None
    for parca in link_header.split(','):
        if 'rel="next"' in parca:
            m = re.search(r'<([^>]+)>', parca)
            if m:
                return m.group(1)
    return None


def shopify_gunluk(baslangic, bitis):
    """Siparisleri bir kez cekip gunlere bolustur."""
    basla_utc = (datetime.strptime(str(baslangic), '%Y-%m-%d') - timedelta(hours=TZ_OFFSET)).strftime('%Y-%m-%dT%H:%M:%SZ')
    bit_utc = (datetime.strptime(str(bitis), '%Y-%m-%d') + timedelta(hours=24 - TZ_OFFSET) - timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

    url = f"https://{SHOPIFY_STORE}/admin/api/2024-01/orders.json"
    params = {
        "status": "any",
        "created_at_min": basla_utc,
        "created_at_max": bit_utc,
        "limit": 250,
        "fields": "subtotal_price,total_discounts,line_items,created_at",
    }
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}

    gunler = defaultdict(lambda: {
        "orders": 0,
        "gross": 0.0,
        "hourly": [[0, 0.0] for _ in range(24)],
        "urunler": defaultdict(float),
    })

    sayfa = 0
    while True:
        r = _get(url, headers=headers, params=params, timeout=120)
        veri = r.json()
        siparisler = veri.get('orders', [])
        sayfa += 1
        if sayfa % 10 == 0:
            print(f"    ...shopify sayfa {sayfa}", flush=True)
        for o in siparisler:
            zaman = datetime.strptime(o['created_at'], '%Y-%m-%dT%H:%M:%S%z').astimezone(TR)
            gun = zaman.date().isoformat()
            brut = float(o.get('subtotal_price', 0)) - float(o.get('total_discounts', 0))
            g = gunler[gun]
            g["orders"] += 1
            g["gross"] += brut
            g["hourly"][zaman.hour][0] += 1
            g["hourly"][zaman.hour][1] += brut
            for item in o.get('line_items', []) or []:
                g["urunler"][item.get('title', '')] += float(item.get('price', 0)) * int(item.get('quantity', 0))
        sonraki = _sonraki_url(r.headers.get('Link', ''))
        if not sonraki:
            break
        url, params = sonraki, {}

    sonuc = {}
    for gun, g in gunler.items():
        urunler = sorted(g["urunler"].items(), key=lambda x: x[1], reverse=True)[:URUN_LIMIT]
        sonuc[gun] = {
            "orders": g["orders"],
            "gross": round(g["gross"], 2),
            "hourly": [[c, round(v, 2)] for c, v in g["hourly"]],
            "products": [[ad, round(tutar, 2)] for ad, tutar in urunler],
        }
    return sonuc


# ---------------------------------------------------------------- ARSIV
def arsiv_yukle():
    if os.path.exists(ARSIV_YOLU):
        with open(ARSIV_YOLU, 'r', encoding='utf-8') as f:
            arsiv = json.load(f)
        arsiv.setdefault("icerikler", {})
        return arsiv
    return {"guncelleme": None, "gunler": {}, "icerikler": {}}


def arsiv_kaydet(arsiv):
    os.makedirs(os.path.dirname(ARSIV_YOLU), exist_ok=True)
    arsiv["guncelleme"] = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    with open(ARSIV_YOLU, 'w', encoding='utf-8') as f:
        json.dump(arsiv, f, ensure_ascii=False, separators=(',', ':'))


def guncelle(gun_sayisi=365, yenile=False, parca=30, kaynaklar=("meta", "google", "shopify")):
    arsiv = arsiv_yukle()
    gunler = arsiv["gunler"]
    icerikler = arsiv.setdefault("icerikler", {})

    son = bugun() - timedelta(days=1)
    ilk = son - timedelta(days=gun_sayisi - 1)

    def gun_eksik(g):
        kayit = gunler.get(g.isoformat())
        if not kayit:
            return True
        return any(k not in kayit for k in kaynaklar if k in ("meta", "google", "shopify"))

    eksik = [g for g in gun_araligi(ilk, son) if yenile or gun_eksik(g)]
    if not eksik:
        print("Arsiv guncel, eklenecek gun yok.")
        return arsiv

    print(f"{len(eksik)} gun cekilecek: {eksik[0]} -> {eksik[-1]}")

    google_client = _google_client() if "google" in kaynaklar else None
    google_musteri = os.getenv('GOOGLE_CUSTOMER_ID', '7145021056').replace('-', '')

    # eksik gunleri bloklara bol (ardisik olmayanlar da olabilir)
    bloklar = []
    blok = [eksik[0]]
    for g in eksik[1:]:
        if (g - blok[-1]).days == 1 and len(blok) < parca:
            blok.append(g)
        else:
            bloklar.append(blok)
            blok = [g]
    bloklar.append(blok)

    for i, blok in enumerate(bloklar, 1):
        b, s = blok[0], blok[-1]
        print(f"[{i}/{len(bloklar)}] {b} -> {s}", flush=True)

        m, m_ads, g_, g_ads, sh = {}, {}, {}, {}, {}
        icerik_gun = {}
        if "meta" in kaynaklar:
            print("  meta...", flush=True)
            m = meta_gunluk(b, s)
            m_ads = meta_reklam_gunluk(b, s)
            print("  meta icerikleri...", flush=True)
            try:
                from meta_icerik import gunluk_icerik
                icerik_gun, yeni_icerikler = gunluk_icerik(b, s)
                icerikler.update(yeni_icerikler)
            except Exception as hata:
                print(f"    icerik cekilemedi: {hata}")
        if "google" in kaynaklar:
            print("  google...", flush=True)
            g_ = google_gunluk(google_client, google_musteri, b, s)
            g_ads = google_reklam_gunluk(google_client, google_musteri, b, s)
        if "shopify" in kaynaklar:
            print("  shopify...", flush=True)
            sh = shopify_gunluk(b, s)

        for gun in blok:
            k = gun.isoformat()
            kayit = gunler.get(k) or bos_gun()
            if "meta" in kaynaklar:
                kayit["meta"] = m.get(k, bos_gun()["meta"])
                kayit["meta_ads"] = m_ads.get(k, [])
                kayit["icerik"] = icerik_gun.get(k, [])
            if "google" in kaynaklar:
                kayit["google"] = g_.get(k, bos_gun()["google"])
                kayit["google_ads"] = g_ads.get(k, [])
            if "shopify" in kaynaklar:
                kayit["shopify"] = sh.get(k, bos_gun()["shopify"])
            gunler[k] = kayit

        arsiv_kaydet(arsiv)
        print(f"  kaydedildi (toplam {len(gunler)} gun)", flush=True)

    return arsiv


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--gun', type=int, default=365)
    p.add_argument('--yenile', action='store_true')
    p.add_argument('--parca', type=int, default=30)
    p.add_argument('--kaynak', default='meta,google,shopify',
                   help='virgulle ayrilmis: meta,google,shopify')
    a = p.parse_args()
    guncelle(gun_sayisi=a.gun, yenile=a.yenile, parca=a.parca,
             kaynaklar=tuple(k.strip() for k in a.kaynak.split(',') if k.strip()))
