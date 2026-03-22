# 핫딜 단가 수집기 - 크롤링 서버

## 지원 커뮤니티
- 뽐뿌 (ppomppu.co.kr)
- 에펨코리아 (fmkorea.com)
- 더쿠 (theqoo.net)
- 퀘이사존 (quasarzone.com)
- 네이버카페 (알구몬 경유 - 직접 접근 불가)

---

## Render.com 무료 배포 방법

### 1단계 - GitHub에 업로드
```
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_ID/hotdeal-crawler.git
git push -u origin main
```

### 2단계 - Render.com 설정
1. https://render.com 접속 → New → Web Service
2. GitHub 레포 연결
3. 아래 설정 입력:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
4. Deploy 클릭

### 3단계 - 배포 완료 후
배포된 URL (예: `https://hotdeal-crawler.onrender.com`)을  
앱의 **외부 수집 API 설정** 란에 입력하면 됩니다.

---

## API 사용법

### 기본 검색
```
GET /search?keyword=사과
```

### 특정 커뮤니티만 검색
```
GET /search?keyword=사과&communities=뽐뿌,퀘이사존
```

### 응답 예시
```json
{
  "keyword": "사과",
  "communities": ["뽐뿌", "에펨코리아"],
  "total": 5,
  "results": [
    {
      "community": "뽐뿌",
      "title": "[쿠팡] 사과 5kg 12,900원",
      "price": 12900,
      "price_text": "12,900원",
      "link": "https://www.ppomppu.co.kr/..."
    }
  ]
}
```

### 상태 확인
```
GET /health
```

---

## 로컬 테스트

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000/search?keyword=사과
```

---

## ⚠️ 주의사항
- Render.com 무료 플랜은 15분 비활성 시 슬립 상태 진입 (첫 요청 느릴 수 있음)
- 네이버카페는 로그인 필요로 직접 크롤링 불가 → 알구몬 경유
- 사이트 구조 변경 시 셀렉터 수정 필요
