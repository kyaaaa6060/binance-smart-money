import asyncio
import os
import re
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from curl_cffi.requests import AsyncSession
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse

DEFAULT_MIN_AUM = float(os.getenv("DEFAULT_MIN_AUM", "0"))
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "120"))
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "4"))

BINANCE_RAW_LINKS = [
    "https://app.binance.com/uni-qr/cpro/Square-Creator-f11904099?l=en&r=LBXLGCLF&uc=app_square_share_link&us=more",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-2e5b520705d2?l=en&r=B2YFHBO6&uc=app_square_share_link&us=more",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-aa47b27b7a24?l=en&r=W0VRB5W3&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-f1e33f5a7ef35?l=en&r=D3CU5ZCA&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-75c835342?l=en&r=BXFBP7KC&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/poorcat?l=en&r=VHU2DSUN&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-90288901e9fd?l=en&r=N62YX4JR&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/daddyofjto?l=en&r=S9PCQGNK&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-731503f0a5b9?l=en&r=BH9VUBT9&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-d48e9bbda29b1?l=en&r=YZ7D92ML&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-0d5f98a93b03?l=en&r=YIFWPH9J&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-0f0afa86dba4?l=en&r=CW6N19XT&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-4f4161992?l=en&r=PNOJ4XR8&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-487243813?l=en&r=ZTCOMOYC&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/zhuaibai?l=en&r=RI14K647&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-d6c907ed4b7e8?l=en&r=YBX6ES0G&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-4cf121271?l=en&r=QJZKD3YM&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-eb08b0791ef00?l=en&r=YYT7LUJ7&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-e5ce582dea41?l=en&r=GLFYZOK7&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-8079dd106c4f?l=en&r=XB4YEC3O&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-be7aa3f355c02?l=en&r=BP98SCPP&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-d1f86189ae7a1?l=en&r=SUHM4L1J&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-19867ce31866?l=en&r=TSIQQGMQ&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-991457747?l=en&r=RVZ2GNXR&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-c22178162?l=en&r=NVSDK3FQ&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/carefree-L?l=en&r=GVBDSDFT&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/TDRh?l=en&r=SCQKEIH6&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-811041579?l=en&r=XJQ83CQ6&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Joker999?l=en&r=Y9YMHIML&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-73624121e3b24?l=en&r=Square-Creator-73624121e3b24&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/imone?l=en&r=CL05MK5E&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-500cfabd1e46f?l=en&r=W8KP8AYS&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-d00d598a2001?l=en&r=AM3ZSKV0&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-5b9377428?l=en&r=A9P4LG58&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-981436500?l=en&r=MGWERBBQ&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/solo-ghost?l=en&r=L6UTXCAC&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-7d02c41a758a?l=en&r=YJUTC07Y&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-c46aea8e0c5a?l=en&r=E34J30UC&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-37403bc2712c4?l=en&r=K68UATKF&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/StefanBayes?l=en&r=XMFJ8LTB&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-4e0884e44c34?l=en&r=IAALX38L&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-0d3a54467a14?l=en&r=ASQEXUJS&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-536c244ec1328?l=en&r=CCCQI4XG&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/aozhou?l=en&r=MNS8OV8K&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-269a7bd77cc64?l=en&r=OBB63Z8V&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-12dee8a98668?l=en&r=QI5ZBS51&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/miesedap?l=en&r=VW60MKDR&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/yonghengyishun?l=en&r=LFY4B4AK&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/gzccc?l=en&r=QLJLAGO9&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-65b555835?l=en&r=VNVQ5ZX8&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-fa80ff4ac1a5?l=en&r=A5QCZ4SY&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-599248483?l=en&r=GBKNY08D&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-ab7166b687b38?l=en&r=EM2ZFBQA&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-b2bd0e16caf7a?l=en&r=ZN5L19ID&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-8fe8dcc4edfc6?l=en&r=X1MVMYYB&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-e61296ffe22f9?l=en&r=JM1XX26Q&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-c52225267?l=en&r=DTYFUNHP&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-1f6975b79365f?l=en&r=LWPLMPE4&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-1eed94bc0ba95?l=en&r=VHFKDPR8&uc=app_square_share_link&us=telegram",
    "https://app.binance.com/uni-qr/cpro/Square-Creator-911d51d83df1?l=en&r=BZPCMPM5&uc=app_square_share_link&us=telegram",
]

