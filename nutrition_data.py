import sys
print(sys.executable)
import os
import time
import requests
import pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__)))
# ======= 1. 設定路徑 & 讀取 Food-101 類別 =======
DATA_DIR = "./"          
META_DIR = "./"
classes_txt = os.path.join(META_DIR, "classes.txt")

with open(classes_txt, "r") as f:
    food101_classes = [line.strip() for line in f.readlines()]

print("Food-101 類別數量：", len(food101_classes))
print("前 5 個：", food101_classes[:5])

# ======= 2. 類別名稱 → 查詢名稱 mapping =======
# 預設：把底線改成空白
def default_query_name(cls_name: str) -> str:
    return cls_name.replace("_", " ")

# 如有特殊要修正的可以在這裡加
NAME_OVERRIDE = {
    # "fish_and_chips": "fish and chips",   # 其實 replace 就夠了，示意而已
}

def to_query_name(cls_name: str) -> str:
    return NAME_OVERRIDE.get(cls_name, default_query_name(cls_name))

# ======= 3. USDA API 設定 =======
USDA_API_KEY = "your_api_key" 
BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# 我們需要使用的 nutrientNumber：
# 208: 能量 (kcal)
# 203: 蛋白質 (g)
# 204: 脂肪 (g)
# 205: 碳水化合物 (g)
# 301: 鈣 (mg)
# 318: 維生素A (µg)
# 401: 維生素C (mg)
TARGET_NUTRIENTS = {
    "208": "kcal",
    "203": "protein_g",
    "204": "fat_g",
    "205": "carbs_g",
    "301": "calcium_mg",
    "318": "vitaminA_ug",
    "401": "vitaminC_mg",
}

def fetch_nutrition_from_usda(query_name: str, api_key: str, max_tries: int = 3):
    """對 USDA API 查詢一個食物名稱，回傳食物 nutrient 字典（可能為 None）"""
    params = {
        "api_key": api_key,
        "query": query_name,
        "pageSize": 1,   # 只取第一筆
    }

    for attempt in range(max_tries):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            foods = data.get("foods", [])
            if not foods:
                print(f"[WARN] 查不到食物：{query_name}")
                return None

            first_food = foods[0]
            nutrients = first_food.get("foodNutrients", [])

            result = {}
            for item in nutrients:
                num = item.get("nutrientNumber")
                if num in TARGET_NUTRIENTS:
                    key = TARGET_NUTRIENTS[num]
                    result[key] = item.get("value", None)

            return result

        except Exception as e:
            print(f"[ERROR] 查詢 {query_name} 失敗，嘗試 {attempt+1}/{max_tries}：{e}")
            time.sleep(1)

    return None

# ======= 4. 對 101 類逐一查詢，整理成 DataFrame =======
rows = []

for cls in food101_classes:
    qname = to_query_name(cls)
    print(f"查詢：{cls}  →  '{qname}'")

    nutri = fetch_nutrition_from_usda(qname, USDA_API_KEY)
    if nutri is None:
        # 查不到就記錄空值
        nutri = {v: None for v in TARGET_NUTRIENTS.values()}

    row = {
        "food101_class": cls,   # e.g. "apple_pie"
        "query_name": qname,    # e.g. "apple pie"
    }
    row.update(nutri)
    rows.append(row)

    time.sleep(0.2)

nutrition_df = pd.DataFrame(rows)
print(nutrition_df.head())

# ======= 5. 儲存成 CSV=======
out_path = os.path.join(DATA_DIR, "nutrition_food101.csv")
nutrition_df.to_csv(out_path, index=False, encoding="utf-8")
print("已儲存營養表：", out_path)
