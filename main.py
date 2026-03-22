import os
import sys
print("서버 시작", flush=True, file=sys.stderr)
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
import asyncio
import re
from typing import Optional
from urllib.parse import quote

app = FastAPI(title="핫딜 단가 수집기 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 네이버 카페별 cafeId
NAVER_CAFE_IDS = {
    "맘이베베": 29434212,
    "맘스홀릭": 10094499,
    "몰테일스토리": 21820768,
}


def extract_price(text: str) -> Optional[int]:
    text = text.replace(",", "").replace(" ", "")
    matches = re.findall(r"\d{3,}", text)
    if matches:
        return int(matches[0])
    return None


# ─── 네이버 Open API (카페 검색) ────────────────────────────────────────
async def crawl_naver_cafe_api(
    keyword: str,
    client: httpx.AsyncClient,
    cafe_name: str,
) -> list[dict]:
    results = []
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print(f"[{cafe_name}] 네이버 API 키 없음", flush=True)
        return results
    try:
        cafe_id = NAVER_CAFE_IDS.get(cafe_name)
        # 카페명 + 키워드로 검색
        query = keyword
        url = (
            f"https://openapi.naver.com/v1/search/cafearticle.json"
            f"?query={quote(query)}&display=20&start=1&sort=date"
        )
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        r = await client.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"[{cafe_name}] API 오류 {r.status_code}: {r.text}")
            return results

        data = r.json()
        items = data.get("items", [])
        print(f"[{cafe_name}] API 응답 건수: {len(items)}")
        if items:
            print(f"[{cafe_name}] 샘플 링크: {items[0].get('link','')}")

        for item in items:
            link = item.get("link", "")
            cafe_id_val = NAVER_CAFE_IDS.get(cafe_name)
            if cafe_id_val and str(cafe_id_val) not in link:
                continue
            title = re.sub(r"<[^>]+>", "", item.get("title", ""))
            price = extract_price(title)
            results.append({
                "community": cafe_name,
                "title": title,
                "price": price,
                "price_text": "",
                "link": link,
            })
        print(f"[{cafe_name}] 필터 후 건수: {len(results)}")
    except Exception as e:
        print(f"[{cafe_name} 오류] {e}")
    return results