OKX_RAW_LINKS = [
    "https://www.okx.com/copy-trading/account/FE701D3CB0AC0E8F?tab=trade",
    "https://www.okx.com/copy-trading/account/6DE7F61BFFD009F6?tab=trade",
    "https://www.okx.com/copy-trading/account/8C756A028EDC2FE7?tab=trade",
    "https://www.okx.com/copy-trading/account/E1E1885A7FC500D3?tab=trade",
    "https://www.okx.com/copy-trading/account/01B0F9478102163C?tab=trade",
    "https://www.okx.com/copy-trading/account/D89A246530D24C6E?tab=trade",
    "https://www.okx.com/copy-trading/account/37D18BE54F98F099?tab=trade",
    "https://www.okx.com/copy-trading/account/B74FC756C8EE894B?tab=trade",
    "https://www.okx.com/copy-trading/account/CEB867A1A00B6682?tab=trade",
    "https://www.okx.com/copy-trading/account/811846999954962957?tab=trade",
    "https://www.okx.com/copy-trading/account/89CB0185A6F9BB72?tab=trade",
    "https://www.okx.com/copy-trading/account/3CE34D3FF6F990FC?tab=trade",
    "https://www.okx.com/copy-trading/account/26E1ADBB02FAACA1?tab=trade",
    "https://www.okx.com/copy-trading/account/38649778D6442398?tab=trade",
    "https://www.okx.com/copy-trading/account/C2B269D649346A25?tab=trade",
    "https://www.okx.com/copy-trading/account/744584888019747661?tab=trade",
    "https://www.okx.com/copy-trading/account/777901231196176970?tab=trade",
    "https://www.okx.com/copy-trading/account/792427085649551867?tab=trade",
    "https://www.okx.com/copy-trading/account/757CC8A7D7FAC010?tab=trade",
    "https://www.okx.com/copy-trading/account/847700947416724159?tab=trade",
    "https://www.okx.com/copy-trading/account/D2A8F38CFFF5F992?tab=trade",
    "https://www.okx.com/copy-trading/account/2D545AFACC03C11E?tab=trade",
    "https://www.okx.com/copy-trading/account/8F53B7AEDF041739?tab=trade",
    "https://www.okx.com/copy-trading/account/EDC2CA66E137873B?tab=trade",
    "https://www.okx.com/copy-trading/account/760386676346038930?tab=trade",
    "https://www.okx.com/copy-trading/account/882337170764375802?tab=trade",
    "https://www.okx.com/copy-trading/account/0E59266AC1409761?tab=trade",
    "https://www.okx.com/copy-trading/account/86432F983B99BA1C?tab=trade",
    "https://www.okx.com/copy-trading/account/D503A7FA37549816?tab=trade",
    "https://www.okx.com/copy-trading/account/F61990B585217C24?tab=trade",
    "https://www.okx.com/copy-trading/account/35E22983F436F55B?tab=trade",
    "https://www.okx.com/copy-trading/account/F1344E1B7AE2D41F?tab=trade",
    "https://www.okx.com/copy-trading/account/E3654BF20F6C758D?tab=trade",
    "https://www.okx.com/copy-trading/account/35F888C7BB441B2B?tab=trade",
    "https://www.okx.com/copy-trading/account/9C2CB3B2306B28EA?tab=trade",
    "https://www.okx.com/copy-trading/account/6A30B93C28DD247F?tab=trade",
    "https://www.okx.com/copy-trading/account/7E27C9B14BB5D378?tab=trade",
    "https://www.okx.com/copy-trading/account/082EDAFDB8CB171F?tab=trade",
    "https://www.okx.com/copy-trading/account/37131D5541108735?tab=trade",
    "https://www.okx.com/copy-trading/account/F10D7F7A4A164AFB?tab=trade",
    "https://www.okx.com/copy-trading/account/58D7D205FB591484?tab=trade",
    "https://www.okx.com/copy-trading/account/EA315ECC2A50F8B6?tab=trade",
    "https://www.okx.com/copy-trading/account/7D34F0975D241797?tab=trade",
    "https://www.okx.com/copy-trading/account/6DC8B73158E4ED70?tab=trade",
    "https://www.okx.com/copy-trading/account/C9B1558F671ED132?tab=trade",
    "https://www.okx.com/copy-trading/account/1761D578C7A15813?tab=trade",
    "https://www.okx.com/copy-trading/account/D286B322B8A241B7?tab=trade",
    "https://www.okx.com/copy-trading/account/FA400F0E91664A05?tab=trade",
    "https://www.okx.com/copy-trading/account/31F3288F9B90B496?tab=trade",
    "https://www.okx.com/copy-trading/account/952071415C9BAD06?tab=trade",
    "https://www.okx.com/copy-trading/account/869309567220652934?tab=trade",
    "https://www.okx.com/copy-trading/account/601D07DAAB0F0C95?tab=trade",
    "https://www.okx.com/copy-trading/account/94FC2CF4A047C10E?tab=trade",
    "https://www.okx.com/copy-trading/account/B31CCBB35ADBF9C0?tab=trade",
    "https://www.okx.com/copy-trading/account/3F6FA12F6D099FEA?tab=trade",
    "https://www.okx.com/copy-trading/account/3DFF614AE5E0AE92?tab=trade",
    "https://www.okx.com/copy-trading/account/9C65CB446B25F5CC?tab=trade",
    "https://www.okx.com/copy-trading/account/7E21239BFA805866?tab=trade",
    "https://www.okx.com/copy-trading/account/24D8CE79A97FD35D?tab=trade",
    "https://www.okx.com/copy-trading/account/5CE58253DFAAF5CF?tab=trade",
    "https://www.okx.com/copy-trading/account/A06A1E6EFE75ECCD?tab=trade",
    "https://www.okx.com/copy-trading/account/0B839006AFCA7A52?tab=trade",
    "https://www.okx.com/copy-trading/account/D500A09517C4A154?tab=trade",
    "https://www.okx.com/copy-trading/account/247FE3434DA88B0D?tab=trade",
    "https://www.okx.com/copy-trading/account/08E31CADCFDDCFB8?tab=trade",
    "https://www.okx.com/copy-trading/account/4CB5596A9CF90DEA?tab=trade",
    "https://www.okx.com/copy-trading/account/9F09D843E575FA68?tab=trade",
    "https://www.okx.com/copy-trading/account/764043965032509720?tab=trade",
    "https://www.okx.com/copy-trading/account/E3680BE95285F87E?tab=trade",
    "https://www.okx.com/copy-trading/account/40A3DB1208A52D7D?tab=trade",
    "https://www.okx.com/copy-trading/account/53AEED5A8E4EBBB2?tab=trade",
    "https://www.okx.com/copy-trading/account/822824429641453680?tab=trade",
    "https://www.okx.com/copy-trading/account/6F2CA760327CA528?tab=trade",
    "https://www.okx.com/copy-trading/account/74F7C7A53CD18275?tab=trade",
    "https://www.okx.com/copy-trading/account/26E8167F37D30564?tab=trade",
    "https://www.okx.com/copy-trading/account/6F262ADB3B44266C?tab=trade",
    "https://www.okx.com/copy-trading/account/1894AF025DAA521A?tab=trade",
    "https://www.okx.com/copy-trading/account/A24E06C746B022B4?tab=trade",
    "https://www.okx.com/copy-trading/account/72AFDC179D66D034?tab=trade",
    "https://www.okx.com/copy-trading/account/80A2447E1FD16A12?tab=trade",
    "https://www.okx.com/copy-trading/account/130F1CFE28E7E467?tab=trade",
    "https://www.okx.com/copy-trading/account/14B24FC1CDA23436?tab=trade",
    "https://www.okx.com/copy-trading/account/517A2A0B4F4C76D6?tab=trade",
    "https://www.okx.com/copy-trading/account/96F4C7FA4260C891?tab=trade",
    "https://www.okx.com/copy-trading/account/9A07C62A15E47307?tab=trade",
    "https://www.okx.com/copy-trading/account/3EB985F124C18792?tab=trade",
    "https://www.okx.com/copy-trading/account/A53ABB45DE8437C5?tab=trade",
    "https://www.okx.com/copy-trading/account/041B49EE3E5F5C00?tab=trade",
    "https://www.okx.com/copy-trading/account/07AB446028582A4E?tab=trade",
    "https://www.okx.com/copy-trading/account/318EE7554752576C?tab=trade",
    "https://www.okx.com/copy-trading/account/91CCB52B97C20FA2?tab=trade",
    "https://www.okx.com/copy-trading/account/F740246F4C8BDC75?tab=trade",
    "https://www.okx.com/copy-trading/account/513536981821738399?tab=trade",
    "https://www.okx.com/copy-trading/account/5251484445FC52D8?tab=trade",
    "https://www.okx.com/copy-trading/account/F2EDD3086F9A651F?tab=trade",
    "https://www.okx.com/copy-trading/account/DA2B29551CBB2AE7?tab=trade",
    "https://www.okx.com/copy-trading/account/BE0DCCC5D9571E5A?tab=trade",
    "https://www.okx.com/copy-trading/account/5C872B837465159F?tab=trade",
    "https://www.okx.com/copy-trading/account/C024C3CB1B42E876?tab=trade",
    "https://www.okx.com/copy-trading/account/1499200359BAE11A?tab=trade",
    "https://www.okx.com/copy-trading/account/0FD18D81A6980710?tab=trade",
    "https://www.okx.com/copy-trading/account/70923A619CCB8F2F?tab=trade",
    "https://www.okx.com/copy-trading/account/C419F165132C0C57?tab=trade",
    "https://www.okx.com/copy-trading/account/4EA706D951ADCBED?tab=trade",
    "https://www.okx.com/copy-trading/account/2128BA01363B35A5?tab=trade",
    "https://www.okx.com/copy-trading/account/05F41A1FD4A0C520?tab=trade",
    "https://www.okx.com/copy-trading/account/DFC68810E340D687?tab=trade",
    "https://www.okx.com/copy-trading/account/36A47C886FB953EA?tab=trade",
    "https://www.okx.com/copy-trading/account/E1936A03E66777C6?tab=trade",
    "https://www.okx.com/copy-trading/account/A72B4B9C78845C00?tab=trade",
    "https://www.okx.com/copy-trading/account/0A97BA09396C4DC8?tab=trade",
    "https://www.okx.com/copy-trading/account/114A1793308A1CEB?tab=trade",
    "https://www.okx.com/copy-trading/account/643A3247025545B6?tab=trade",
    "https://www.okx.com/copy-trading/account/8D623C226208DA05?tab=trade",
    "https://www.okx.com/copy-trading/account/FEA1F20A4558468F?tab=trade",
]

