"""
setup_db2.py — Fast version using JSON extraction instead of list_filter

Strategy:
  1. Load raw structs as JSON strings (very fast)
  2. Extract fields with json_extract_string (fast scalar ops)

Usage: python setup_db2.py
"""

import duckdb
import time

PARQUET  = "data/0000.parquet"
DB_PATH  = "data/off_v2.duckdb"
IMG_BASE = "https://images.openfoodfacts.org/images/products"

def setup():
    start = time.time()
    print("=" * 60)
    print("BUILDING off_v2.duckdb (fast mode)")
    print("=" * 60)

    con = duckdb.connect(DB_PATH)

    # Use all available threads and memory
    con.execute("PRAGMA threads=8")
    con.execute("PRAGMA memory_limit='4GB'")

    con.execute("DROP TABLE IF EXISTS products")
    con.execute("DROP TABLE IF EXISTS products_raw")

    counts = {}

    # ----------------------------------------------------------------
    # Helper: build the fast SELECT using json_extract on cast structs
    # ----------------------------------------------------------------
    def build_select(primary_country: str, limit: str = "") -> str:
        code_path = """CASE WHEN LENGTH(code) > 8
            THEN SUBSTRING(code,1,3)||'/'||SUBSTRING(code,4,3)||'/'||SUBSTRING(code,7,3)||'/'||SUBSTRING(code,10)
            ELSE code END"""

        return f"""
            code,
            -- product name: cast array to json, regex out en/fr/main text
            json_extract_string(
                json_extract(CAST(product_name AS JSON), '$[*]'),
                '$[0].text'
            ) AS product_name,
            TRY_CAST(brands AS VARCHAR)                         AS brands,
            lang,
            CAST(languages_tags AS VARCHAR)                     AS languages_tags,
            TRY_CAST(quantity AS VARCHAR)                       AS product_quantity,
            TRY_CAST(serving_size AS VARCHAR)                   AS serving_size,
            TRY_CAST(nutrition_data_per AS VARCHAR)             AS nutrition_data_per,

            -- Health scores
            TRY_CAST(nutriscore_grade AS VARCHAR)               AS nutriscore_grade,
            TRY_CAST(nutriscore_score AS INTEGER)               AS nutriscore_score,
            TRY_CAST(nova_group AS INTEGER)                     AS nova_group,
            TRY_CAST(nova_groups AS VARCHAR)                    AS nova_groups,
            TRY_CAST(ecoscore_grade AS VARCHAR)                 AS ecoscore_grade,
            TRY_CAST(ecoscore_score AS INTEGER)                 AS ecoscore_score,

            -- Ingredients as raw text (we'll parse bilingually in step 2)
            CAST(ingredients_text AS VARCHAR)                   AS ingredients_raw,
            CAST(ingredients_analysis_tags AS VARCHAR)          AS ingredients_analysis_tags,
            TRY_CAST(ingredients_n AS INTEGER)                  AS ingredients_n,
            TRY_CAST(additives_n AS INTEGER)                    AS additives_n,
            CAST(additives_tags AS VARCHAR)                     AS additives_tags,
            TRY_CAST(with_sweeteners AS INTEGER)                AS with_sweeteners,
            TRY_CAST(with_non_nutritive_sweeteners AS INTEGER)  AS with_non_nutritive_sweeteners,
            TRY_CAST(ingredients_from_palm_oil_n AS INTEGER)    AS ingredients_from_palm_oil_n,
            TRY_CAST(no_nutrition_data AS BOOLEAN)              AS no_nutrition_data,

            -- Categories
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

            -- Nutriments: store as raw JSON, extract flat in step 2
            CAST(nutriments AS VARCHAR)                         AS nutriments_raw,

            -- Country & popularity
            CAST(countries_tags AS VARCHAR)                     AS countries_tags,
            '{primary_country}'                                 AS primary_country,
            COALESCE(TRY_CAST(popularity_key AS BIGINT), 0)    AS popularity_key,
            COALESCE(TRY_CAST(unique_scans_n AS INTEGER), 0)   AS unique_scans_n,
            COALESCE(TRY_CAST(scans_n AS INTEGER), 0)          AS scans_n,
            TRY_CAST(completeness AS FLOAT)                     AS completeness,

            -- Store raw images JSON, extract URL in step 2
            CAST(images AS VARCHAR)                             AS images_raw,
            TRY_CAST(link AS VARCHAR)                           AS link
        """

    BASE_WHERE = """
        product_name IS NOT NULL
        AND len(product_name) > 0
        AND CAST(images AS VARCHAR) ILIKE '%front%'
        AND (obsolete IS NULL OR obsolete = false)
    """

    # ----------------------------------------------------------------
    # STEP 1: Load all 4 countries into raw table (fast - no parsing)
    # ----------------------------------------------------------------
    print("\n[1/5] Loading Canada...")
    con.execute(f"""
        CREATE TABLE products_raw AS
        SELECT {build_select('canada')}
        FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%canada%'
          AND {BASE_WHERE}
    """)
    counts['canada'] = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0]
    print(f"   ✅ Canada: {counts['canada']:,}  ({time.time()-start:.0f}s)")

    print("\n[2/5] Loading United States (top 275k)...")
    con.execute(f"""
        INSERT INTO products_raw
        SELECT {build_select('united-states')}
        FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%united-states%'
          AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%canada%'
          AND {BASE_WHERE}
        ORDER BY COALESCE(popularity_key, 0) DESC
        LIMIT 275000
    """)
    counts['us'] = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0] - counts['canada']
    print(f"   ✅ United States: {counts['us']:,}  ({time.time()-start:.0f}s)")

    print("\n[3/5] Loading India...")
    con.execute(f"""
        INSERT INTO products_raw
        SELECT {build_select('india')}
        FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%india%'
          AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%canada%'
          AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%united-states%'
          AND {BASE_WHERE}
    """)
    counts['india'] = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0] - counts['canada'] - counts['us']
    print(f"   ✅ India: {counts['india']:,}  ({time.time()-start:.0f}s)")

    print("\n[4/5] Loading United Kingdom...")
    con.execute(f"""
        INSERT INTO products_raw
        SELECT {build_select('united-kingdom')}
        FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%united-kingdom%'
          AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%canada%'
          AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%united-states%'
          AND CAST(countries_tags AS VARCHAR) NOT ILIKE '%india%'
          AND {BASE_WHERE}
    """)
    counts['uk'] = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0] - counts['canada'] - counts['us'] - counts['india']
    print(f"   ✅ United Kingdom: {counts['uk']:,}  ({time.time()-start:.0f}s)")

    raw_total = con.execute("SELECT COUNT(*) FROM products_raw").fetchone()[0]
    print(f"\n   Raw total loaded: {raw_total:,}")

    # ----------------------------------------------------------------
    # STEP 2: Flatten into final products table (fast Python-side JSON)
    # ----------------------------------------------------------------
    print(f"\n[5/5] Flattening structs into final table...")

    import json, re

    def extract_lang_from_raw(json_str, lang):
        """Extract text for given lang from stringified struct array."""
        if not json_str:
            return None
        try:
            # DuckDB stringifies structs like: [{'lang': 'en', 'text': '...'}, ...]
            # Replace single quotes with double for JSON parse
            cleaned = json_str.replace("'", '"').replace('None', 'null').replace('True','true').replace('False','false')
            items = json.loads(cleaned)
            if not isinstance(items, list):
                return None
            # Try exact lang match
            for item in items:
                if isinstance(item, dict) and item.get('lang') == lang:
                    return item.get('text')
            return None
        except Exception:
            return None

    def extract_main_text(json_str):
        """Extract best text: en → main → first."""
        if not json_str:
            return None
        try:
            cleaned = json_str.replace("'", '"').replace('None', 'null').replace('True','true').replace('False','false')
            items = json.loads(cleaned)
            if not isinstance(items, list) or len(items) == 0:
                return None
            for lang in ['en', 'main']:
                for item in items:
                    if isinstance(item, dict) and item.get('lang') == lang:
                        t = item.get('text')
                        if t:
                            return t
            # fallback: first non-empty
            for item in items:
                if isinstance(item, dict):
                    t = item.get('text')
                    if t:
                        return t
            return None
        except Exception:
            return None

    def extract_nutriment(json_str, name):
        """Extract 100g value for a nutriment."""
        if not json_str:
            return None
        try:
            cleaned = json_str.replace("'", '"').replace('None', 'null').replace('True','true').replace('False','false')
            items = json.loads(cleaned)
            if not isinstance(items, list):
                return None
            for item in items:
                if isinstance(item, dict) and item.get('name') == name:
                    val = item.get('100g')
                    return float(val) if val is not None else None
            return None
        except Exception:
            return None

    def build_image_url(code, images_raw):
        """Build front image URL."""
        if not images_raw or 'front' not in images_raw:
            return None
        try:
            cleaned = images_raw.replace("'", '"').replace('None', 'null').replace('True','true').replace('False','false')
            items = json.loads(cleaned)
            if not isinstance(items, list):
                return None
            imgid = None
            # Priority: front_en > front_* > front > *front*
            for prefix in ['front_en', 'front_', 'front', '']:
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    key = item.get('key', '')
                    if prefix == '' or key.startswith(prefix) or (prefix == '' and 'front' in key):
                        imgid = item.get('imgid')
                        break
                if imgid:
                    break
            if not imgid:
                return None
            if len(str(code)) > 8:
                c = str(code)
                path = f"{c[:3]}/{c[3:6]}/{c[6:9]}/{c[9:]}"
            else:
                path = str(code)
            return f"{IMG_BASE}/{path}/{imgid}.400.jpg"
        except Exception:
            return None

    # Load raw data into pandas for fast Python processing
    print("   Reading raw table into memory...")
    df = con.execute("SELECT * FROM products_raw").fetchdf()
    print(f"   Processing {len(df):,} rows...")

    # Extract bilingual + flat columns
    df['product_name_en']   = df['ingredients_raw'].apply(lambda x: None)  # placeholder
    df['product_name_fr']   = df['ingredients_raw'].apply(lambda x: None)

    # Process product_name from raw (it's already extracted as first element string in step1)
    # We need to re-read from parquet for bilingual — but product_name column was cast to string
    # So let's just use what we have and do a simpler approach:
    # product_name is already the best text from step1
    # For bilingual, we'll use a regex approach on the raw string

    print("   Extracting bilingual names...")
    # Re-read just the bilingual columns we need from parquet in batches
    bilingual = con.execute(f"""
        SELECT
            code,
            CAST(product_name AS VARCHAR)    AS pn_raw,
            CAST(ingredients_text AS VARCHAR) AS ing_raw,
            CAST(nutriments AS VARCHAR)       AS nut_raw,
            CAST(images AS VARCHAR)           AS img_raw
        FROM read_parquet('{PARQUET}')
        WHERE code IN (SELECT code FROM products_raw)
    """).fetchdf()

    print(f"   Bilingual data fetched for {len(bilingual):,} rows...")

    bilingual['product_name_en'] = bilingual['pn_raw'].apply(lambda x: extract_lang_from_raw(x, 'en'))
    bilingual['product_name_fr'] = bilingual['pn_raw'].apply(lambda x: extract_lang_from_raw(x, 'fr'))
    bilingual['product_name']    = bilingual['pn_raw'].apply(extract_main_text)
    bilingual['ingredients_en']  = bilingual['ing_raw'].apply(lambda x: extract_lang_from_raw(x, 'en'))
    bilingual['ingredients_fr']  = bilingual['ing_raw'].apply(lambda x: extract_lang_from_raw(x, 'fr'))
    bilingual['ingredients_text']= bilingual['ing_raw'].apply(extract_main_text)

    print("   Extracting nutrition values...")
    nutrients = ['energy-kcal', 'energy', 'fat', 'saturated-fat',
                 'carbohydrates', 'sugars', 'fiber', 'proteins', 'salt', 'sodium']
    for n in nutrients:
        col = n.replace('-', '_') + '_100g'
        bilingual[col] = bilingual['nut_raw'].apply(lambda x, n=n: extract_nutriment(x, n))

    print("   Building image URLs...")
    bilingual['image_url'] = bilingual.apply(
        lambda row: build_image_url(row['code'], row['img_raw']), axis=1
    )

    # Merge back
    keep_cols = ['code', 'product_name_en', 'product_name_fr', 'product_name',
                 'ingredients_en', 'ingredients_fr', 'ingredients_text', 'image_url'] + \
                [n.replace('-', '_') + '_100g' for n in nutrients]

    bilingual = bilingual[keep_cols]

    # Drop overlapping cols from df before merge
    df = df.drop(columns=['ingredients_raw', 'nutriments_raw', 'images_raw', 'product_name'], errors='ignore')
    final = df.merge(bilingual, on='code', how='left')

    print(f"   Final dataframe: {len(final):,} rows x {len(final.columns)} columns")

    # Write final table to DuckDB
    print("   Writing final products table to DuckDB...")
    con.execute("DROP TABLE IF EXISTS products")
    con.execute("CREATE TABLE products AS SELECT * FROM final")

    # ----------------------------------------------------------------
    # INDEXES
    # ----------------------------------------------------------------
    print("   Creating indexes...")
    con.execute("CREATE INDEX IF NOT EXISTS idx_code       ON products(code)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_country    ON products(primary_country)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_nutriscore ON products(nutriscore_grade)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_nova       ON products(nova_group)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ecoscore   ON products(ecoscore_grade)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_popularity ON products(popularity_key DESC)")
    print("   ✅ Indexes created")

    con.execute("DROP TABLE IF EXISTS products_raw")

    # ----------------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------------
    total   = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    elapsed = time.time() - start

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Canada:         {counts['canada']:>10,}")
    print(f"  United States:  {counts['us']:>10,}")
    print(f"  India:          {counts['india']:>10,}")
    print(f"  United Kingdom: {counts['uk']:>10,}")
    print(f"  ──────────────────────────")
    print(f"  TOTAL:          {total:>10,}")
    print(f"  Time:           {elapsed:.1f}s")
    print(f"  DB:             {DB_PATH}")

    cols = con.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'products' ORDER BY ordinal_position
    """).fetchdf()
    print(f"\n  Columns: {len(cols)}")
    for _, r in cols.iterrows():
        print(f"    {r['column_name']:<35} {r['data_type']}")

    # Sample
    print("\n--- SAMPLE (top 5 by popularity) ---")
    sample = con.execute("""
        SELECT code, product_name, brands, primary_country,
               nutriscore_grade, nova_group,
               CASE WHEN image_url IS NOT NULL THEN '✅' ELSE '❌' END AS img
        FROM products ORDER BY popularity_key DESC LIMIT 5
    """).fetchdf()
    print(sample.to_string(index=False))

    # Bilingual fill rate
    print("\n--- CANADA BILINGUAL FILL RATE ---")
    bil = con.execute("""
        SELECT COUNT(*) AS total,
               COUNT(product_name_en) AS name_en,
               COUNT(product_name_fr) AS name_fr,
               COUNT(ingredients_en)  AS ing_en,
               COUNT(ingredients_fr)  AS ing_fr
        FROM products WHERE primary_country = 'canada'
    """).fetchdf()
    ca = bil['total'].iloc[0]
    for col in ['name_en', 'name_fr', 'ing_en', 'ing_fr']:
        v = bil[col].iloc[0]
        print(f"  {col:<12} {v:,} / {ca:,}  ({v/ca*100:.1f}%)")

    null_imgs = con.execute("SELECT COUNT(*) FROM products WHERE image_url IS NULL").fetchone()[0]
    print(f"\n  NULL image_url: {null_imgs:,}")

    con.close()
    print("\n✅ off_v2.duckdb is ready!")

if __name__ == "__main__":
    setup()