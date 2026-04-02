"""
Inspect parquet - country distribution WITH image availability
Usage: python inspect_parquet.py
"""

import duckdb

con = duckdb.connect()

PARQUET = 'data/0000.parquet'

print("=" * 70)
print("COUNTRY + IMAGE AVAILABILITY REPORT")
print("=" * 70)

targets = [
    ('canada',          'en:canada'),
    ('france',          'en:france'),
    ('india',           'en:india'),
    ('united-states',   'en:united-states'),
    ('united-kingdom',  'en:united-kingdom'),
    ('germany',         'en:germany'),
]

print(f"\n{'Country':<20} {'Total':>10} {'Has Image':>12} {'No Image':>10} {'Image %':>9}")
print("-" * 65)

for label, tag in targets:
    total = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%{label}%'
    """).fetchone()[0]

    with_img = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%{label}%'
          AND images IS NOT NULL
          AND len(images) > 0
    """).fetchone()[0]

    no_img = total - with_img
    pct = (with_img / total * 100) if total > 0 else 0
    print(f"{label:<20} {total:>10,} {with_img:>12,} {no_img:>10,} {pct:>8.1f}%")

print("\n--- FRONT IMAGE AVAILABILITY (products with key containing 'front') ---")
print(f"\n{'Country':<20} {'Has Image':>12} {'Has Front':>12} {'Front %':>9}")
print("-" * 57)

for label, tag in targets:
    with_img = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%{label}%'
          AND images IS NOT NULL AND len(images) > 0
    """).fetchone()[0]

    with_front = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%{label}%'
          AND CAST(images AS VARCHAR) ILIKE '%front%'
    """).fetchone()[0]

    pct = (with_front / with_img * 100) if with_img > 0 else 0
    print(f"{label:<20} {with_img:>12,} {with_front:>12,} {pct:>8.1f}%")

print("\n--- FULLY USABLE PRODUCTS (name + front image + not obsolete) ---")
print(f"\n{'Country':<20} {'Usable':>10} {'of Total':>10}")
print("-" * 44)

total_usable = 0
for label, tag in targets:
    usable = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%{label}%'
          AND product_name IS NOT NULL
          AND len(product_name) > 0
          AND CAST(images AS VARCHAR) ILIKE '%front%'
          AND (obsolete IS NULL OR obsolete = false)
    """).fetchone()[0]

    total_p = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{PARQUET}')
        WHERE CAST(countries_tags AS VARCHAR) ILIKE '%{label}%'
    """).fetchone()[0]

    total_usable += usable
    print(f"{label:<20} {usable:>10,} {total_p:>10,}")

print(f"\n{'TOTAL USABLE':<20} {total_usable:>10,}")
print(f"\n→ Our 500k limit looks {'✅ fine' if total_usable >= 500000 else f'⚠️  short — only {total_usable:,} usable products'}")

con.close()
print("\n✅ Done!")