CACHE = {
    "last_updated": None,
    "scanned_leaders": 0,
    "binance_count": 0,
    "okx_count": 0,
    "leaders": [],
}

API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.binance.com/",
}


def parse_links(links: list, exchange: str) -> list:
    seen_keys = set()
    parsed_items = []

    for raw in links:
        link = (raw or "").strip()
        if not link:
            continue

        u = urlparse(link)
        qs = parse_qs(u.query)
        path_parts = [p for p in u.path.split("/") if p]

        if exchange == "OKX" and "account" in path_parts:
            idx = path_parts.index("account")
            code = path_parts[idx + 1] if idx + 1 < len(path_parts) else path_parts[-1]
        else:
            code = path_parts[-1] if path_parts else link

        ref_code = (
            qs.get("uniqueCode", [None])[0]
            or qs.get("portfolioId", [None])[0]
            or qs.get("r", [None])[0]
        )

        primary_id = code if exchange == "OKX" else (ref_code or code)
        dedup_key = f"{exchange}:{primary_id.upper()}"

        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        short_label = f"{exchange[:2]}-{primary_id[:8]}"
        resolved_init = (
            primary_id
            if (primary_id.isdigit() and len(primary_id) >= 12)
            else (code if code.isdigit() and len(code) >= 12 else None)
        )

        parsed_items.append(
            {
                "id": primary_id,
                "resolved_id": resolved_init,
                "slug": code,
                "name": short_label,
                "url": link,
                "exchange": exchange,
                "aum": 0.0,
            }
        )

    return parsed_items