async def crawl_mam_ibebe(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    return await crawl_naver_cafe_api(keyword, client, "맘이베베")

async def crawl_momsholic(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    return await crawl_naver_cafe_api(keyword, client, "맘스홀릭")

async def crawl_malltail(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    return await crawl_naver_cafe_api(keyword, client, "몰테일스토리")


# ─── 뽐뿌 ───────────────────────────────────────────────────────────────
async def crawl_ppomppu(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    results = []
    try:
        url = f"https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu&search_type=subject&keyword={quote(keyword)}"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr.baseList, tr.baseList-e")
        for row in rows[:20]:
            title_el = row.select_one("a.baseList-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            price_match = re.search(r'[\d,]+원', title)
            price_text = price_match.group(0) if price_match else ""
            price = extract_price(price_text) if price_text else None
            link_tag = title_el.get("href", "")
            link = "https://www.ppomppu.co.kr/zboard/" + link_tag if link_tag else ""
            if keyword.lower() in title.lower():
                results.append({
                    "community": "뽐뿌",
                    "title": title,
                    "price": price,
                    "price_text": price_text,
                    "link": link,
                })
    except Exception as e:
        print(f"[뽐뿌 오류] {e}")
    return results


# ─── 에펨코리아 ─────────────────────────────────────────────────────────
async def crawl_fmkorea(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    results = []
    try:
        url = f"https://www.fmkorea.com/index.php?mid=hotdeal&search_keyword={quote(keyword)}&search_target=title"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table.bd_lst tr")
        for row in rows:
            title_el = row.select_one("td.title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            price_match = re.search(r'[\d,]+원', title)
            price_text = price_match.group(0) if price_match else ""
            price = extract_price(price_text) if price_text else None
            href = title_el.get("href", "")
            link = "https://www.fmkorea.com" + href if href.startswith("/") else href
            if keyword.lower() in title.lower():
                results.append({
                    "community": "에펨코리아",
                    "title": title,
                    "price": price,
                    "price_text": price_text,
                    "link": link,
                })
    except Exception as e:
        print(f"[에펨코리아 오류] {e}")
    return results


# ─── 더쿠 ───────────────────────────────────────────────────────────────
async def crawl_theqoo(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    results = []
    try:
        url = f"https://theqoo.net/index.php?mid=hotdeal&search_keyword={quote(keyword)}&search_target=title"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table.bd_lst tr")
        for row in rows:
            title_el = row.select_one("td.title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            price_match = re.search(r'[\d,]+원', title)
            price_text = price_match.group(0) if price_match else ""
            price = extract_price(price_text) if price_text else None
            href = title_el.get("href", "")
            link = "https://theqoo.net" + href if href.startswith("/") else href
            if keyword.lower() in title.lower():
                results.append({
                    "community": "더쿠",
                    "title": title,
                    "price": price,
                    "price_text": price_text,
                    "link": link,
                })
    except Exception as e:
        print(f"[더쿠 오류] {e}")
    return results


# ─── 퀘이사존 ───────────────────────────────────────────────────────────
async def crawl_quasarzone(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    results = []
    try:
        url = f"https://quasarzone.com/bbs/qb_saleinfo?sca=&sfl=wr_subject&stx={quote(keyword)}"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("div.market-info-list-wrap li, ul.market-info-list li, .market-info-cont")
        for row in rows:
            title_el = row.select_one("p.tit a, .tit a, h1 a, h2 a, h3 a")
            price_el = row.select_one("span.price, .market-price, .price")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            price_text = price_el.get_text(strip=True) if price_el else ""
            price = extract_price(price_text) if price_text else extract_price(title)
            href = title_el.get("href", "")
            link = "https://quasarzone.com" + href if href.startswith("/") else href
            if keyword.lower() in title.lower():
                results.append({
                    "community": "퀘이사존",
                    "title": title,
                    "price": price,
                    "price_text": price_text,
                    "link": link,
                })
    except Exception as e:
        print(f"[퀘이사존 오류] {e}")
    return results


# ─── 엔드포인트 ─────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "핫딜 단가 수집기 API가 실행 중입니다."}


@app.get("/search")
async def search(
    keyword: str = Query(..., description="검색할 키워드"),
    communities: str = Query(
        default="뽐뿌,에펨코리아,더쿠,퀘이사존,맘이베베,맘스홀릭,몰테일스토리",
        description="쉼표로 구분된 커뮤니티 목록"
    ),
):
    selected = [c.strip() for c in communities.split(",")]

    crawlers = {
        "뽐뿌": crawl_ppomppu,
        "에펨코리아": crawl_fmkorea,
        "더쿠": crawl_theqoo,
        "퀘이사존": crawl_quasarzone,
        "맘이베베": crawl_mam_ibebe,
        "맘스홀릭": crawl_momsholic,
        "몰테일스토리": crawl_malltail,
    }

    async with httpx.AsyncClient() as client:
        tasks = [
            crawlers[name](keyword, client)
            for name in selected
            if name in crawlers
        ]
        all_results = await asyncio.gather(*tasks)

    flat = [item for sublist in all_results for item in sublist]
    flat.sort(key=lambda x: (x["price"] is None, x["price"] or 0))

    return {
        "keyword": keyword,
        "communities": selected,
        "total": len(flat),
        "results": flat,
    }

@app.get("/test-naver")
async def test_naver():
    client_id = os.environ.get("NAVER_CLIENT_ID", "")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
    if not client_id:
        return {"ok": False, "message": "API 키 없음"}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://openapi.naver.com/v1/search/cafearticle.json?query=사과&display=3",
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            timeout=10
        )
        return {"status": r.status_code, "body": r.json()}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

저장 후 배포 완료되면:
```
https://hotdeal-crawler.onrender.com/test-naver
@app.get("/health")
async def health():
    return {"status": "healthy"}
