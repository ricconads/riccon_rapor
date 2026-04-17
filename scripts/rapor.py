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

def build_period_html(period, m, g, s):
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
        top_urunler_html += f'<div class="bar-row"><div class="bar-rank">{i+1}</div><div class="bar-name">{name}</div><div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div><div class="bar-val">₺{val:,.2f}</div></div>'

    hourly = s.get("hourly_data", [])
    hourly_labels = str([h["hour"] for h in hourly])
    hourly_counts = str([h["count"] for h in hourly])
    hourly_revenue = str([h["revenue"] for h in hourly])

    html = f'''
<div id="period-{period}" class="period-content {active_class}">
<div class="wrap">

  <div class="plabel">Genel Özet</div>
  <div class="summary-grid">
    <div class="scard">
      <div class="scard-label">Toplam Harcama</div>
      <div class="scard-value">₺{total_spend:,.2f}</div>
      <div class="scard-sub neutral">—</div>
    </div>
    <div class="scard green">
      <div class="scard-label">Toplam Gelir</div>
      <div class="scard-value">₺{s["total_sales"]:,.2f}</div>
      <div class="scard-sub neutral">—</div>
    </div>
    <div class="scard orange">
      <div class="scard-label">Toplam ROAS</div>
      <div class="scard-value">{total_roas}x</div>
      <div class="scard-sub neutral">—</div>
    </div>
    <div class="scard purple">
      <div class="scard-label">Toplam Sipariş</div>
      <div class="scard-value">{total_orders}</div>
      <div class="scard-sub neutral">—</div>
    </div>
  </div>

  <div class="plabel">Meta Ads</div>
  <div class="platform-block">
    <div class="pb-header"><div class="pb-name">Meta Ads</div></div>
    <div class="metrics-row" style="grid-template-columns:repeat(6,1fr)">
      <div class="mc"><div class="mc-label">Harcama</div><div class="mc-value">₺{m.get("spend",0):,.2f}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">Alışveriş</div><div class="mc-value">{m.get("purchases",0)}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">ROAS</div><div class="mc-value">{m.get("roas",0)}x</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">CPC</div><div class="mc-value">₺{m.get("cpc",0)}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">CTR</div><div class="mc-value">%{m.get("ctr",0)}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">CPM</div><div class="mc-value">₺{m.get("cpm",0)}</div><div class="mc-change neutral">—</div></div>
    </div>
  </div>

  <div class="plabel">Google Ads</div>
  <div class="platform-block">
    <div class="pb-header"><div class="pb-name">Google Ads</div></div>
    <div class="metrics-row" style="grid-template-columns:repeat(6,1fr)">
      <div class="mc"><div class="mc-label">Harcama</div><div class="mc-value">₺{g.get("spend",0):,.2f}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">Dönüşüm</div><div class="mc-value">{int(g.get("conversions",0))}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">ROAS</div><div class="mc-value">{g.get("roas",0)}x</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">TBM</div><div class="mc-value">₺{g.get("tbm",0)}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">Tıklama Oranı</div><div class="mc-value">%{g.get("ctr",0)}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">BGBM</div><div class="mc-value">₺{g.get("bgbm",0)}</div><div class="mc-change neutral">—</div></div>
    </div>
  </div>

  <div class="plabel">Shopify</div>
  <div class="platform-block">
    <div class="pb-header"><div class="pb-name">Shopify</div></div>
    <div class="metrics-row" style="grid-template-columns:repeat(5,1fr)">
      <div class="mc"><div class="mc-label">Gelir</div><div class="mc-value">₺{s["total_sales"]:,.2f}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">Toplam ROAS</div><div class="mc-value">{total_roas}x</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">Ort. Sepet</div><div class="mc-value">₺{s["aov"]:,.2f}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">Sipariş</div><div class="mc-value">{total_orders}</div><div class="mc-change neutral">—</div></div>
      <div class="mc"><div class="mc-label">Dönüşüm Oranı</div><div class="mc-value">%{donusum_orani}</div><div class="mc-change neutral">—</div></div>
    </div>
  </div>

  <div class="plabel">Analizler</div>

  <div class="charts-grid">
    <div style="background:white;border-radius:10px;border:0.5px solid #cce0ee;padding:14px 16px;height:320px;display:flex;flex-direction:column;">
      <div class="cc-title"><span>En çok satan ürünler</span><span class="cc-count">{len(products)} ürün</span></div>
      <div class="scroll-area">{top_urunler_html}</div>
    </div>
    <div style="background:white;border-radius:10px;border:0.5px solid #cce0ee;padding:14px 16px;height:320px;display:flex;flex-direction:column;">
      <div class="cc-title"><span>Saatlik sipariş dağılımı</span></div>
      <div style="flex:1;min-height:0;position:relative;">
        <canvas id="hourly_chart_{period}" style="max-height:240px;"></canvas>
      </div>
    </div>
  </div>

  <div class="charts-grid">
    <div style="background:white;border-radius:10px;border:0.5px solid #cce0ee;padding:14px 16px;height:320px;display:flex;flex-direction:column;">
      <div class="cc-title"><span>Platform harcama dağılımı</span></div>
      <div class="pie-wrap">
        <canvas id="pie_spend_{period}" width="180" height="180"></canvas>
      </div>
      <div class="pie-legend">
        <div style="display:flex;align-items:center;gap:5px"><div class="pie-dot" style="background:#1877f2"></div><div class="pie-label">Meta · ₺{m.get("spend",0):,.2f}</div></div>
        <div style="display:flex;align-items:center;gap:5px"><div class="pie-dot" style="background:#ea4335"></div><div class="pie-label">Google · ₺{g.get("spend",0):,.2f}</div></div>
      </div>
    </div>
    <div style="background:white;border-radius:10px;border:0.5px solid #cce0ee;padding:14px 16px;height:320px;display:flex;flex-direction:column;">
      <div class="cc-title"><span>Platform dönüşüm geliri dağılımı</span></div>
      <div class="pie-wrap">
        <canvas id="pie_roas_{period}" width="180" height="180"></canvas>
      </div>
      <div class="pie-legend">
        <div style="display:flex;align-items:center;gap:5px"><div class="pie-dot" style="background:#1877f2"></div><div class="pie-label">Meta · ₺{m.get("purchase_value",0):,.2f}</div></div>
        <div style="display:flex;align-items:center;gap:5px"><div class="pie-dot" style="background:#ea4335"></div><div class="pie-label">Google · ₺{g.get("conversion_value",0):,.2f}</div></div>
      </div>
    </div>
  </div>

  <div class="charts-grid">
    <div style="background:white;border-radius:10px;border:0.5px solid #cce0ee;padding:14px 16px;height:320px;display:flex;flex-direction:column;">
      <div class="cc-title"><span>Meta — En yüksek ROAS\'lı reklamlar</span></div>
      <div class="scroll-area" id="meta_ads_{period}"></div>
    </div>
    <div style="background:white;border-radius:10px;border:0.5px solid #cce0ee;padding:14px 16px;height:320px;display:flex;flex-direction:column;">
      <div class="cc-title"><span>Google — En yüksek ROAS\'lı reklamlar</span></div>
      <div class="scroll-area" id="google_ads_{period}"></div>
    </div>
  </div>

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
    with open('template.html', 'r', encoding='utf-8') as f:
        html = f.read()

    periods = ["yesterday", "last_7d", "last_30d", "this_month"]
    pie_data_map = {}
    all_meta = {}
    all_google = {}
    all_shopify = {}

    for period in periods:
        print(f"Veri çekiliyor: {period}...")
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

    js_map = "window.pieDataMap = {"
    for period in periods:
        d = pie_data_map[period]
        js_map += f'"{period}":{{metaSpend:{d["metaSpend"]},googleSpend:{d["googleSpend"]},metaRoasVal:{d["metaRoasVal"]},googleRoasVal:{d["googleRoasVal"]}}},'
    js_map += "};"

    ads_js = ""
    for period in periods:
        meta_ads = all_meta[period]["top_ads"]
        google_ads = all_google[period]["top_ads"]

        max_m = max([a["roas"] for a in meta_ads], default=1)
        meta_js = ""
        for i, a in enumerate(meta_ads):
            pct = round((a["roas"] / max_m) * 100) if max_m > 0 else 0
            name = a["ad_name"].replace('"', '').replace("'", '')
            meta_js += f'html+="<div class=\\"bar-row\\"><div class=\\"bar-rank\\">{i+1}</div><div class=\\"bar-name\\">{name}</div><div class=\\"bar-track\\"><div class=\\"bar-fill\\" style=\\"width:{pct}%;background:#1877f2\\"></div></div><div class=\\"bar-val\\">{a["roas"]}x</div></div>";'

        max_g = max([a["roas"] for a in google_ads], default=1)
        google_js = ""
        for i, a in enumerate(google_ads):
            pct = round((a["roas"] / max_g) * 100) if max_g > 0 else 0
            name = a["name"].replace('"', '').replace("'", '')
            google_js += f'html+="<div class=\\"bar-row\\"><div class=\\"bar-rank\\">{i+1}</div><div class=\\"bar-name\\">{name}</div><div class=\\"bar-track\\"><div class=\\"bar-fill\\" style=\\"width:{pct}%;background:#ea4335\\"></div></div><div class=\\"bar-val\\">{a["roas"]}x</div></div>";'

        ads_js += f'(function(){{var html="";{meta_js}document.getElementById("meta_ads_{period}").innerHTML=html;}})();'
        ads_js += f'(function(){{var html="";{google_js}document.getElementById("google_ads_{period}").innerHTML=html;}})();'

    full_js = js_map + "\nwindow.addEventListener('load',function(){" + ads_js + "});"
    html = html.replace("%%PIE_DATA_MAP%%", full_js)

    for period in periods:
        m = all_meta[period]["metrics"]
        g = all_google[period]["metrics"]
        s = all_shopify[period]
        period_html = build_period_html(period, m, g, s)
        html = html.replace(f"%%PERIOD_{period.upper()}%%", period_html)

    output_path = 'output/index.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nRapor oluşturuldu: {output_path}")

if __name__ == "__main__":
    build_report()
