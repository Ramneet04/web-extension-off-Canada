# Run this in google collab to create a DuckDB database file.
!pip install duckdb pandas -q
print("✅ Done")

import re, json, time
import pandas as pd
import duckdb

PARQUET  = "/content/0000.parquet"
DB_PATH  = "/content/off_v2.duckdb"
IMG_BASE = ""  # store path only: 327/408/000/5003/1.400.jpg

NUTRIENTS = ['energy-kcal', 'energy', 'fat', 'saturated-fat',
             'carbohydrates', 'sugars', 'fiber', 'proteins', 'salt', 'sodium']

def parse_duckdb_struct(s):
    if not s or s == '[]':
        return []
    s = str(s).strip()
    s = s.replace('NULL', '"__NULL__"')
    s = re.sub(
        r"(:\s*)([^',\{\}\[\]]+?)(\s*[,\}])",
        lambda m: m.group(1) + "'" + m.group(2).strip() + "'" + m.group(3),
        s
    )
    s = s.replace("\\'", '__APOS__')
    s = re.sub(r"'([^']*)'", lambda m: '"' + m.group(1) + '"', s)
    s = s.replace('__APOS__', "'")
    s = s.replace('"__NULL__"', 'null')
    try:
        result = json.loads(s)
        return result if isinstance(result, list) else []
    except Exception:
        return []

def process_row(pn_raw, ing_raw, nut_raw, img_raw, code):
    """Process all struct fields for a single row in one pass."""
    result = {}

    
    pn_items = parse_duckdb_struct(pn_raw)
    result['product_name_en'] = None
    result['product_name_fr'] = None
    result['product_name']    = None
    for lang in ['en', 'fr', 'main']:
        for item in pn_items:
            if isinstance(item, dict) and item.get('lang') == lang:
                t = item.get('text')
                if t and t != 'null':
                    if lang == 'en' and not result['product_name_en']:
                        result['product_name_en'] = t
                    elif lang == 'fr' and not result['product_name_fr']:
                        result['product_name_fr'] = t
                    elif lang == 'main' and not result['product_name']:
                        result['product_name'] = t
    result['product_name'] = (result['product_name_en'] or
                               result['product_name_fr'] or
                               result['product_name'] or
                               (pn_items[0].get('text') if pn_items else None))

    
    ing_items = parse_duckdb_struct(ing_raw)
    result['ingredients_en'] = None
    result['ingredients_fr'] = None
    result['ingredients_text'] = None
    for item in ing_items:
        if not isinstance(item, dict):
            continue
        lang = item.get('lang')
        t = item.get('text')
        if not t or t == 'null':
            continue
        if lang == 'en' and not result['ingredients_en']:
            result['ingredients_en'] = t
        elif lang == 'fr' and not result['ingredients_fr']:
            result['ingredients_fr'] = t
        elif lang == 'main' and not result['ingredients_text']:
            result['ingredients_text'] = t
    result['ingredients_text'] = (result['ingredients_en'] or
                                   result['ingredients_fr'] or
                                   result['ingredients_text'])

    
    nut_items = parse_duckdb_struct(nut_raw)
    nut_map = {}
    for item in nut_items:
        if isinstance(item, dict):
            name = item.get('name')
            val  = item.get('100g')
            if name and val and val != 'null':
                try:
                    nut_map[name] = float(val)
                except (ValueError, TypeError):
                    pass
    for n in NUTRIENTS:
        result[n.replace('-','_') + '_100g'] = nut_map.get(n)


    result['image_url'] = None
    if img_raw and 'front' in str(img_raw):
        img_items = parse_duckdb_struct(img_raw)
        imgid = None
        for prefix in ['front_en', 'front_fr', 'front_', 'front']:
            for item in img_items:
                if not isinstance(item, dict):
                    continue
                key = str(item.get('key', ''))
                if key.startswith(prefix) or key == prefix:
                    candidate = item.get('imgid')
                    if candidate and str(candidate) != 'null':
                        imgid = candidate
                        break
            if imgid:
                break
        if imgid:
            c = str(code)
            path = f"{c[:3]}/{c[3:6]}/{c[6:9]}/{c[9:]}" if len(c) > 8 else c
            result["image_url"] = f"{path}/{imgid}.400.jpg"

    return result


test_pn  = "[{'lang': main, 'text': Chamomile Herbal Tea}, {'lang': en, 'text': Chamomile Herbal Tea}]"
test_nut = "[{'name': saturated-fat, 'value': 10.0, '100g': 10.0, 'serving': NULL, 'unit': g, 'prepared_value': NULL, 'prepared_100g': NULL, 'prepared_serving': NULL, 'prepared_unit': NULL}]"
test_img = "[{'key': front_fr, 'imgid': 1, 'rev': 4, 'sizes': {'100': {'h': 100, 'w': 75}}, 'uploaded_t': NULL, 'uploader': NULL}]"
r = process_row(test_pn, "[{'lang': en, 'text': CHAMOMILE FLOWERS.}]", test_nut, test_img, '3274080005003')

