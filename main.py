from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
import asyncio
import re
from typing import Optional

app = FastAPI(title="핫딜 단가 수집기 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def extract_price(text: str) -> Optional[int]:
    """텍스트에서 가격(숫자) 추출"""
    text = text.replace(",", "").replace(" ", "")
    matches = re.findall(r"\d{3,}", text)
    if matches:
        return int(matches[0])
    return None


# ─── 뽐뿌 ───────────────────────────────────────────────────────────────
async def crawl_ppomppu(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    results = []
    try:
        url = f"https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu&search_type=subject&keyword={keyword}"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr.baseList, tr.baseList-e")
        for row in rows[:20]:
            title_el = row.select_one("a.baseList-title")
            price_el = row.select_one("td.baseList-space")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            price_text = price_el.get_text(strip=True) if price_el else ""
            price = extract_price(price_text)
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
        url = f"https://www.fmkorea.com/index.php?mid=hotdeal&search_keyword={keyword}&search_target=title"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select("li.li_hotdeal_pop1, td.title a")
        rows = soup.select("table.bd_lst tr")
        for row in rows:
            title_el = row.select_one("td.title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            # 가격은 제목에서 추출 (에펨코리아 핫딜 특성)
            price = extract_price(title)
            href = title_el.get("href", "")
            link = "https://www.fmkorea.com" + href if href.startswith("/") else href
            if keyword.lower() in title.lower():
                results.append({
                    "community": "에펨코리아",
                    "title": title,
                    "price": price,
                    "price_text": "",
                    "link": link,
                })
    except Exception as e:
        print(f"[에펨코리아 오류] {e}")
    return results


# ─── 더쿠 ───────────────────────────────────────────────────────────────
async def crawl_theqoo(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    results = []
    try:
        url = f"https://theqoo.net/index.php?mid=hotdeal&search_keyword={keyword}&search_target=title"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table.bd_lst tr")
        for row in rows:
            title_el = row.select_one("td.title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            price = extract_price(title)
            href = title_el.get("href", "")
            link = "https://theqoo.net" + href if href.startswith("/") else href
            if keyword.lower() in title.lower():
                results.append({
                    "community": "더쿠",
                    "title": title,
                    "price": price,
                    "price_text": "",
                    "link": link,
                })
    except Exception as e:
        print(f"[더쿠 오류] {e}")
    return results


# ─── 퀘이사존 ───────────────────────────────────────────────────────────
async def crawl_quasarzone(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    results = []
    try:
        url = f"https://quasarzone.com/bbs/qb_saleinfo?sca=&sfl=wr_subject&stx={keyword}"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("div.market-info-list-wrap li, ul.market-info-list li")
        for row in rows:
            title_el = row.select_one("p.tit a, .title a")
            price_el = row.select_one("span.price, .market-price")
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


# ─── 네이버카페 (알구몬 경유) ──────────────────────────────────────────
async def crawl_naver_via_algomon(keyword: str, client: httpx.AsyncClient) -> list[dict]:
    """
    네이버카페는 로그인 필요로 직접 접근 불가.
    알구몬(algomon.com)을 통해 핫딜 데이터를 수집.
    """
    results = []
    try:
        url = f"https://www.algomon.com/search?keyword={keyword}&category=hotdeal"
        r = await client.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".product-item, .deal-item, article")
        for item in items[:20]:
            title_el = item.select_one("h2, h3, .title, .name")
            price_el = item.select_one(".price, .cost, [class*='price']")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            price_text = price_el.get_text(strip=True) if price_el else ""
            price = extract_price(price_text)
            link_tag = item.select_one("a")
            link = link_tag.get("href", "") if link_tag else ""
            results.append({
                "community": "알구몬(네이버카페)",
                "title": title,
                "price": price,
                "price_text": price_text,
                "link": link,
            })
    except Exception as e:
        print(f"[알구몬 오류] {e}")
    return results


# ─── 엔드포인트 ─────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "핫딜 단가 수집기 API가 실행 중입니다."}


@app.get("/search")
async def search(
    keyword: str = Query(..., description="검색할 키워드"),
    communities: str = Query(
        default="뽐뿌,에펨코리아,더쿠,퀘이사존,네이버카페",
        description="쉼표로 구분된 커뮤니티 목록"
    ),
):
    """
    키워드로 여러 커뮤니티 핫딜 탭을 동시에 검색합니다.

    - **keyword**: 검색 키워드 (예: 사과, 노트북)
    - **communities**: 검색할 커뮤니티 (쉼표 구분, 기본값: 전체)

    Returns: 각 커뮤니티별 단가 목록
    """
    selected = [c.strip() for c in communities.split(",")]

    crawlers = {
        "뽐뿌": crawl_ppomppu,
        "에펨코리아": crawl_fmkorea,
        "더쿠": crawl_theqoo,
        "퀘이사존": crawl_quasarzone,
        "네이버카페": crawl_naver_via_algomon,
    }

    async with httpx.AsyncClient() as client:
        tasks = [
            crawlers[name](keyword, client)
            for name in selected
            if name in crawlers
        ]
        all_results = await asyncio.gather(*tasks)

    flat = [item for sublist in all_results for item in sublist]

    # 가격 있는 항목 앞으로 정렬
    flat.sort(key=lambda x: (x["price"] is None, x["price"] or 0))

    return {
        "keyword": keyword,
        "communities": selected,
        "total": len(flat),
        "results": flat,
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
