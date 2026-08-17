from pathlib import Path
from typing import Dict, Union
import geopandas as gpd
import numpy as np
import xarray as xr


def build_netcdf_cube_from_annual_gpkgs(
    file_year_map: Dict[int, str],
    layer_map: Union[str, Dict[int, str]],
    out_nc_path: str,
):
    """Converte arquivos GPKG anuais em um unico arquivo NetCDF (time, y, x).

    file_year_map: {2015: "dados/observed/ecube_2015.gpkg", ...} layer_map:
    "cs_2015" ou {2015: "cs_2015", 2020: "cs_2020", ...}
    """
    print(f"Gerando Cubo NetCDF: {out_nc_path}...")

    sorted_years = sorted(file_year_map.keys())
    cols_to_exclude = ["geometry", "id", "_temp_id", "col", "row"]

    # 1. Carrega a malha base do primeiro ano para mapear X, Y e colunas
    first_year = sorted_years[0]
    first_layer = (
        layer_map[first_year] if isinstance(layer_map, dict) else layer_map
    )

    gdf_base = gpd.read_file(file_year_map[first_year], layer=first_layer)

    cols_col = [
        c for c in gdf_base.columns if c.lower() in ["col", "column", "x_id"]
    ]
    cols_row = [
        c for c in gdf_base.columns if c.lower() in ["row", "row_id", "y_id"]
    ]

    if cols_col and cols_row:
        cols = gdf_base[cols_col[0]].to_numpy(dtype=int)
        rows = gdf_base[cols_row[0]].to_numpy(dtype=int)
    else:
        centroids = gdf_base.geometry.centroid
        unique_x = np.sort(centroids.x.round(2).unique())
        unique_y = np.sort(centroids.y.round(2).unique())
        x_map = {val: idx for idx, val in enumerate(unique_x)}
        y_map = {val: idx for idx, val in enumerate(unique_y)}
        cols = centroids.x.round(2).map(x_map).to_numpy(dtype=int)
        rows = centroids.y.round(2).map(y_map).to_numpy(dtype=int)

    max_col, max_row = cols.max() + 1, rows.max() + 1

    # Identifica colunas de dados presentes no primeiro ano
    data_cols = [
        c
        for c in gdf_base.columns
        if c not in cols_to_exclude and np.issubdtype(gdf_base[c].dtype, np.number)
    ]

    # 2. Prepara os cubos 3D inicializados com NaN
    n_years = len(sorted_years)
    var_cubes = {
        var: np.full((n_years, max_row, max_col), np.nan) for var in data_cols
    }

    # 3. Preenche cada fatia temporal lendo o GPKG correspondente
    for t_idx, year in enumerate(sorted_years):
        gpkg_path = file_year_map[year]
        current_layer = (
            layer_map[year] if isinstance(layer_map, dict) else layer_map
        )

        if not Path(gpkg_path).exists():
            print(
                f"   [Aviso] Arquivo do ano {year} não encontrado em: {gpkg_path}."
            )
            continue

        gdf_year = gpd.read_file(gpkg_path, layer=current_layer)

        for var_name in data_cols:
            if var_name in gdf_year.columns:
                grid_array = np.full((max_row, max_col), np.nan)
                grid_array[rows, cols] = gdf_year[var_name].to_numpy()
                var_cubes[var_name][t_idx, :, :] = grid_array

    # 4. Exporta para NetCDF
    ds_vars = {
        var_name: (["time", "y", "x"], array_3d)
        for var_name, array_3d in var_cubes.items()
    }

    ds = xr.Dataset(
        data_vars=ds_vars,
        coords={
            "time": sorted_years,
            "y": np.arange(max_row),
            "x": np.arange(max_col),
        },
    )

    out_path = Path(out_nc_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out_path)
    print(f" -> Sucesso! Cubo NetCDF salvo em: {out_nc_path}\n")