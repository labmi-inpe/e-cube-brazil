import geopandas as gpd
import pandas as pd
from rasterstats import zonal_stats


def apply_raster_metrics(
    gdf_grid: gpd.GeoDataFrame,
    raster_path: str,
    method: str = "quantitative",
    stats: list = None,
    all_touched: bool = False,
    out_column_prefix: str = "r_",
    n_processes: int = 4,
) -> gpd.GeoDataFrame:
    """Aplica estatísticas zonais extraídas de um arquivo Raster com suporte a paralelização."""
    grid = gdf_grid.copy()

    # 1. RASTER QUANTITATIVO (Média, Soma, Min, Max, etc.)
    if method == "quantitative":
        stats_to_calc = stats or ["mean", "sum", "min", "max", "std", "median", "count"]
        res = zonal_stats(
            grid,
            raster_path,
            stats=stats_to_calc,
            all_touched=all_touched,
            n_processes=n_processes,
        )
        df_res = pd.DataFrame(res)

        for stat in stats_to_calc:
            col_name = f"{out_column_prefix}{stat}"
            grid[col_name] = df_res[stat].fillna(0.0)

    # 2. RASTER CATEGÓRICO (Moda, Cobertura, Área por classe)
    elif method == "categorical":
        stats_cat = zonal_stats(
            grid,
            raster_path,
            stats=["majority"],
            categorical=True,
            all_touched=all_touched,
            n_processes=n_processes,
        )
        df_cat = pd.DataFrame(stats_cat)

        if "majority" in df_cat.columns:
            grid[f"{out_column_prefix}mode"] = df_cat["majority"].fillna(-9999).astype(int)

        class_cols = [c for c in df_cat.columns if isinstance(c, (int, float))]
        if class_cols:
            df_counts = df_cat[class_cols].fillna(0)
            total_pixels = df_counts.sum(axis=1)
            df_cov = df_counts.div(total_pixels, axis=0).fillna(0.0)

            for cls in class_cols:
                col_name = f"c_{cls}"[:10]
                grid[col_name] = df_cov[cls].values

    return grid