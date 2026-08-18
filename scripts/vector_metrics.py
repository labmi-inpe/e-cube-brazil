import geopandas as gpd
import pandas as pd


def apply_vector_metrics(
    gdf_grid: gpd.GeoDataFrame,
    layer_path: str,
    method: str,
    out_column: str = None,
    attr_num: str = None,
    attr_cat: str = None,
) -> gpd.GeoDataFrame:
    """Aplica métricas espaciais baseadas em camadas vetoriais com suporte a geometrias complexas."""
    grid = gdf_grid.copy()
    
    # -------------------------------------------------------------------------
    # TRATAMENTO DE ENCODING (Resolve o erro do UnicodeDecodeError)
    # -------------------------------------------------------------------------
    try:
        layer = gpd.read_file(layer_path, encoding="utf-8")
    except (UnicodeDecodeError, Exception):
        layer = gpd.read_file(layer_path, encoding="latin-1")

    if layer.crs is None:
        raise ValueError(f"A camada vetorial '{layer_path}' não possui sistema de referência espacial (CRS) definido.")

    # Alinhamento de CRS e correção de geometrias
    layer = layer.to_crs(grid.crs)
    layer["geometry"] = layer.geometry.make_valid()

    grid["_temp_id"] = range(len(grid))
    grid["area_cell"] = grid.geometry.area

    # 1. DISTÂNCIA
    if method == "distance":
        grid_points = grid.copy()
        grid_points["geometry"] = grid_points.geometry.centroid
        
        joined = gpd.sjoin_nearest(
            grid_points[["_temp_id", "geometry"]],
            layer,
            how="left",
            distance_col=out_column or "distance",
        ).drop_duplicates(subset=["_temp_id"])
        
        grid[out_column or "distance"] = joined.sort_values("_temp_id")[out_column or "distance"].values

    # 2. CONTAGEM E PRESENÇA
    elif method in ("count", "presence"):
        join_count = gpd.sjoin(
            grid[["_temp_id", "geometry"]],
            layer,
            how="inner",
            predicate="intersects",
        )
        counts = join_count.groupby("_temp_id").size()
        grid["count_val"] = grid["_temp_id"].map(counts).fillna(0).astype(int)

        if method == "presence":
            grid[out_column or "presence"] = (grid["count_val"] > 0).astype(int)
            grid = grid.drop(columns=["count_val"])
        else:
            grid[out_column or "count"] = grid["count_val"]
            grid = grid.drop(columns=["count_val"])

    # 3. INTERSEÇÃO, ÁREA E ESTATÍSTICAS (OVERLAY)
    elif method in ("area", "coverage", "stats", "mode"):
        overlay_gdf = gpd.overlay(
            grid[["_temp_id", "area_cell", "geometry"]],
            layer,
            how="intersection",
        )
        overlay_gdf["inter_area"] = overlay_gdf.geometry.area
        overlay_gdf["prop_area"] = overlay_gdf["inter_area"] / overlay_gdf["area_cell"]

        if method == "area":
            area_pct = overlay_gdf.groupby("_temp_id")["prop_area"].sum()
            grid[out_column or "area_pct"] = grid["_temp_id"].map(area_pct).fillna(0.0)

        elif method == "coverage" and attr_cat:
            coverage = (
                overlay_gdf.groupby(["_temp_id", attr_cat])["prop_area"]
                .sum()
                .unstack(fill_value=0)
            )
            coverage.columns = [f"c_{str(c)[:7]}" for c in coverage.columns]
            grid = grid.merge(coverage, on="_temp_id", how="left").fillna(0.0)

        elif method == "stats" and attr_num:
            # Média Ponderada com proteção contra divisão por zero
            overlay_gdf["weighted_val"] = overlay_gdf[attr_num] * overlay_gdf["inter_area"]
            grouped = overlay_gdf.groupby("_temp_id")
            sum_area = grouped["inter_area"].sum().replace(0, float("nan"))
            avg_weighted = grouped["weighted_val"].sum() / sum_area
            grid[out_column or f"avg_{attr_num}"] = grid["_temp_id"].map(avg_weighted).fillna(0.0)

        elif method == "mode" and attr_cat:
            idx_max = overlay_gdf.groupby("_temp_id")["inter_area"].idxmax()
            mode_series = overlay_gdf.loc[idx_max].set_index("_temp_id")[attr_cat]
            grid[out_column or "mode_val"] = (
                grid["_temp_id"].map(mode_series).fillna("Nenhum").astype(str).str[:10]
            )

    grid = grid.drop(columns=["_temp_id", "area_cell"], errors="ignore")
    return grid