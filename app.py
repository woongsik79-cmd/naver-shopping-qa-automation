import time
import re
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
from openpyxl.styles import Alignment  # 엑셀 정렬 라이브러리 추가


def setup_driver():
    chromedriver_autoinstaller.install()
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    driver.implicitly_wait(3)
    return driver


# 카테고리 설정 (네이버 선물샵 기반) 오타, 해당 카테고리 여부 확인 필수
CATEGORY_MAP = {
    "전체": [None],
    "e쿠폰": [
        "전체",
        "상품권",
        "카페/디저트",
        "치킨/피자",
        "편의점",
        "아이스크림/빙수",
        "생활편의",
        "뮤직/컨텐츠",
        "외식",
        "데이터/통화",
    ],
    "꽃배달": ["전체", "생화", "화환/난"],
    "카페·디저트": ["전체", "교환권", "배송"],
    "과일": [None],
    "한우": [None],
    "뷰티": [
        "전체",
        "스킨케어",
        "향수",
        "핸드/네일케어",
        "바디/헤어케어",
        "메이크업",
        "멘즈뷰티",
        "뷰티용품",
    ],
    "패션": [
        "전체",
        "의류",
        "주얼리",
        "시계",
        "가방/지갑",
        "모자/벨트/장갑/양말",
        "기타 액세서리",
        "신발",
    ],
    "리빙·생활": [
        "전체",
        "가구",
        "주방용품",
        "침구/패브릭",
        "조명",
        "홈프래그런스",
        "인테리어 소품",
        "리빙 생활용품",
        "생필품",
    ],
    "바디케어": [None],
    "이벤트·파티": ["전체", "파티의상", "파티용품", "게임"],
    "식품": [
        "전체",
        "과일",
        "견과류",
        "채소/곡물",
        "고기",
        "수산",
        "밀키트",
        "가공식품",
        "디저트",
        "차/커피",
        "음료",
        "전통주",
    ],
    "건강식품": ["전체", "홍삼/인삼/꿀", "영양제", "건강즙/과일즙", "다이어트"],
    "디지털·가전": [
        "전체",
        "건강용품",
        "음향기기",
        "계절가전",
        "생활가전",
        "주방가전",
        "미용가전",
        "PC/모바일기기",
        "폰/태블릿케이스/액세서리",
        "게임기/타이틀",
        "마우스/키보드",
        "기타 디지털기기",
    ],
    "음향기기": [None],
    "레저·자동차": ["전체", "헬스/요가", "골프", "캠핑", "아웃도어", "자동차"],
    "도서": [
        "전체",
        "경제/경영",
        "자기계발",
        "인문",
        "소설",
        "시/에세이",
        "어린이",
        "유아",
        "초등학교 참고서",
        "중학교 참고서",
        "고등학교 참고서",
    ],
    "캔들·디퓨저": [None],
    "유아동": [
        "전체",
        "완구/교구",
        "가구",
        "액세서리",
        "실내/외출용품",
        "출산/육아용품",
        "분유/이유식/간식",
        "기저귀/물티슈",
        "임산부",
        "의류",
    ],
    "라인프렌즈": [None],
    "웹툰굿즈": [None],
}
MAIN_ORDER = list(CATEGORY_MAP.keys())
SORT_ORDER = ["낮은 가격순", "높은 가격순"]


def collect_items_strict(driver, limit=30):
    results = []
    seen_names = set()
    time.sleep(0.8)  # 0.6 ~ 0.8 사이가 적당
    for scroll_attempt in range(10):  # 5 ~ 10회 적당
        last_height = driver.execute_script("return document.body.scrollHeight")
        items = driver.find_elements(
            By.XPATH,
            "//li[descendant::strong] | //div[contains(@class, 'item') and descendant::strong]",
        )
        for item in items:
            try:
                name_el = item.find_element(By.TAG_NAME, "strong")
                name = name_el.text.strip().split("\n")[-1]
                if "광고" in item.text or len(name) < 2 or name in seen_names:
                    continue
                price_all = re.findall(r"(\d{1,3}(,\d{3})*)원", item.text)
                if not price_all:
                    continue
                final_price = int(price_all[-1][0].replace(",", ""))
                seen_names.add(name)
                results.append((name, final_price))
                if len(results) >= limit:
                    return results[:limit]
            except:
                continue
        driver.execute_script("window.scrollBy(0, 2500);")
        time.sleep(0.7)
        if driver.execute_script("return document.body.scrollHeight") == last_height:
            break
    return results


