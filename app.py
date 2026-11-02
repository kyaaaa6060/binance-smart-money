import os
import time
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. BÖLÜM: KOPYA TİCARETİ TARAMA MOTORU
# ==========================================

MIN_LOSS = 6.0  # % zarar alt sınır
MAX_LOSS = 20.0  # % zarar üst sınır
USE_LEVERAGE = False
HL_TOP_N = 100
MIN_ACCOUNT_VALUE = 10_000
SLEEP = 0.2
ENABLED = ['hyperliquid', 'binance', 'bybit', 'okx', 'bitget', 'mexc']

S = requests.Session()
S.headers.update({
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,'
        ' like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Content-Type': 'application/json',
})


def norm_coin(sym: str) -> str:
  if not sym:
    return ''
  s = (
      sym.upper()
      .replace('-SWAP', '')
      .replace('_', '')
      .replace('-', '')
      .replace('/', '')
  )
  if s.startswith('XBT'):
    s = 'BTC' + s[3:]
  for q in ('USDT', 'USDC', 'USD', 'PERP', 'COIN'):
    if s.endswith(q):
      s = s[:-len(q)]
      break
  return s


def fetch_hyperliquid():
  out = []
  try:
    lb = S.get(
        'https://stats-data.hyperliquid.xyz/Mainnet/leaderboard', timeout=20
    ).json()
    rows = lb.get('leaderboardRows', [])
    rows = [
        r for r in rows if float(r.get('accountValue', 0)) >= MIN_ACCOUNT_VALUE
    ]
    rows.sort(key=lambda r: float(r['accountValue']), reverse=True)
    for r in rows[:HL_TOP_N]:
      addr = r['ethAddress']
      try:
        st_data = S.post(
            'https://api.hyperliquid.xyz/info',
            json={'type': 'clearinghouseState', 'user': addr},
            timeout=10,
        ).json()
      except Exception:
        continue
      for ap in st_data.get('assetPositions', []):
        p = ap['position']
        szi = float(p['szi'])
        if szi == 0:
          continue
        out.append(
            dict(
                exchange='hyperliquid',
                trader=addr,
                coin=norm_coin(p['coin']),
                side='LONG' if szi > 0 else 'SHORT',
                entry=float(p['entryPx']),
                notional=abs(float(p['positionValue'])),
                leverage=float(p.get('leverage', {}).get('value', 1)),
                mark=None,
            )
        )
      time.sleep(SLEEP)
  except Exception as e:
    print(f'Hyperliquid Hata: {e}')
  return out


def hyperliquid_prices():
  try:
    mids = S.post(
        'https://api.hyperliquid.xyz/info',
        json={'type': 'allMids'},
        timeout=10,
    ).json()
    return {
        norm_coin(k): float(v) for k, v in mids.items() if not k.startswith('@')
    }
  except Exception:
    return {}


def fetch_binance(top_n=30):
  out = []
  base = 'https://www.binance.com/bapi/futures'
  body = {
      'pageNumber': 1,
      'pageSize': 20,
      'timeRange': '30D',
      'dataType': 'ROI',
      'favoriteOnly': False,
      'hideFull': False,
      'nickname': '',
      'order': 'DESC',
      'userAsset': 0,
      'portfolioType': 'ALL',
      'useAiRecommended': False,
  }
  leaders = []
  try:
    r = S.post(
        f'{base}/v1/friendly/future/copy-trade/home-page/query-list',
        json=body,
        timeout=15,
    ).json()
    items = (r.get('data') or {}).get('list') or []
    for i in items[:top_n]:
      leaders.append(i['leadPortfolioId'])
  except Exception:
    pass

  for pid in leaders:
    try:
      r = S.get(
          f'{base}/v1/friendly/future/copy-trade/lead-data/positions',
          params={'portfolioId': pid},
          timeout=10,
      ).json()
      for p in r.get('data') or []:
        amt = float(p.get('positionAmount', 0))
        if amt == 0:
          continue
        entry = float(p['entryPrice'])
        out.append(
            dict(
                exchange='binance',
                trader=str(pid),
                coin=norm_coin(p['symbol']),
                side=(
                    'LONG'
                    if p.get('positionSide', '').upper() == 'LONG'
                    or (p.get('positionSide', 'BOTH') == 'BOTH' and amt > 0)
                    else 'SHORT'
                ),
                entry=entry,
                notional=abs(amt) * float(p.get('markPrice', entry)),
                leverage=float(p.get('leverage', 1)),
                mark=float(p['markPrice']) if p.get('markPrice') else None,
            )
        )
    except Exception:
      pass
    time.sleep(SLEEP)
  return out