BINANCE_WATCHLIST = parse_links(BINANCE_RAW_LINKS, "BINANCE")
OKX_WATCHLIST = parse_links(OKX_RAW_LINKS, "OKX")


def normalize_symbol(raw_symbol: str) -> str:
    if not raw_symbol:
        return ""
    return (
        raw_symbol.upper()
        .replace("-SWAP", "")
        .replace("-FUTURES", "")
        .replace("-", "")
        .replace("/", "")
    )


def extract_number(obj: dict, keys: tuple, default: float = 0.0) -> float:
    for k in keys:
        val = obj.get(k)
        if val is not None and val != "":
            try:
                num = float(val)
                if num != 0:
                    return num
            except (ValueError, TypeError):
                pass
    return default


def extract_positions_list(payload: dict) -> list:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("list", "positions", "rows", "records", "items"):
            if isinstance(data.get(key), list):
                return data[key]
    for key in ("list", "positions", "rows", "records"):
        if isinstance(payload.get(key), list):
            return payload[key]
    return []


def parse_position_item(pos: dict, exchange: str) -> dict | None:
    if not isinstance(pos, dict):
        return None

    raw_sym = (
        pos.get("symbol")
        or pos.get("instId")
        or pos.get("pair")
        or pos.get("contractCode")
        or ""
    )
    symbol = normalize_symbol(raw_sym)
    if not symbol:
        return None

    amt = extract_number(
        pos,
        (
            "positionAmount",
            "posAmt",
            "pos",
            "sz",
            "size",
            "holdVol",
            "volume",
            "qty",
            "quantity",
        ),
        0.0,
    )
    raw_side = str(
        pos.get("positionSide")
        or pos.get("posSide")
        or pos.get("side")
        or pos.get("direction")
        or ""
    ).upper()

    if raw_side in ("LONG", "BUY"):
        side = "LONG"
    elif raw_side in ("SHORT", "SELL"):
        side = "SHORT"
    elif raw_side in ("BOTH", "NET", ""):
        if amt > 0:
            side = "LONG"
        elif amt < 0:
            side = "SHORT"
        else:
            return None
    else:
        return None

    entry_price = extract_number(
        pos,
        (
            "entryPrice",
            "avgEntryPrice",
            "avgCostPrice",
            "avgPx",
            "openPrice",
            "markPx",
            "markPrice",
        ),
        0.0,
    )
    notional = abs(
        extract_number(
            pos,
            (
                "notionalValue",
                "notional",
                "posValue",
                "positionValue",
                "margin",
                "imr",
            ),
            0.0,
        )
    )

    if notional <= 0 and entry_price > 0 and abs(amt) > 0:
        notional = abs(amt) * entry_price

    if abs(amt) == 0 and notional <= 0:
        return None

    return {
        "exchange": exchange,
        "symbol": symbol,
        "side": side,
        "notional": notional,
        "entry_price": entry_price,
        "amount": abs(amt),
    }


