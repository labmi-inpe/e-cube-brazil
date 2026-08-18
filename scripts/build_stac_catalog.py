"""
build_stac_catalog.py
Script para criação e exportação do Catálogo STAC com suporte a Datacube Extension
para dados ambientais NetCDF do E-Cube (IBGE).
"""

from datetime import datetime, timezone
import pystac
from pystac.extensions.datacube import (
    DatacubeExtension,
    HorizontalSpatialDimension,
    HorizontalSpatialDimensionAxis,
    TemporalDimension,
    Variable,
    VariableType,
)

def build_catalog():
    # -------------------------------------------------------------------------
    # 1. Instanciação do Catálogo STAC Raiz
    # -------------------------------------------------------------------------
    catalog = pystac.Catalog(
        id="ecube-ibge-observed",
        title="E-Cube IBGE - Catálogo de Dados Observados",
        description="Catálogo STAC contendo o cubo de dados ambientais observados (2015-2020) do E-Cube/IBGE em NetCDF."
    )

    # -------------------------------------------------------------------------
    # 2. Definição da Geometria GeoJSON e Bounding Box (Abrangência Brasil)
    # BBox: [min_lon, min_lat, max_lon, max_lat]
    # -------------------------------------------------------------------------
    bbox = [-73.9, -33.7, -34.7, 5.2]
    
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [-73.9, -33.7],
                [-34.7, -33.7],
                [-34.7, 5.2],
                [-73.9, 5.2],
                [-73.9, -33.7]
            ]
        ]
    }

    # Intervalo Temporal em formato UTC ISO 8601
    start_dt = datetime(2015, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2020, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    # -------------------------------------------------------------------------
    # 3. Criação do Item STAC
    # -------------------------------------------------------------------------
    item_obs = pystac.Item(
        id="ecube-observed-2015-2020",
        geometry=geometry,
        bbox=bbox,
        datetime=start_dt,
        properties={
            "start_datetime": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_datetime": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "title": "E-Cube Observado 2015-2020",
            "license": "CC-BY-4.0",
            "providers": [
                {
                    "name": "IBGE",
                    "roles": ["producer", "licensor"]
                }
            ]
        }
    )

    # -------------------------------------------------------------------------
    # 4. Inclusão do Asset NetCDF no Item
    # -------------------------------------------------------------------------
    asset_netcdf = pystac.Asset(
        href="./ecube_observed_2015_2020.nc",
        title="Arquivo NetCDF do Cubo de Dados Observados",
        media_type=pystac.MediaType.NETCDF,
        roles=["data", "datacube"]
    )
    item_obs.add_asset(key="netcdf_data", asset=asset_netcdf)

    # -------------------------------------------------------------------------
    # 5. Aplicação e Configuração da Datacube Extension
    # -------------------------------------------------------------------------
    dc_ext = DatacubeExtension.ext(item_obs, add_if_missing=True)
    
    # Mapeamento das dimensões (x, y, time)
    dc_ext.dimensions = {
        "x": HorizontalSpatialDimension(
            properties={
                "axis": HorizontalSpatialDimensionAxis.X,
                "extent": [-73.9, -34.7],
                "description": "Longitude (EPSG:4326)"
            }
        ),
        "y": HorizontalSpatialDimension(
            properties={
                "axis": HorizontalSpatialDimensionAxis.Y,
                "extent": [-33.7, 5.2],
                "description": "Latitude (EPSG:4326)"
            }
        ),
        "time": TemporalDimension(
            properties={
                "extent": [
                    start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                ],
                "step": "P1D",  # Frequência diária
                "description": "Dimensão temporal de observações diárias"
            }
        )
    }

    # Configuração das Variáveis Contidas no NetCDF
    dc_ext.variables = {
        "pre": Variable(
            properties={
                "type": VariableType.DATA,
                "dimensions": ["time", "y", "x"],
                "unit": "mm/day",
                "description": "Precipitação total acumulada diária"
            }
        ),
        "tmp_min": Variable(
            properties={
                "type": VariableType.DATA,
                "dimensions": ["time", "y", "x"],
                "unit": "degC",
                "description": "Temperatura mínima diária"
            }
        ),
        "tmp_max": Variable(
            properties={
                "type": VariableType.DATA,
                "dimensions": ["time", "y", "x"],
                "unit": "degC",
                "description": "Temperatura máxima diária"
            }
        )
    }

    # -------------------------------------------------------------------------
    # 6. Vínculo do Item ao Catálogo e Exportação
    # Nota: Utiliza-se catalog.add_item() em vez de add_child() para objetos Item
    # -------------------------------------------------------------------------
    catalog.add_item(item_obs)

    # Gravação do catálogo autocontido
    output_dir = "./stac_catalog"
    catalog.normalize_and_save(
        root_href=output_dir,
        catalog_type=pystac.CatalogType.SELF_CONTAINED
    )
    
    print(f"✅ Catálogo STAC exportado com sucesso em '{output_dir}'")

if __name__ == "__main__":
    build_catalog()