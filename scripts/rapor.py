import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meta_rapor import get_all_data as get_meta
from google_rapor import get_all_data as get_google
from shopify_rapor import get_shopify_data
from dotenv import load_dotenv
from datetime import datetime

load_dotenv('.env')

META_PERIODS = {
    "yesterday": "yesterday",
    "last_7d": "last_7d",
    "last_30d": "last_30d",
    "this_month": "this_month"
}

GOOGLE_PERIODS = {
    "yesterday": "YESTERDAY",
    "last_7d": "LAST_7_DAYS",
    "last_30d": "LAST_30_DAYS",
    "this_month": "THIS_MONTH"
}


# ---------------------------------------------------------------- karsilastirma
def tr_sayi(x, ondalik=2):
    """1234.5 -> 1.234,50"""
    metin = f"{x:,.{ondalik}f}"
    return metin.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def donem_araligi(period, tz=3):
    """Rapordaki donemin gun araligi (Shopify ile ayni mantik)."""
    from datetime import datetime as _d, timedelta as _t
    bugun = (_d.utcnow() + _t(hours=tz)).date()
    if period == "yesterday":
        return bugun - _t(days=1), bugun - _t(days=1)
    if period == "last_7d":
        return bugun - _t(days=7), bugun - _t(days=1)
    if period == "last_30d":
        return bugun - _t(days=30), bugun - _t(days=1)
    if period == "this_month":
        return bugun.replace(day=1), bugun - _t(days=1)
    return bugun - _t(days=1), bugun - _t(days=1)


def onceki_aralik(bas, bit):
    """Ayni uzunlukta, hemen oncesindeki aralik."""
    from datetime import timedelta as _t
    gun = (bit - bas).days + 1
    return bas - _t(days=gun), bas - _t(days=1)


def arsiv_topla(gunler, bas, bit):
    """Arsivden bir aralik icin toplam degerleri cikar."""
    from datetime import timedelta as _t
    t = {
        "meta_spend": 0.0, "meta_clicks": 0, "meta_impr": 0, "meta_purch": 0, "meta_pval": 0.0,
        "g_spend": 0.0, "g_clicks": 0, "g_impr": 0, "g_conv": 0.0, "g_cval": 0.0,
        "orders": 0, "gross": 0.0, "gun": 0,
    }
    g = bas
    while g <= bit:
        kayit = gunler.get(g.isoformat())
        if kayit:
            t["gun"] += 1
            m = kayit.get("meta", {})
            t["meta_spend"] += m.get("spend", 0); t["meta_clicks"] += m.get("clicks", 0)
            t["meta_impr"] += m.get("impr", 0); t["meta_purch"] += m.get("purch", 0)
            t["meta_pval"] += m.get("pval", 0)
            gg = kayit.get("google", {})
            t["g_spend"] += gg.get("spend", 0); t["g_clicks"] += gg.get("clicks", 0)
            t["g_impr"] += gg.get("impr", 0); t["g_conv"] += gg.get("conv", 0)
            t["g_cval"] += gg.get("cval", 0)
            sh = kayit.get("shopify", {})
            t["orders"] += sh.get("orders", 0); t["gross"] += sh.get("gross", 0)
        g += _t(days=1)

    def b(a, c):
        return a / c if c else 0

    t["meta_roas"] = b(t["meta_pval"], t["meta_spend"])
    t["meta_ctr"] = b(t["meta_clicks"], t["meta_impr"]) * 100
    t["meta_cpc"] = b(t["meta_spend"], t["meta_clicks"])
    t["meta_cpm"] = b(t["meta_spend"], t["meta_impr"]) * 1000
    t["g_roas"] = b(t["g_cval"], t["g_spend"])
    t["g_ctr"] = b(t["g_clicks"], t["g_impr"]) * 100
    t["g_tbm"] = b(t["g_spend"], t["g_clicks"])
    t["g_bgbm"] = b(t["g_spend"], t["g_impr"]) * 1000
    t["toplam_spend"] = t["meta_spend"] + t["g_spend"]
    t["toplam_roas"] = b(t["gross"], t["toplam_spend"])
    t["aov"] = b(t["gross"], t["orders"])
    return t


