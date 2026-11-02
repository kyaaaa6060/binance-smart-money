import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Copy Trade Tersteki Traderlar", layout="wide")

st.title("🚀 Kripto Copy Trade - Tersteki Smart Money Analizi")
st.markdown("Borsalardan canlı çekilen master trader verileri ve **%6 - %20 zararda (terste)** olan pozisyonlar.")

# Yenileme butonu
if st.button("🔄 Verileri Yenile / Raporu Oku"):
    st.rerun()

rapor_yolu = "copytrade_rapor.xlsx"

if os.path.exists(rapor_yolu):
    try:
        df_terste = pd.read_excel(rapor_yolu, sheet_name="Terste_%6-20")
        df_tum = pd.read_excel(rapor_yolu, sheet_name="Tum_Pozisyonlar")

        st.subheader("⚠️ %6 - %20 Zararda (Terste) Kalan Lider Traderlar")
        if not df_terste.empty:
            st.dataframe(df_terste, use_container_width=True)
        else:
            st.info("Şu anda %6 - %20 arası terste kalan pozisyon bulunamadı.")

        st.divider()

        st.subheader("📊 Tüm Pozisyonların Genel Harmanlanmış Özeti")
        if not df_tum.empty:
            st.dataframe(df_tum, use_container_width=True)
            
    except Exception as e:
        st.error(f"Rapor okunurken hata oluştu: {e}")
else:
    st.warning("Henüz oluşturulmuş bir `copytrade_rapor.xlsx` raporu bulunamadı. Arka plan tarayıcısının çalışması bekleniyor...")