print("=== PARSER TESTS ===")
print(f"product_name:    {r['product_name']}")
print(f"product_name_en: {r['product_name_en']}")
print(f"ingredients_en:  {r['ingredients_en']}")
print(f"sat_fat_100g:    {r['saturated_fat_100g']}")
print(f"image_url:       {r['image_url']}")
print("✅ Parser working!" if all(v is not None for v in [r['product_name'], r['image_url'], r['saturated_fat_100g']]) else "❌ Parser broken!")


con = duckdb.connect(DB_PATH)
con.execute("PRAGMA threads=4")
con.execute("PRAGMA memory_limit='12GB'")
con.execute("DROP TABLE IF EXISTS products_raw")
con.execute("DROP TABLE IF EXISTS products")

BASE_WHERE = """
    product_name IS NOT NULL
    AND len(product_name) > 0
    AND CAST(images AS VARCHAR) ILIKE '%front%'
    AND (obsolete IS NULL OR obsolete = false)
"""

def raw_select(country):
    return f"""
        code,
        CAST(product_name AS VARCHAR)                       AS pn_raw,
        TRY_CAST(brands AS VARCHAR)                         AS brands,
        lang,
        CAST(languages_tags AS VARCHAR)                     AS languages_tags,
        TRY_CAST(quantity AS VARCHAR)                       AS product_quantity,
        TRY_CAST(serving_size AS VARCHAR)                   AS serving_size,
        TRY_CAST(nutrition_data_per AS VARCHAR)             AS nutrition_data_per,
        TRY_CAST(nutriscore_grade AS VARCHAR)               AS nutriscore_grade,
        TRY_CAST(nutriscore_score AS INTEGER)               AS nutriscore_score,
        TRY_CAST(nova_group AS INTEGER)                     AS nova_group,
        TRY_CAST(nova_groups AS VARCHAR)                    AS nova_groups,
        TRY_CAST(ecoscore_grade AS VARCHAR)                 AS ecoscore_grade,
        TRY_CAST(ecoscore_score AS INTEGER)                 AS ecoscore_score,
        CAST(ingredients_text AS VARCHAR)                   AS ing_raw,
        CAST(ingredients_analysis_tags AS VARCHAR)          AS ingredients_analysis_tags,
        TRY_CAST(ingredients_n AS INTEGER)                  AS ingredients_n,
        TRY_CAST(additives_n AS INTEGER)                    AS additives_n,
        CAST(additives_tags AS VARCHAR)                     AS additives_tags,
        TRY_CAST(with_sweeteners AS INTEGER)                AS with_sweeteners,
        TRY_CAST(with_non_nutritive_sweeteners AS INTEGER)  AS with_non_nutritive_sweeteners,
        TRY_CAST(ingredients_from_palm_oil_n AS INTEGER)    AS ingredients_from_palm_oil_n,
        TRY_CAST(no_nutrition_data AS BOOLEAN)              AS no_nutrition_data,
        CAST(categories_tags AS VARCHAR)                    AS categories_tags,
        CAST(food_groups_tags AS VARCHAR)                   AS food_groups_tags,
        CAST(labels_tags AS VARCHAR)                        AS labels_tags,
        TRY_CAST(labels AS VARCHAR)                         AS labels,
        CAST(allergens_tags AS VARCHAR)                     AS allergens_tags,
        CAST(traces_tags AS VARCHAR)                        AS traces_tags,
        CAST(origins_tags AS VARCHAR)                       AS origins_tags,
        CAST(stores_tags AS VARCHAR)                        AS stores_tags,
        CAST(packaging_tags AS VARCHAR)                     AS packaging_tags,
        CAST(minerals_tags AS VARCHAR)                      AS minerals_tags,
        CAST(vitamins_tags AS VARCHAR)                      AS vitamins_tags,
        CAST(nutriments AS VARCHAR)                         AS nut_raw,
        CAST(countries_tags AS VARCHAR)                     AS countries_tags,
        '{country}'                                         AS primary_country,
        COALESCE(TRY_CAST(popularity_key AS BIGINT), 0)    AS popularity_key,
        COALESCE(TRY_CAST(unique_scans_n AS INTEGER), 0)   AS unique_scans_n,
        COALESCE(TRY_CAST(scans_n AS INTEGER), 0)          AS scans_n,
        TRY_CAST(completeness AS FLOAT)                     AS completeness,
        CAST(images AS VARCHAR)                             AS img_raw,
        TRY_CAST(link AS VARCHAR)                           AS link
    """

counts = {}
start = time.time()

print("Loading Canada...")
con.execute(f"""
    CREATE TABLE products_raw AS
    SELECT {raw_select('canada')}
    FROM read_parquet('{PARQUET}')
    WHERE CAST(countries_tags AS VARCHAR) ILIKE '%canada%'
      AND {BASE_WHERE}
""")
counts['canada'] = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0]
print(f"  ✅ Canada: {counts['canada']:,}  ({time.time()-start:.0f}s)")