if __name__ == "__main__":
    all_category_data = {main: [] for main in MAIN_ORDER}
    m_idx, s_idx = 0, 0

    while m_idx < len(MAIN_ORDER):
        driver = setup_driver()
        wait = WebDriverWait(driver, 10)
        try:
            driver.get("https://shopping.naver.com/gift/category")
            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(., '상품 카테고리')]")
                )
            ).click()
            time.sleep(1)

            while m_idx < len(MAIN_ORDER):
                main = MAIN_ORDER[m_idx]
                print(f"\n{'='*50}\n[대분류] {main} 진입")
                clean_main = main.replace("·", "")
                try:
                    m_btn = wait.until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                f"//div[contains(@class,'category')]//button[contains(., '{clean_main[:2]}')]",
                            )
                        )
                    )
                    driver.execute_script("arguments[0].click();", m_btn)
                    time.sleep(1)
                except:
                    m_idx += 1
                    continue

                subs = CATEGORY_MAP[main]
                while s_idx < len(subs):
                    sub = subs[s_idx]
                    sub_label = sub if sub else "전체"
                    print(f"  ▶ [소분류] {sub_label}")
                    if sub:
                        try:
                            s_btn = wait.until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        f"(//div[contains(@class,'category')])[2]//button[text()='{sub}']",
                                    )
                                )
                            )
                            driver.execute_script("arguments[0].click();", s_btn)
                            time.sleep(0.8)
                        except:
                            s_idx += 1
                            continue

                    for sort in SORT_ORDER:
                        sort_btn = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, f"//button[contains(., '{sort}')]")
                            )
                        )
                        driver.execute_script("arguments[0].click();", sort_btn)
                        search_time = datetime.now().strftime("%H:%M:%S")
                        collected = collect_items_strict(driver, 30)

                        if len(collected) == 0:  # 수집 0개 -> 크롤링 터짐
                            print(f"      ⚠️ 수집 0개. 재시작 시도.")  # 로그 후 재시작
                            raise Exception("ZeroDataError")

                        print(f"      └ {sort}: {len(collected)}개 완료")
                        for i, (name, price) in enumerate(collected):
                            status, note = "PASS", ""
                            if i > 0:
                                if (
                                    sort == "낮은 가격순"
                                    and price < collected[i - 1][1]
                                ) or (sort == "높은 가격순" and price > collected[i - 1][1]):
                                    status, note = (
                                        "FAIL",
                                        f"이전가격({collected[i-1][1]}) 위반",
                                    )

                            all_category_data[main].append(
                                {
                                    "대분류": main,
                                    "소분류": sub_label,
                                    "정렬": sort,
                                    "순위": f"{i + 1}위",
                                    "상품명": name,
                                    "가격": f"{price:,}원",
                                    "탐색시간": search_time,
                                    "결과": status,
                                    "비고": note,
                                    "raw_price": price,
                                }
                            )
                    s_idx += 1
                m_idx += 1
                s_idx = 0
            driver.quit()
            break
        except Exception as e:
            driver.quit()
            time.sleep(2)
            continue

    # Excel 저장
    if any(all_category_data.values()):
        fname = f"Naver_Gift_Final_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
        with pd.ExcelWriter(fname, engine="openpyxl") as writer:
            for cat, items in all_category_data.items():
                if items:
                    df = pd.DataFrame(items)
                    if "raw_price" in df.columns:
                        df = df.drop(columns=["raw_price"])  # 검사용 데이터 삭제

                    sheet_name = re.sub(r"[\\/*?:\[\]]", "", cat)[:30]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

                    worksheet = writer.sheets[sheet_name]
                    #  첫 줄 가운데 정렬 및 열 너비 조정
                    for idx, col_name in enumerate(df.columns):
                        cell = worksheet.cell(row=1, column=idx + 1)
                        cell.alignment = Alignment(
                            horizontal="center", vertical="center"
                        )  # 가운데 정렬

                        # 열 너비 조정
                        data_len = df[col_name].astype(str).map(len).max()
                        max_len = min(max(data_len, len(col_name)) + 5, 60)
                        worksheet.column_dimensions[chr(65 + idx)].width = max_len

        print(f"\n✨ 완료. 파일명: {fname}")
