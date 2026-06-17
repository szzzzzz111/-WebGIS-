"""Week 16 backend data readiness check.

This script checks local data and database readiness for the midterm demo.
It intentionally avoids importing Flask/Rasterio so it can run in a minimal
Python environment.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "landuse.db"
DATA_PATHS = {
    "processed_csv": ROOT / "data" / "processed_landuse.csv",
    "raster_1980": ROOT / "data" / "raster" / "1980.tif",
    "raster_2000": ROOT / "data" / "raster" / "2000.tif",
    "raster_2020": ROOT / "data" / "raster" / "2020.tif",
    "vector_shp": ROOT / "data" / "vector" / "county_boundaries.shp",
}
EXPECTED_COLUMNS = {"id", "county_id", "county_name", "year", "land_type", "area"}


def check_files() -> dict[str, object]:
    files = {}
    missing = []

    for name, path in DATA_PATHS.items():
        exists = path.exists()
        files[name] = {
            "path": str(path.relative_to(ROOT)),
            "exists": exists,
            "size": path.stat().st_size if exists else 0,
        }
        if not exists:
            missing.append(name)

    return {"files": files, "missing": missing}


def check_database() -> dict[str, object]:
    if not DB_PATH.exists():
        return {"exists": False, "error": "landuse.db not found"}

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        if "landuse_data" not in tables:
            return {"exists": True, "tables": tables, "error": "landuse_data table not found"}

        cursor.execute("PRAGMA table_info(landuse_data)")
        columns = [row[1] for row in cursor.fetchall()]
        missing_columns = sorted(EXPECTED_COLUMNS.difference(columns))

        cursor.execute("SELECT COUNT(*) FROM landuse_data")
        row_count = cursor.fetchone()[0]

        cursor.execute("SELECT DISTINCT year FROM landuse_data ORDER BY year")
        years = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(DISTINCT county_id) FROM landuse_data")
        county_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT county_id, county_name, year, land_type, ROUND(area, 4)
            FROM landuse_data
            ORDER BY county_id, year, land_type
            LIMIT 5
            """
        )
        sample_rows = cursor.fetchall()

    return {
        "exists": True,
        "tables": tables,
        "columns": columns,
        "missing_columns": missing_columns,
        "row_count": row_count,
        "years": years,
        "county_count": county_count,
        "sample_rows": sample_rows,
    }


def main() -> int:
    file_result = check_files()
    db_result = check_database()
    ok = not file_result["missing"] and db_result.get("exists") and not db_result.get("error")

    report = {
        "ok": bool(ok),
        "week": 16,
        "files": file_result,
        "database": db_result,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