print("Loading United States (top 275k)...")
con.execute(f"""
    INSERT INTO products_raw
    SELECT {raw_select('united-states')}
    FROM read_parquet('{PARQUET}')
    WHERE CAST(countries_tags AS VARCHAR) ILIKE '%united-states%'
      AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%canada%'
      AND {BASE_WHERE}
    ORDER BY COALESCE(popularity_key, 0) DESC
    LIMIT 275000
""")
counts['us'] = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0] - counts['canada']
print(f"  ✅ US: {counts['us']:,}  ({time.time()-start:.0f}s)")

print("Loading India...")
con.execute(f"""
    INSERT INTO products_raw
    SELECT {raw_select('india')}
    FROM read_parquet('{PARQUET}')
    WHERE CAST(countries_tags AS VARCHAR) ILIKE '%india%'
      AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%canada%'
      AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%united-states%'
      AND {BASE_WHERE}
""")
counts['india'] = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0] - counts['canada'] - counts['us']
print(f"  ✅ India: {counts['india']:,}  ({time.time()-start:.0f}s)")

print("Loading United Kingdom...")
con.execute(f"""
    INSERT INTO products_raw
    SELECT {raw_select('united-kingdom')}
    FROM read_parquet('{PARQUET}')
    WHERE CAST(countries_tags AS VARCHAR) ILIKE '%united-kingdom%'
      AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%canada%'
      AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%united-states%'
      AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%india%'
      AND {BASE_WHERE}
""")
counts['uk'] = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0] - counts['canada'] - counts['us'] - counts['india']
print(f"  ✅ UK: {counts['uk']:,}  ({time.time()-start:.0f}s)")

print(f"\n✅ Raw load done: {con.execute('SELECT COUNT(*) FROM products_raw').fetchone()[0]:,} rows in {time.time()-start:.0f}s")


print("Reading into pandas...")
df = con.execute("SELECT * FROM products_raw").fetchdf()
print(f"  {len(df):,} rows x {len(df.columns)} cols")

print("Processing all struct columns in single pass...")
t = time.time()

processed = [
    process_row(row.pn_raw, row.ing_raw, row.nut_raw, row.img_raw, row.code)
    for row in df[['code','pn_raw','ing_raw','nut_raw','img_raw']].itertuples(index=False)
]

processed_df = pd.DataFrame(processed)
df = df.drop(columns=['pn_raw','ing_raw','nut_raw','img_raw'])
df = pd.concat([df, processed_df], axis=1)

print(f"  ✅ Done in {time.time()-t:.0f}s")
print(f"  Sample name:  {df['product_name'].dropna().iloc[0]}")
print(f"  Sample image: {df['image_url'].dropna().iloc[0]}")
print(f"  Final shape:  {len(df):,} rows x {len(df.columns)} cols")


print("\nWriting to DuckDB...")
con.execute("DROP TABLE IF EXISTS products")
con.register('df_view', df)
con.execute("CREATE TABLE products AS SELECT * FROM df_view")
con.execute("DROP TABLE IF EXISTS products_raw")

print("Creating indexes...")
for idx, col in [
    ('idx_code',       'code'),
    ('idx_country',    'primary_country'),
    ('idx_nutriscore', 'nutriscore_grade'),
    ('idx_nova',       'nova_group'),
    ('idx_ecoscore',   'ecoscore_grade'),
    ('idx_popularity', 'popularity_key DESC'),
    ('idx_scans',      'unique_scans_n DESC'),
]:
    con.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON products({col})")
print(" Indexes done")

total   = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
elapsed = time.time() - start

print("\n" + "="*50)
print("FINAL SUMMARY")
print("="*50)
print(f"  Canada:         {counts['canada']:>8,}")
print(f"  United States:  {counts['us']:>8,}")
print(f"  India:          {counts['india']:>8,}")
print(f"  United Kingdom: {counts['uk']:>8,}")
print(f"  TOTAL:          {total:>8,}")
print(f"  Time:           {elapsed:.0f}s")

print("\n--- TOP 5 PRODUCTS ---")
print(con.execute("""
    SELECT code, product_name, brands, primary_country,
           nutriscore_grade,
           CASE WHEN image_url IS NOT NULL THEN '✅' ELSE '❌' END AS img
    FROM products ORDER BY popularity_key DESC LIMIT 5
""").fetchdf().to_string(index=False))

bil = con.execute("""
    SELECT COUNT(*) AS total,
           COUNT(product_name_en) AS name_en,
           COUNT(product_name_fr) AS name_fr,
           COUNT(ingredients_en)  AS ing_en,
           COUNT(ingredients_fr)  AS ing_fr
    FROM products WHERE primary_country = 'canada'
""").fetchdf()
ca = bil['total'].iloc[0]
print(f"\n--- CANADA BILINGUAL ---")
for col in ['name_en','name_fr','ing_en','ing_fr']:
    v = bil[col].iloc[0]
    print(f"  {col:<12} {v:,} / {ca:,}  ({v/ca*100:.1f}%)")

null_imgs = con.execute("SELECT COUNT(*) FROM products WHERE image_url IS NULL").fetchone()[0]
print(f"\n  NULL image_url: {null_imgs:,} / {total:,}  ({null_imgs/total*100:.1f}%)")

con.close()
print("\n✅ off_v2.duckdb is ready!")


from google.colab import files
files.download("/content/off_v2.duckdb")