async def resolve_binance_portfolio_id(session: AsyncSession, leader: dict) -> str:
    if leader.get("resolved_id"):
        return str(leader["resolved_id"])

    candidate = str(leader["id"]).strip()
    if candidate.isdigit() and len(candidate) >= 12:
        leader["resolved_id"] = candidate
        return candidate

    try:
        resp = await session.get(
            leader["url"],
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            timeout=12,
            allow_redirects=True,
        )
        html = resp.text or ""
        patterns = [
            r'"portfolioId"\s*:\s*"?(\d{12,25})"?',
            r"portfolioId[\"'=\s:]+(\d{12,25})",
            r"portfolio-detail/(\d{12,25})",
        ]
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                found = m.group(1)
                leader["resolved_id"] = found
                print(f"[BINANCE ID OK] {leader['name']} -> {found}")
                return found

        final_url = str(resp.url)
        qs_final = parse_qs(urlparse(final_url).query)
        q_pid = (qs_final.get("portfolioId") or qs_final.get("r") or [None])[0]
        if q_pid and q_pid.isdigit() and len(q_pid) >= 12:
            leader["resolved_id"] = q_pid
            print(f"[BINANCE ID QUERY] {leader['name']} -> {q_pid}")
            return q_pid

        m_url = re.search(r"(\d{12,25})", final_url)
        if m_url:
            found = m_url.group(1)
            leader["resolved_id"] = found
            print(f"[BINANCE ID URL] {leader['name']} -> {found}")
            return found

        print(f"[BINANCE ID MISS] {leader['name']} status={resp.status_code} url={final_url[:90]}")
    except Exception as exc:
        print(f"[BINANCE ID ERR] {leader['name']}: {exc}")

    return candidate