def fark(yeni, eski, ters=False, notr=False, bicim=None, sinif="mc-change"):
    """Onceki doneme gore degisim rozeti."""
    if eski is None or eski == 0:
        return f'<div class="{sinif} neutral" title="Önceki dönemde veri yok">—</div>'
    degisim = (yeni - eski) / abs(eski) * 100
    if abs(degisim) < 0.05:
        ipucu0 = f"Önceki dönem: {bicim(eski)}" if bicim else ""
        return f'<div class="{sinif} neutral" title="{ipucu0}">%0,0</div>'
    ok = "▲" if degisim > 0 else "▼"
    if notr:
        renk = "neutral"
    else:
        iyi = degisim > 0
        if ters:
            iyi = not iyi
        renk = "up" if iyi else "down"
    ipucu = f"Önceki dönem: {bicim(eski)}" if bicim else ""
    return f'<div class="{sinif} {renk}" title="{ipucu}">{ok} %{tr_sayi(abs(degisim), 1)}</div>'


def para(x):
    return "₺" + tr_sayi(x)


def adet(x):
    return tr_sayi(x, 0)


def carpan(x):
    return tr_sayi(x, 2) + "x"


def yuzde(x):
    return "%" + tr_sayi(x, 2)


def arsiv_icerik(gunler, icerikler, bas, bit, limit=10):
    """Arsivden bir aralik icin en iyi performansli icerikleri cikar."""
    from datetime import timedelta as _t
    toplam = {}
    g = bas
    while g <= bit:
        kayit = gunler.get(g.isoformat())
        if kayit:
            for satir in kayit.get("icerik", []) or []:
                cid, harcama, gelir, tiklama, gosterim = satir
                t = toplam.setdefault(cid, [0.0, 0.0, 0, 0])
                t[0] += harcama
                t[1] += gelir
                t[2] += tiklama
                t[3] += gosterim
        g += _t(days=1)

    liste = []
    for cid, (harcama, gelir, tiklama, gosterim) in toplam.items():
        if harcama <= 0:
            continue
        bilgi = icerikler.get(cid, {})
        liste.append({
            "cid": cid,
            "aciklama": bilgi.get("aciklama", ""),
            "gorsel": bilgi.get("gorsel", ""),
            "permalink": bilgi.get("permalink", ""),
            "ig": bilgi.get("ig", False),
            "harcama": round(harcama, 2),
            "gelir": round(gelir, 2),
            "roas": round(gelir / harcama, 2),
            "ctr": round(tiklama / gosterim * 100, 2) if gosterim else 0,
        })

    instagram = [i for i in liste if i["ig"]]
    kaynak = "instagram" if instagram else "tumu"
    secilen = instagram if instagram else liste
    secilen.sort(key=lambda x: x["roas"], reverse=True)
    return secilen[:limit], kaynak


def icerik_bloku(icerik_listesi, kaynak):
    """En iyi performansli icerikler bolumunun HTML'i."""
    from html import escape as _esc

    if not icerik_listesi:
        govde = ('<div class="bos">Bu dönem için içerik verisi yok. '
                 'Meta bağlantısı kurulduktan sonra burası dolacak.</div>')
        sayi_metni = ''
    else:
        satirlar = []
        for i, ic in enumerate(icerik_listesi, 1):
            aciklama = _esc(ic["aciklama"] or "Açıklama yok")
            if ic["gorsel"]:
                gorsel = '<img src="%s" alt="" loading="lazy">' % _esc(ic["gorsel"])
            else:
                gorsel = '<div class="ic-yok">görsel<br>yok</div>'
            if ic["permalink"]:
                baglanti = ('<a class="ic-link" href="%s" target="_blank" rel="noopener">'
                            'Instagram\'da aç ↗</a>') % _esc(ic["permalink"])
            else:
                baglanti = ''
            satirlar.append(
                '<div class="icerik-satir">'
                '<div class="ic-rank">%d</div>'
                '<div class="ic-gorsel">%s</div>'
                '<div class="ic-metin"><div class="ic-aciklama" title="%s">%s</div>%s</div>'
                '<div class="ic-metrik"><span>Harcama</span><b>₺%s</b></div>'
                '<div class="ic-metrik"><span>Gelir</span><b>₺%s</b></div>'
                '<div class="ic-metrik vurgu"><span>ROAS</span><b>%sx</b></div>'
                '<div class="ic-metrik"><span>Tıklama Oranı</span><b>%%%s</b></div>'
                '</div>' % (i, gorsel, aciklama, aciklama, baglanti,
                            tr_sayi(ic["harcama"]), tr_sayi(ic["gelir"]),
                            tr_sayi(ic["roas"]), tr_sayi(ic["ctr"]))
            )
        govde = ''.join(satirlar)
        sayi_metni = ('<span class="cc-count">%d gönderi · ROAS\'a göre sıralı</span>'
                      % len(icerik_listesi))

    uyari = ''
    if icerik_listesi and kaynak == "tumu":
        uyari = ('<div class="ic-uyari">Instagram kaynaklı gönderi bulunamadı; '
                 'tüm reklam kreatifleri listeleniyor.</div>')

    return ('  <div class="plabel">Meta Ads — En iyi performanslı içerikler</div>\n'
            '  <div class="chart-card full icerik-kart" data-ico="reklam">\n'
            '    <div class="cc-title"><span>En iyi performanslı içerikler</span>%s</div>\n'
            '    %s\n'
            '    <div class="icerik-liste">%s</div>\n'
            '  </div>' % (sayi_metni, uyari, govde))