def fetch_bybit(top_n=20):
  out = []
  try:
    r = S.get(
        'https://gw.bybit.com/perpetual/copy-trade/v1/public/leaderboard/query-rsp-list',
        params={'limit': top_n, 'sortBy': 'roi'},
        timeout=15,
    ).json()
    items = (r.get('result') or {}).get('list') or []
    for item in items:
      enc_uid = item.get('encryptedUid')
      if not enc_uid:
        continue
      pos_r = S.get(
          'https://gw.bybit.com/perpetual/copy-trade/v1/public/leaderboard/positions',
          params={'encryptedUid': enc_uid},
          timeout=10,
      ).json()
      for p in (pos_r.get('result') or {}).get('positionList') or []:
        size = float(p.get('size', 0))
        if size == 0:
          continue
        entry = float(p.get('entryPrice', 0))
        out.append(
            dict(
                exchange='bybit',
                trader=str(enc_uid),
                coin=norm_coin(p.get('symbol', '')),
                side='LONG' if p.get('side', '').upper() == 'BUY' else 'SHORT',
                entry=entry,
                notional=abs(size) * entry,
                leverage=float(p.get('leverage', 1)),
                mark=None,
            )
        )
      time.sleep(SLEEP)
  except Exception:
    pass
  return out


def fetch_okx(top_n=20):
  out = []
  try:
    r = S.get(
        'https://www.okx.com/v3/c2c/copytrading/public-lead-traders',
        params={'limit': top_n, 'period': '30d'},
        timeout=15,
    ).json()
    items = (r.get('data') or {}).get('list') or []
    for item in items:
      inst_id = item.get('uniqueCode')
      if not inst_id:
        continue
      pos_r = S.get(
          'https://www.okx.com/v3/c2c/copytrading/public-lead-positions',
          params={'uniqueCode': inst_id},
          timeout=10,
      ).json()
      for p in pos_r.get('data') or []:
        sz = float(p.get('pos', 0))
        if sz == 0:
          continue
        entry = float(p.get('avgPx', 0))
        out.append(
            dict(
                exchange='okx',
                trader=str(inst_id),
                coin=norm_coin(p.get('instId', '')),
                side='LONG' if sz > 0 else 'SHORT',
                entry=entry,
                notional=abs(sz) * entry,
                leverage=float(p.get('lever', 1)),
                mark=None,
            )
        )
      time.sleep(SLEEP)
  except Exception:
    pass
  return out


def fetch_bitget(top_n=20):
  out = []
  try:
    r = S.get(
        'https://api.bitget.com/api/v2/mix/copy/trader/query-expert-list',
        params={'pageSize': top_n, 'pageNo': 1},
        timeout=15,
    ).json()
    items = (r.get('data') or {}).get('resultList') or []
    for item in items:
      tracer_id = item.get('tracerNo') or item.get('userId')
      if not tracer_id:
        continue
      pos_r = S.get(
          'https://api.bitget.com/api/v2/mix/copy/trader/query-current-orders',
          params={'tracerNo': tracer_id},
          timeout=10,
      ).json()
      for p in pos_r.get('data') or []:
        hold_amount = float(p.get('holdAmount', 0))
        if hold_amount == 0:
          continue
        entry = float(p.get('openPriceAvg', 0))
        out.append(
            dict(
                exchange='bitget',
                trader=str(tracer_id),
                coin=norm_coin(p.get('symbol', '')),
                side='LONG' if p.get('holdSide', '').upper() == 'LONG' else 'SHORT',
                entry=entry,
                notional=abs(hold_amount) * entry,
                leverage=float(p.get('leverage', 1)),
                mark=None,
            )
        )
      time.sleep(SLEEP)
  except Exception:
    pass
  return out


def fetch_mexc(top_n=20):
  out = []
  try:
    r = S.get(
        'https://contract.mexc.com/api/v1/copy/mixed/client/list/rank',
        params={'pageSize': top_n, 'rankType': 1},
        timeout=15,
    ).json()
    items = (r.get('data') or {}).get('result') or []
    for item in items:
      uid = item.get('copyUid') or item.get('uid')
      if not uid:
        continue
      pos_r = S.get(
          'https://contract.mexc.com/api/v1/copy/mixed/position/open/list',
          params={'copyUid': uid},
          timeout=10,
      ).json()
      for p in pos_r.get('data') or []:
        vol = float(p.get('vol', 0))
        if vol == 0:
          continue
        entry = float(p.get('openPrice', 0))
        out.append(
            dict(
                exchange='mexc',
                trader=str(uid),
                coin=norm_coin(p.get('symbol', '')),
                side='LONG' if p.get('positionType', 1) == 1 else 'SHORT',
                entry=entry,
                notional=abs(vol) * entry,
                leverage=float(p.get('leverage', 1)),
                mark=None,
            )
        )
      time.sleep(SLEEP)
  except Exception:
    pass
  return out


ADAPTERS = dict(
    hyperliquid=fetch_hyperliquid,
    binance=fetch_binance,
    bybit=fetch_bybit,
    okx=fetch_okx,
    bitget=fetch_bitget,
    mexc=fetch_mexc,
)


def wavg(df):
  return (
      (df.entry * df.notional).sum() / df.notional.sum()
      if df.notional.sum()
      else float('nan')
  )


def summarize(df, label_cols):
  rows = []
  for keys, g in df.groupby(label_cols):
    keys = keys if isinstance(keys, tuple) else (keys,)
    rows.append({
        **dict(zip(label_cols, keys)),
        'trader_sayisi': g.trader.nunique(),
        'pozisyon_buyuklugu_AUM': round(g.notional.sum(), 2),
        'ort_giris': wavg(g),
    })
  return pd.DataFrame(rows)