async def fetch_binance_leader_positions(
    session: AsyncSession, semaphore: asyncio.Semaphore, leader: dict
) -> dict:
    parsed = []
    resolved_id = str(leader["id"])
    async with semaphore:
        try:
            await asyncio.sleep(0.25)
            resolved_id = await resolve_binance_portfolio_id(session, leader)

            candidates = [resolved_id]
            if leader.get("id") and str(leader["id"]) != resolved_id:
                candidates.append(str(leader["id"]))
            if leader.get("slug") and str(leader["slug"]) not in candidates:
                candidates.append(str(leader["slug"]))

            fetched_ok = False
            for pid_try in candidates:
                urls = [
                    "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/"
                    f"lead-data/positions?portfolioId={pid_try}",
                    "https://www.binance.com/bapi/futures/v1/public/future/copy-trade/"
                    f"lead-data/positions?portfolioId={pid_try}",
                ]
                for url in urls:
                    resp = await session.get(url, headers=API_HEADERS, timeout=12)
                    if resp.status_code != 200:
                        continue
                    try:
                        payload = resp.json()
                    except Exception:
                        continue

                    raw_list = extract_positions_list(payload)
                    if raw_list:
                        resolved_id = pid_try
                        leader["resolved_id"] = pid_try
                        for item in raw_list:
                            p = parse_position_item(item, "BINANCE")
                            if p:
                                parsed.append(p)
                        fetched_ok = True
                        break
                if fetched_ok:
                    break

            if not fetched_ok:
                print(f"[BINANCE EMPTY] {leader['name']} tried={candidates}")
        except Exception as exc:
            print(f"[BINANCE ERR] {leader['name']} ({resolved_id}): {exc}")

    return {
        "id": resolved_id,
        "name": leader["name"],
        "exchange": "BINANCE",
        "aum": float(leader.get("aum", 0.0) or 0.0),
        "positions": parsed,
    }


async def fetch_okx_leader_positions(
    session: AsyncSession, semaphore: asyncio.Semaphore, leader: dict
) -> dict:
    uid = str(leader["id"])
    urls = [
        f"https://www.okx.com/api/v5/copytrading/public-current-subpositions?uniqueCode={uid}&instType=SWAP",
        f"https://www.okx.com/priapi/v5/ecotrade/public/lead-trader/current-positions?uniqueCode={uid}",
    ]
    parsed = []
    async with semaphore:
        for url in urls:
            try:
                await asyncio.sleep(0.2)
                resp = await session.get(url, headers=API_HEADERS, timeout=12)
                raw_list = extract_positions_list(resp.json())
                if raw_list:
                    for item in raw_list:
                        p = parse_position_item(item, "OKX")
                        if p:
                            parsed.append(p)
                    break
            except Exception as exc:
                print(f"[OKX ERR] {uid}: {exc}")

    return {
        "id": uid,
        "name": leader["name"],
        "exchange": "OKX",
        "aum": float(leader.get("aum", 0.0) or 0.0),
        "positions": parsed,
    }


