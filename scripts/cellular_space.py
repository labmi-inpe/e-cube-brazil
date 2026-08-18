import json
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
from shapely.geometry import box
from shapely.strtree import STRtree


def fmt2(n: int) -> str:
    return f"{int(n):02d}"


@dataclass
class CellRef:
    cs: "CellularSpacePy"
    idx: int

    @property
    def row(self) -> int:
        return int(self.cs.rows_arr[self.idx])

    @property
    def col(self) -> int:
        return int(self.cs.cols_arr[self.idx])

    @property
    def geom(self):
        return self.cs.gdf.geometry.iloc[self.idx]

    def getId(self) -> Union[int, str]:
        return self.cs.ids_arr[self.idx]


class CellularSpacePy:
    def __init__(
        self,
        gdf: gpd.GeoDataFrame,
        xy: Tuple[str, str] = ("col", "row"),
        id_field: str = "id",
        zero: str = "bottom",
    ):
        self.gdf = gdf
        self.xy = xy
        self.id_field = id_field
        self.zero = zero

        # Extração vetorizada via NumPy para alta performance
        self.cols_arr = self.gdf[self.xy[0]].to_numpy(dtype=int)
        self.rows_arr = self.gdf[self.xy[1]].to_numpy(dtype=int)
        self.ids_arr = self.gdf[self.id_field].to_numpy()

        self._index_xy: Dict[Tuple[int, int], int] = {
            (c, r): i for i, (c, r) in enumerate(zip(self.cols_arr, self.rows_arr))
        }
        self._strtree = STRtree(list(self.gdf.geometry))

    def __len__(self) -> int:
        return len(self.gdf)

    def get(self, col: int, row: int) -> Optional[CellRef]:
        idx = self._index_xy.get((int(col), int(row)))
        if idx is None:
            return None
        return CellRef(self, idx)

    def createNeighborhood(
        self,
        strategy: str = "moore",
        wrap: bool = False,
        self_neighbor: bool = False,
    ) -> Dict[Union[int, str], List[Union[int, str]]]:
        """Gera a estrutura de vizinhança exclusivamente ESPACIAL (x, y)."""
        if strategy not in ("moore", "vonneumann"):
            raise ValueError("strategy suportada: 'moore' ou 'vonneumann'.")

        cmin, cmax = int(self.cols_arr.min()), int(self.cols_arr.max())
        rmin, rmax = int(self.rows_arr.min()), int(self.rows_arr.max())

        offsets = (
            [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
            if strategy == "moore"
            else [(0, -1), (-1, 0), (1, 0), (0, 1)]
        )

        neigh: Dict[Union[int, str], List[Union[int, str]]] = {}

        for i in range(len(self.gdf)):
            cell_id = self.ids_arr[i]
            c = self.cols_arr[i]
            r = self.rows_arr[i]

            nlist: List[Union[int, str]] = []
            if self_neighbor:
                nlist.append(cell_id)

            for dc, dr in offsets:
                cc, rr = c + dc, r + dr
                if wrap:
                    if cc < cmin: cc = cmax
                    elif cc > cmax: cc = cmin
                    if rr < rmin: rr = rmax
                    elif rr > rmax: rr = rmin

                ref = self.get(cc, rr)
                if ref is not None:
                    nlist.append(ref.getId())

            neigh[cell_id] = nlist

        return neigh

    def createSpatioTemporalNeighborhood(
        self,
        time_steps: List[Union[int, str]],
        strategy: str = "moore",
        wrap: bool = False,
        self_neighbor: bool = False,
        temporal_window: Tuple[int, int] = (-1, 1),
    ) -> Dict[Tuple[Union[int, str], Union[int, str]], List[Tuple[Union[int, str], Union[int, str]]]]:
        """Gera a estrutura de vizinhança ESPAÇO-TEMPORAL (x, y, t)."""
        if strategy not in ("moore", "vonneumann"):
            raise ValueError("strategy suportada: 'moore' ou 'vonneumann'.")

        cmin, cmax = int(self.cols_arr.min()), int(self.cols_arr.max())
        rmin, rmax = int(self.rows_arr.min()), int(self.rows_arr.max())

        offsets = (
            [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
            if strategy == "moore"
            else [(0, -1), (-1, 0), (1, 0), (0, 1)]
        )

        st_neigh: Dict[Tuple[Union[int, str], Union[int, str]], List[Tuple[Union[int, str], Union[int, str]]]] = {}
        t_min, t_max = temporal_window

        for t_idx, t_curr in enumerate(time_steps):
            for i in range(len(self.gdf)):
                cell_id = self.ids_arr[i]
                c = self.cols_arr[i]
                r = self.rows_arr[i]

                st_nlist: List[Tuple[Union[int, str], Union[int, str]]] = []

                for dt in range(t_min, t_max + 1):
                    target_t_idx = t_idx + dt

                    if 0 <= target_t_idx < len(time_steps):
                        t_target = time_steps[target_t_idx]

                        if dt == 0 and self_neighbor:
                            st_nlist.append((cell_id, t_target))

                        for dc, dr in offsets:
                            cc, rr = c + dc, r + dr
                            if wrap:
                                if cc < cmin: cc = cmax
                                elif cc > cmax: cc = cmin
                                if rr < rmin: rr = rmax
                                elif rr > rmax: rr = rmin

                            ref = self.get(cc, rr)
                            if ref is not None:
                                st_nlist.append((ref.getId(), t_target))

                st_neigh[(cell_id, t_curr)] = st_nlist

        return st_neigh

    def export_3d_topology_json(
        self,
        output_json: str,
        time_steps: List[Union[int, str]],
        strategy: str = "moore",
        temporal_window: Tuple[int, int] = (-1, 1),
        wrap: bool = False,
        self_neighbor: bool = False,
    ) -> None:
        """Gera a topologia espaço-temporal 3D e exporta em formato JSON serializável."""
        st_raw = self.createSpatioTemporalNeighborhood(
            time_steps=time_steps,
            strategy=strategy,
            wrap=wrap,
            self_neighbor=self_neighbor,
            temporal_window=temporal_window,
        )

        topology_export = {}
        for (cell_id, t_curr), neighbors in st_raw.items():
            key_str = f"{cell_id}_{t_curr}"
            topology_export[key_str] = {
                "cell_id": str(cell_id),
                "time_step": t_curr,
                "neighbors": [
                    {"neighbor_id": str(nid), "time_step": nt}
                    for nid, nt in neighbors
                ],
            }

        # Garante a criação do diretório (ex: 'dados/') se ele não existir
        output_dir = os.path.dirname(output_json)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(topology_export, f, indent=4, ensure_ascii=False)

    def save(self, out_path: str) -> None:
        driver = "GPKG" if out_path.endswith(".gpkg") else None
        self.gdf.to_file(out_path, driver=driver)


def generate_cellularspace_terrame_like(
    limit_shp: str,
    out_shp: Optional[str] = None,
    resolution: float = 50000,
    xy: Tuple[str, str] = ("col", "row"),
    zero: str = "bottom",
    clip: str = "mask",
    id_field: str = "id",
) -> CellularSpacePy:
    gdf_lim = gpd.read_file(limit_shp)
    if gdf_lim.empty or gdf_lim.crs is None or gdf_lim.crs.is_geographic:
        raise ValueError("Shapefile inválido, sem CRS ou com coordenadas geográficas (graus). Use projeção métrica.")

    limit_geom = gdf_lim.geometry.union_all()
    minx, miny, maxx, maxy = limit_geom.bounds

    n_cols = math.ceil((maxx - minx) / resolution)
    n_rows = math.ceil((maxy - miny) / resolution)

    geoms, ids, cols, rows = [], [], [], []

    for r in range(n_rows):
        y1 = miny + r * resolution
        y2 = y1 + resolution

        for c in range(n_cols):
            x1 = minx + c * resolution
            x2 = x1 + resolution
            cell = box(x1, y1, x2, y2)

            if not cell.intersects(limit_geom):
                continue

            cell_geom = cell.intersection(limit_geom) if clip == "intersection" else cell
            if cell_geom.is_empty:
                continue

            row_val = r if zero == "bottom" else (n_rows - 1) - r

            geoms.append(cell_geom)
            cols.append(c)
            rows.append(row_val)
            ids.append(f"C{fmt2(c)}L{fmt2(row_val)}")

    out = gpd.GeoDataFrame(
        {id_field: ids, xy[0]: cols, xy[1]: rows},
        geometry=geoms,
        crs=gdf_lim.crs,
    )

    cs = CellularSpacePy(out, xy=xy, id_field=id_field, zero=zero)
    if out_shp:
        cs.save(out_shp)

    return cs


# ==============================================================================
# EXECUÇÃO DO FLUXO
# ==============================================================================
if __name__ == "__main__":
    # 1. Gera o espaço celular baseado no seu vetor limite
    cs = generate_cellularspace_terrame_like(
        limit_shp="seu_limite.shp",
        resolution=50000
    )

    # 2. Exporta a topologia 3D para o caminho desejado
    cs.export_3d_topology_json(
        output_json="dados/topologia_3d.json",
        time_steps=[2015, 2020]
    )