def run_scan():
  positions = []
  for name in ENABLED:
    if name not in ADAPTERS:
      continue
    try:
      data = ADAPTERS[name]()
      positions += data
    except Exception as e:
      print(f'{name} Hatası: {e}')

  if not positions:
    return False

  df = pd.DataFrame(positions)
  prices = hyperliquid_prices()

  df['price'] = df.apply(
      lambda r: r.mark if (r.mark and r.mark > 0) else prices.get(r.coin),
      axis=1,
  )
  df['price'] = df['price'].fillna(df['entry'])
  df = df.dropna(subset=['price'])

  if df.empty:
    return False

  move = df.apply(
      lambda r: (
          (r.entry - r.price) / r.entry * 100
          if r.side == 'LONG'
          else (r.price - r.entry) / r.entry * 100
      ),
      axis=1,
  )
  df['loss_pct'] = move * (df.leverage if USE_LEVERAGE else 1)

  all_sum = summarize(df, ['coin', 'side']).assign(exchange='ALL')
  ex_sum = summarize(df, ['exchange', 'coin', 'side'])
  main_tbl = pd.concat([all_sum, ex_sum]).sort_values(
      ['coin', 'side', 'exchange']
  )

  flt = df[(df.loss_pct >= MIN_LOSS) & (df.loss_pct <= MAX_LOSS)]
  if len(flt) > 0:
    flt_all = summarize(flt, ['coin', 'side']).assign(exchange='ALL')
    flt_ex = summarize(flt, ['exchange', 'coin', 'side'])
    flt_tbl = pd.concat([flt_all, flt_ex]).sort_values(
        ['coin', 'side', 'exchange']
    )
  else:
    flt_tbl = pd.DataFrame(
        columns=[
            'coin',
            'side',
            'exchange',
            'trader_sayisi',
            'pozisyon_buyuklugu_AUM',
            'ort_giris',
        ]
    )

  with pd.ExcelWriter('copytrade_rapor.xlsx', engine='openpyxl') as w:
    main_tbl.to_excel(w, sheet_name='Tum_Pozisyonlar', index=False)
    flt_tbl.to_excel(
        w, sheet_name=f'Terste_%{int(MIN_LOSS)}-{int(MAX_LOSS)}', index=False
    )
    df.to_excel(w, sheet_name='Ham_Veri', index=False)
  return True


# ==========================================
# 2. BÖLÜM: STREAMLIT WEB ARAYÜZÜ (DASHBOARD)
# ==========================================

st.set_page_config(
    page_title='Smart Money Copy Trade Dashboard', layout='wide'
)

st.title('📊 Kripto Smart Money & Tersteki Trader Dashboard')
st.markdown(
    'Çoklu borsa (Hyperliquid, Binance, Bybit, OKX, Bitget, MEXC) canlı copy'
    ' trade verileri ve **%6 - %20 zararda (terste)** olan pozisyonlar.'
)

col1, col2 = st.columns([1, 4])

with col1:
  if st.button('🔄 Borsaları Şimdi Tara'):
    with st.spinner('Tüm borsalar taranıyor... (1-2 dk sürebilir)'):
      success = run_scan()
      if success:
        st.success('Tarama başarılı!')
        st.rerun()
      else:
        st.error('Veri çekilemedi.')

rapor_yolu = 'copytrade_rapor.xlsx'

if os.path.exists(rapor_yolu):
  try:
    df_terste = pd.read_excel(rapor_yolu, sheet_name='Terste_%6-20')
    df_tum = pd.read_excel(rapor_yolu, sheet_name='Tum_Pozisyonlar')

    coins = (
        ['TÜMÜ'] + sorted(list(df_tum['coin'].unique()))
        if 'coin' in df_tum.columns and not df_tum.empty
        else []
    )
    selected_coin = st.selectbox('🔍 Coin Seçin:', coins)

    if selected_coin != 'TÜMÜ':
      if not df_terste.empty and 'coin' in df_terste.columns:
        df_terste = df_terste[df_terste['coin'] == selected_coin]
      if not df_tum.empty and 'coin' in df_tum.columns:
        df_tum = df_tum[df_tum['coin'] == selected_coin]

    st.divider()
    st.subheader('⚠️ %6 - %20 Zararda (Terste) Kalan Master Traderlar')
    if not df_terste.empty:
      st.dataframe(df_terste, use_container_width=True)
    else:
      st.info('Seçilen kritere uyan tersteki pozisyon bulunamadı.')

    st.divider()
    st.subheader('📈 Harmanlanmış Tüm Pozisyon Özeti (AUM & Giriş Ort.)')
    if not df_tum.empty:
      st.dataframe(df_tum, use_container_width=True)

  except Exception as e:
    st.error(f'Rapor okunurken hata oluştu: {e}')
else:
  st.warning(
      'Henüz rapor verisi yok. Lütfen yukarıdaki **"Borsaları Şimdi Tara"**'
      ' butonuna basın.'
  )