def build_coin_summary(leaders_data: list, min_aum: float, exchange_filter: str = "ALL"):
    coin_map = defaultdict(
        lambda: {
            "long_count": 0,
            "short_count": 0,
            "long_vol": 0.0,
            "short_vol": 0.0,
            "total_vol": 0.0,
            "long_weighted_entry_sum": 0.0,
            "long_entry_vol_sum": 0.0,
            "short_weighted_entry_sum": 0.0,
            "short_entry_vol_sum": 0.0,
            "traders": [],
        }
    )

    filtered_leaders = 0
    visible_leaders = 0
    ex_upper = exchange_filter.upper()

    for leader in leaders_data:
        if ex_upper != "ALL" and leader["exchange"] != ex_upper:
            continue
        if leader["aum"] < min_aum:
            continue

        filtered_leaders += 1
        positions = leader["positions"]
        if positions:
            visible_leaders += 1

        for p in positions:
            sym = p["symbol"]
            side = p["side"]
            notional = p["notional"]
            entry = p["entry_price"]

            if side == "LONG":
                coin_map[sym]["long_count"] += 1
                coin_map[sym]["long_vol"] += notional
                if entry > 0 and notional > 0:
                    coin_map[sym]["long_weighted_entry_sum"] += entry * notional
                    coin_map[sym]["long_entry_vol_sum"] += notional
            elif side == "SHORT":
                coin_map[sym]["short_count"] += 1
                coin_map[sym]["short_vol"] += notional
                if entry > 0 and notional > 0:
                    coin_map[sym]["short_weighted_entry_sum"] += entry * notional
                    coin_map[sym]["short_entry_vol_sum"] += notional
            else:
                continue

            coin_map[sym]["total_vol"] += notional
            coin_map[sym]["traders"].append(
                {
                    "id": leader["id"],
                    "name": leader["name"],
                    "exchange": leader["exchange"],
                    "aum": round(leader["aum"], 2),
                    "side": side,
                    "notional": round(notional, 2),
                    "entry_price": round(entry, 6) if entry > 0 else 0.0,
                }
            )

    formatted_coins = []
    for sym, d in coin_map.items():
        total = d["long_count"] + d["short_count"]
        long_pct = round((d["long_count"] / total) * 100, 1) if total > 0 else 0.0
        long_avg_entry = (
            d["long_weighted_entry_sum"] / d["long_entry_vol_sum"]
            if d["long_entry_vol_sum"] > 0
            else 0.0
        )
        short_avg_entry = (
            d["short_weighted_entry_sum"] / d["short_entry_vol_sum"]
            if d["short_entry_vol_sum"] > 0
            else 0.0
        )

        sorted_traders = sorted(d["traders"], key=lambda t: t["notional"], reverse=True)

        formatted_coins.append(
            {
                "symbol": sym,
                "total": total,
                "long_count": d["long_count"],
                "short_count": d["short_count"],
                "long_vol": round(d["long_vol"], 2),
                "short_vol": round(d["short_vol"], 2),
                "total_vol": round(d["total_vol"], 2),
                "long_avg_entry": round(long_avg_entry, 6),
                "short_avg_entry": round(short_avg_entry, 6),
                "long_pct": long_pct,
                "short_pct": round(100 - long_pct, 1),
                "traders": sorted_traders,
            }
        )

    formatted_coins.sort(key=lambda x: x["total"], reverse=True)
    return {
        "last_updated": CACHE["last_updated"],
        "scanned_leaders": len(leaders_data),
        "binance_count": CACHE["binance_count"],
        "okx_count": CACHE["okx_count"],
        "filtered_leaders": filtered_leaders,
        "visible_leaders": visible_leaders,
        "min_aum": min_aum,
        "exchange": ex_upper,
        "coins": formatted_coins,
    }


async def scanner_loop():
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    while True:
        try:
            async with AsyncSession(impersonate="chrome120") as session:
                bn_tasks = [
                    fetch_binance_leader_positions(session, semaphore, l)
                    for l in BINANCE_WATCHLIST
                ]
                okx_tasks = [
                    fetch_okx_leader_positions(session, semaphore, l)
                    for l in OKX_WATCHLIST
                ]
                results = await asyncio.gather(*(bn_tasks + okx_tasks))

                bn_active = sum(
                    1 for r in results if r["exchange"] == "BINANCE" and r["positions"]
                )
                okx_active = sum(
                    1 for r in results if r["exchange"] == "OKX" and r["positions"]
                )

                CACHE["last_updated"] = time.strftime("%H:%M:%S")
                CACHE["binance_count"] = len(BINANCE_WATCHLIST)
                CACHE["okx_count"] = len(OKX_WATCHLIST)
                CACHE["scanned_leaders"] = len(results)
                CACHE["leaders"] = results
                print(
                    f"[SCAN DONE] {CACHE['last_updated']} | "
                    f"BN active: {bn_active}/{len(BINANCE_WATCHLIST)} | "
                    f"OKX active: {okx_active}/{len(OKX_WATCHLIST)}"
                )
        except Exception as exc:
            print(f"[SCANNER LOOP ERR]: {exc}")

        await asyncio.sleep(SCAN_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scanner_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return JSONResponse(
        {
            "status": "ok",
            "last_updated": CACHE["last_updated"],
            "binance_unique": CACHE["binance_count"],
            "okx_unique": CACHE["okx_count"],
        }
    )


@app.get("/")
async def serve_ui():
    return FileResponse(Path("static/index.html"))


@app.get("/api/positions")
async def get_positions(
    min_aum: float = Query(default=DEFAULT_MIN_AUM, ge=0),
    exchange: str = Query(default="ALL"),
):
    return build_coin_summary(
        CACHE["leaders"], min_aum=min_aum, exchange_filter=exchange
    )