def build_period_html(period, m, g, s, onceki=None, aralik=None, icerik_html=''):
    total_spend = m.get("spend", 0) + g.get("spend", 0)
    total_roas = round(s["total_sales"] / total_spend, 2) if total_spend > 0 else 0
    add_to_cart = s.get("add_to_cart", 0)
    total_orders = s["total_orders"]
    donusum_orani = round((total_orders / add_to_cart) * 100, 2) if add_to_cart > 0 else 0
    active_class = "active" if period == "yesterday" else ""

    top_urunler_html = ""
    products = s.get("top_products", [])
    max_val = max([v for _, v in products], default=1)
    colors = ["#2c77a3","#2c77a3","#3a8fc4","#3a8fc4","#4a9cc4","#4a9cc4","#5aaad4","#5aaad4","#6ab8d8","#6ab8d8","#7ac6dc","#7ac6dc","#8acfe0","#8acfe0","#9ad8e4","#9ad8e4","#aae0e8","#aae0e8","#bae8ec","#bae8ec"]
    for i, (name, val) in enumerate(products):
        pct = round((val / max_val) * 100)
        color = colors[i] if i < len(colors) else "#bae8ec"
        top_urunler_html += f'<div class="bar-row"><div class="bar-rank">{i+1}</div><div class="bar-name" title="{name}">{name}</div><div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div><div class="bar-val">₺{val:,.2f}</div></div>'

    hourly = s.get("hourly_data", [])
    o = onceki or {}
    if aralik:
        (kb, kt), (ob, ot) = aralik
        trg = lambda d: d.strftime('%d.%m.%Y')
        gun_sayisi = (kt - kb).days + 1
        if onceki:
            karsilastirma_not = (f'<div class="kars-not"><span class="kars-tag">Karşılaştırma</span>'
                                 f'<span><b>{trg(kb)} — {trg(kt)}</b> ({gun_sayisi} gün) '
                                 f'&nbsp;·&nbsp; önceki dönem: <b>{trg(ob)} — {trg(ot)}</b></span></div>')
        else:
            karsilastirma_not = ('<div class="kars-not"><span class="kars-tag">Karşılaştırma</span>'
                                 '<span>Önceki dönemin tamamı arşivde olmadığı için karşılaştırma yapılmadı. '
                                 'Arşiv doldukça bu alan çalışmaya başlayacak.</span></div>')
    else:
        karsilastirma_not = ''

    hourly_labels = str([h["hour"] for h in hourly])
    hourly_counts = str([h["count"] for h in hourly])
    hourly_revenue = str([h["revenue"] for h in hourly])

    html = f'''
<div id="period-{period}" class="period-content {active_class}">
<div class="wrap">

  {karsilastirma_not}
  <div class="plabel">Genel Özet</div>
  <div class="summary-grid">
    <div class="scard" data-ico="harcama">
      <div class="scard-label">Toplam Harcama</div>
      <div class="scard-value">₺{total_spend:,.2f}</div>
      {fark(total_spend, o.get("toplam_spend"), notr=True, bicim=para, sinif="scard-sub")}
    </div>
    <div class="scard green" data-ico="gelir">
      <div class="scard-label">Toplam Gelir</div>
      <div class="scard-value">₺{s["total_sales"]:,.2f}</div>
      {fark(s["total_sales"], o.get("gross"), bicim=para, sinif="scard-sub")}
    </div>
    <div class="scard orange" data-ico="roas">
      <div class="scard-label">Toplam ROAS</div>
      <div class="scard-value">{total_roas}x</div>
      {fark(total_roas, o.get("toplam_roas"), bicim=carpan, sinif="scard-sub")}
    </div>
    <div class="scard purple" data-ico="siparis">
      <div class="scard-label">Toplam Sipariş</div>
      <div class="scard-value">{total_orders}</div>
      {fark(total_orders, o.get("orders"), bicim=adet, sinif="scard-sub")}
    </div>
  </div>

  <div class="plabel">Meta Ads</div>
  <div class="platform-block">
    <div class="pb-header"><div class="pb-icon"><img src="logos/meta-ads-logo.png" alt="Meta"></div><div class="pb-name">Meta Ads</div></div>
    <div class="metrics-row" style="grid-template-columns:repeat(6,1fr)">
      <div class="mc" data-ico="harcama"><div class="mc-label">Harcama</div><div class="mc-value">₺{m.get("spend",0):,.2f}</div>{fark(m.get("spend",0), o.get("meta_spend"), notr=True, bicim=para)}</div>
      <div class="mc" data-ico="sepet"><div class="mc-label">Alışveriş</div><div class="mc-value">{m.get("purchases",0)}</div>{fark(m.get("purchases",0), o.get("meta_purch"), bicim=adet)}</div>
      <div class="mc" data-ico="roas"><div class="mc-label">ROAS</div><div class="mc-value">{m.get("roas",0)}x</div>{fark(m.get("roas",0), o.get("meta_roas"), bicim=carpan)}</div>
      <div class="mc" data-ico="tiklama"><div class="mc-label">CPC</div><div class="mc-value">₺{m.get("cpc",0)}</div>{fark(m.get("cpc",0), o.get("meta_cpc"), ters=True, bicim=para)}</div>
      <div class="mc" data-ico="oran"><div class="mc-label">CTR</div><div class="mc-value">%{m.get("ctr",0)}</div>{fark(m.get("ctr",0), o.get("meta_ctr"), bicim=yuzde)}</div>
      <div class="mc" data-ico="gosterim"><div class="mc-label">CPM</div><div class="mc-value">₺{m.get("cpm",0)}</div>{fark(m.get("cpm",0), o.get("meta_cpm"), ters=True, bicim=para)}</div>
    </div>
  </div>

  <div class="plabel">Google Ads</div>
  <div class="platform-block">
    <div class="pb-header"><div class="pb-icon"><img src="logos/google-ads-logo.png" alt="Google Ads"></div><div class="pb-name">Google Ads</div></div>
    <div class="metrics-row" style="grid-template-columns:repeat(6,1fr)">
      <div class="mc" data-ico="harcama"><div class="mc-label">Harcama</div><div class="mc-value">₺{g.get("spend",0):,.2f}</div>{fark(g.get("spend",0), o.get("g_spend"), notr=True, bicim=para)}</div>
      <div class="mc" data-ico="donusum"><div class="mc-label">Dönüşüm</div><div class="mc-value">{int(g.get("conversions",0))}</div>{fark(g.get("conversions",0), o.get("g_conv"), bicim=adet)}</div>
      <div class="mc" data-ico="roas"><div class="mc-label">ROAS</div><div class="mc-value">{g.get("roas",0)}x</div>{fark(g.get("roas",0), o.get("g_roas"), bicim=carpan)}</div>
      <div class="mc" data-ico="tiklama"><div class="mc-label">TBM</div><div class="mc-value">₺{g.get("tbm",0)}</div>{fark(g.get("tbm",0), o.get("g_tbm"), ters=True, bicim=para)}</div>
      <div class="mc" data-ico="oran"><div class="mc-label">Tıklama Oranı</div><div class="mc-value">%{g.get("ctr",0)}</div>{fark(g.get("ctr",0), o.get("g_ctr"), bicim=yuzde)}</div>
      <div class="mc" data-ico="gosterim"><div class="mc-label">BGBM</div><div class="mc-value">₺{g.get("bgbm",0)}</div>{fark(g.get("bgbm",0), o.get("g_bgbm"), ters=True, bicim=para)}</div>
    </div>
  </div>

  <div class="plabel">Shopify</div>
  <div class="platform-block">
    <div class="pb-header"><div class="pb-icon"><img src="logos/shopify-logo.png" alt="Shopify"></div><div class="pb-name">Shopify</div></div>
    <div class="metrics-row" style="grid-template-columns:repeat(4,1fr)">
      <div class="mc" data-ico="gelir"><div class="mc-label">Gelir</div><div class="mc-value">₺{s["total_sales"]:,.2f}</div>{fark(s["total_sales"], o.get("gross"), bicim=para)}</div>
      <div class="mc" data-ico="roas"><div class="mc-label">Toplam ROAS</div><div class="mc-value">{total_roas}x</div>{fark(total_roas, o.get("toplam_roas"), bicim=carpan)}</div>
      <div class="mc" data-ico="sepet"><div class="mc-label">Ort. Sepet</div><div class="mc-value">₺{s["aov"]:,.2f}</div>{fark(s["aov"], o.get("aov"), bicim=para)}</div>
      <div class="mc" data-ico="siparis"><div class="mc-label">Sipariş</div><div class="mc-value">{total_orders}</div>{fark(total_orders, o.get("orders"), bicim=adet)}</div>

    </div>
  </div>

  <div class="plabel">Analizler</div>

  <div class="chart-card full" data-ico="urun">
    <div class="cc-title"><span>En çok satan ürünler</span><span class="cc-count">{len(products)} ürün</span></div>
    <div class="scroll-area">{top_urunler_html}</div>
  </div>

  <div class="chart-card full" data-ico="saat">
    <div class="cc-title"><span>Saatlik sipariş dağılımı</span></div>
    <div class="hourly-box"><canvas id="hourly_chart_{period}"></canvas></div>
  </div>

  {icerik_html}

</div>
</div>
<script>
(function(){{
  var labels = {hourly_labels};
  var counts = {hourly_counts};
  var revenues = {hourly_revenue};
  window.addEventListener('load', function(){{
    var ctx = document.getElementById('hourly_chart_{period}');
    if(!ctx) return;
    new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: labels,
        datasets: [{{
          label: 'Sipariş',
          data: counts,
          backgroundColor: '#2c77a3',
          borderRadius: 3,
          yAxisID: 'y'
        }},{{
          label: 'Gelir',
          data: revenues,
          type: 'line',
          borderColor: '#2e9e62',
          backgroundColor: 'rgba(46,158,98,0.08)',
          tension: 0.4,
          pointRadius: 2,
          borderWidth: 2,
          yAxisID: 'y1'
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{ legend: {{ labels: {{ font: {{ size: 10 }}, boxWidth: 10 }} }} }},
        scales: {{
          x: {{ ticks: {{ font: {{ size: 8 }}, maxRotation: 45 }}, grid: {{ display: false }} }},
          y: {{ ticks: {{ font: {{ size: 9 }} }}, grid: {{ color: '#e8f2f9' }} }},
          y1: {{ position: 'right', ticks: {{ font: {{ size: 9 }}, callback: function(v){{ return '₺'+v.toLocaleString('tr-TR'); }} }}, grid: {{ display: false }} }}
        }}
      }}
    }});
  }});
}})();
</script>
'''
    return html

def build_report():
    import json as _json
    with open('template.html', 'r', encoding='utf-8') as f:
        html = f.read()

    _tz = int(os.environ.get("TZ_OFFSET", "3"))
    arsiv_yolu = os.path.join('data', 'gunluk.json')
    arsiv_gunler = {}
    arsiv_icerikler = {}
    if os.path.exists(arsiv_yolu):
        with open(arsiv_yolu, 'r', encoding='utf-8') as f:
            _arsiv = _json.load(f)
        arsiv_gunler = _arsiv.get('gunler', {})
        arsiv_icerikler = _arsiv.get('icerikler', {})
        print(f"Arşiv okundu: {len(arsiv_gunler)} gün (karşılaştırma için)")
    else:
        print("UYARI: data/gunluk.json yok — karşılaştırma yapılamayacak.")

    periods = ["yesterday", "last_7d", "last_30d", "this_month"]
    pie_data_map = {}
    all_meta = {}
    all_google = {}
    all_shopify = {}

    for period in periods:
        print(f"Veri çekiliyor: {period}...")
        import os as _os; from datetime import datetime as _dt, timedelta as _td; _tz=int(_os.environ.get("TZ_OFFSET","3")); _today=(_dt.utcnow()+_td(hours=_tz)).date(); print(f"DEBUG: bugun={_today}, dun={_today-_td(days=1)}, tz={_tz}")
        meta = get_meta(META_PERIODS[period])
        google = get_google(GOOGLE_PERIODS[period])
        shopify = get_shopify_data(period)

        m = meta.get("metrics") or {}
        g = google.get("metrics") or {}
        s = shopify

        all_meta[period] = {"metrics": m, "top_ads": meta.get("top_ads", [])}
        all_google[period] = {"metrics": g, "top_ads": google.get("top_ads", [])}
        all_shopify[period] = s

        pie_data_map[period] = {
            "metaSpend": m.get("spend", 0),
            "googleSpend": g.get("spend", 0),
            "metaRoasVal": m.get("purchase_value", 0),
            "googleRoasVal": g.get("conversion_value", 0)
        }

    html = html.replace("%%PIE_DATA_MAP%%", "")


    for period in periods:
        m = all_meta[period]["metrics"]
        g = all_google[period]["metrics"]
        s = all_shopify[period]
        kb, kt = donem_araligi(period, _tz)
        ob, ot = onceki_aralik(kb, kt)
        onceki = arsiv_topla(arsiv_gunler, ob, ot) if arsiv_gunler else None
        beklenen_gun = (ot - ob).days + 1
        if onceki and onceki["gun"] < beklenen_gun:
            # arsivde o donemin tum gunleri yoksa yuzde yaniltici olur
            print(f"  {period}: önceki dönem eksik ({onceki['gun']}/{beklenen_gun} gün) — karşılaştırma atlandı")
            onceki = None
        icerikler_sozluk = arsiv_icerikler if arsiv_icerikler else {}
        icerik_listesi, icerik_kaynak = arsiv_icerik(arsiv_gunler, icerikler_sozluk, kb, kt)
        icerik_html = icerik_bloku(icerik_listesi, icerik_kaynak)
        period_html = build_period_html(period, m, g, s, onceki, ((kb, kt), (ob, ot)), icerik_html)
        html = html.replace(f"%%PERIOD_{period.upper()}%%", period_html)

    # --- arsiv: ozel tarih araligi icin gunluk veri ---
    import shutil as _shutil
    from datetime import datetime as _dt2, timedelta as _td2
    arsiv_min = arsiv_max = ''
    if arsiv_gunler:
        gunler = sorted(arsiv_gunler.keys())
        arsiv_min, arsiv_max = gunler[0], gunler[-1]
        os.makedirs('output', exist_ok=True)
        _shutil.copyfile(arsiv_yolu, os.path.join('output', 'veri.json'))
        print(f"Arşiv kopyalandı: output/veri.json ({len(gunler)} gün)")
    else:
        print("UYARI: özel tarih aralığı çalışmayacak (arşiv boş).")

    # --- icerik gorselleri cikti klasorune kopyalansin ---
    if os.path.isdir(os.path.join('data', 'icerik')):
        hedef_ic = os.path.join('output', 'icerik')
        os.makedirs(hedef_ic, exist_ok=True)
        sayac = 0
        for dosya in os.listdir(os.path.join('data', 'icerik')):
            _shutil.copyfile(os.path.join('data', 'icerik', dosya), os.path.join(hedef_ic, dosya))
            sayac += 1
        print(f"İçerik görselleri kopyalandı: output/icerik ({sayac} dosya)")

    # --- logolar cikti klasorune kopyalansin ---
    if os.path.isdir('logos'):
        hedef = os.path.join('output', 'logos')
        os.makedirs(hedef, exist_ok=True)
        kopyalanan = 0
        for dosya in os.listdir('logos'):
            if dosya.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.webp')):
                _shutil.copyfile(os.path.join('logos', dosya), os.path.join(hedef, dosya))
                kopyalanan += 1
        print(f"Logolar kopyalandı: output/logos ({kopyalanan} dosya)")
    else:
        print("UYARI: logos klasörü bulunamadı — platform logoları görünmeyecek.")

    bugun_tr = (_dt2.utcnow() + _td2(hours=_tz))
    html = html.replace("%%RAPOR_TARIHI%%", bugun_tr.strftime('%d.%m.%Y'))
    html = html.replace("%%YIL%%", bugun_tr.strftime('%Y'))
    if arsiv_min and arsiv_max:
        aralik_metni = f"{arsiv_min} — {arsiv_max}"
    else:
        aralik_metni = "hazırlanıyor"
    html = html.replace("%%ARSIV_MIN%% — %%ARSIV_MAX%%", aralik_metni)
    html = html.replace("%%ARSIV_MIN%%", arsiv_min)
    html = html.replace("%%ARSIV_MAX%%", arsiv_max)

    output_path = 'output/index.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nRapor oluşturuldu: {output_path}")

if __name__ == "__main__":
    build_report()
