import sys
from pathlib import Path
import geopandas as gpd
import yaml

# Importação das funções dos módulos locais otimizados
from cellular_space import CellularSpacePy, generate_cellularspace_terrame_like
from raster_metrics import apply_raster_metrics
from vector_metrics import apply_vector_metrics


def run_pipeline(config_path: str = "config.yaml"):
    print("==================================================")
    print("           INICIANDO FILLCELL PYTHON              ")
    print("==================================================\n")

    # 0. Carregar Arquivo de Configuração
    print(f"[0/3] Lendo arquivo de configuração: {config_path}")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        print(f"Erro ao ler o arquivo {config_path}: {e}")
        sys.exit(1)

    # 1. Obter ou Criar a Grade Espacial BASE (Apenas uma vez)
    cs_cfg = cfg.get("cellular_space", {})
    mode = cs_cfg.get("mode", "create")
    id_field = cs_cfg.get("id_field", "id")

    cs = None  # Inicialização da variável para escopo global da função

    if mode == "use_existing":
        existing_path = cs_cfg.get("existing_grid_path")
        print(
            f"[1/3] Modo: 'use_existing'. Carregando grade de:\n      -> {existing_path}"
        )
        try:
            base_grid = gpd.read_file(existing_path)
            # Instancia o CellularSpacePy a partir do GDF existente se necessário
            cs = CellularSpacePy(base_grid, id_field=id_field)
        except Exception as e:
            print(f"Erro ao carregar a grade existente: {e}")
            sys.exit(1)

    elif mode == "create":
        print(
            f"[1/3] Modo: 'create'. Gerando nova grade ({cs_cfg.get('resolution')}m)..."
        )
        try:
            cs = generate_cellularspace_terrame_like(
                limit_shp=cs_cfg["limit_shp"],
                out_shp=None,
                resolution=cs_cfg["resolution"],
                xy=tuple(cs_cfg.get("xy", ["col", "row"])),
                zero=cs_cfg.get("zero", "bottom"),
                clip=cs_cfg.get("clip", "mask"),
                id_field=id_field,
            )
            base_grid = cs.gdf.copy()
        except Exception as e:
            print(f"Erro ao gerar a nova grade celular: {e}")
            sys.exit(1)

    else:
        raise ValueError(
            f"Modo '{mode}' inválido na configuração. Use 'create' ou 'use_existing'."
        )

    print(f"      Grade base pronta com {len(base_grid)} células.\n")

    # 2. Executar Saídas Múltiplas (Estático, Dinâmicos e Cenários)
    outputs = cfg.get("outputs", [])
    print(f"[2/3] Processando {len(outputs)} grupo(s) de saída...")

    for out_idx, out_group in enumerate(outputs, 1):
        target_gpkg = out_group.get("target_gpkg")
        layer_name = out_group.get("layer_name", "cellular_space")
        keep_only_updated = out_group.get("keep_only_updated", False)
        operations = out_group.get("fill_operations", [])

        print(f"\n--- Output [{out_idx}/{len(outputs)}]: {layer_name} ---")

        current_grid = base_grid.copy()
        cols_before = list(current_grid.columns)

        for i, op in enumerate(operations, 1):
            op_type = op.get("type")
            source = op.get("source")
            method = op.get("method")

            print(
                f"  -> ({i}/{len(operations)}) [{op_type.upper()}] Método: '{method}' | Fonte: {source}"
            )

            try:
                if op_type == "vector":
                    current_grid = apply_vector_metrics(
                        gdf_grid=current_grid,
                        layer_path=source,
                        method=method,
                        out_column=op.get("out_column"),
                        attr_num=op.get("attr_num"),
                        attr_cat=op.get("attr_cat"),
                    )

                elif op_type == "raster":
                    current_grid = apply_raster_metrics(
                        gdf_grid=current_grid,
                        raster_path=source,
                        method=method,
                        stats=op.get("stats"),
                        out_column_prefix=op.get("out_prefix", "r_"),
                        n_processes=op.get("n_processes", 4),
                    )

                else:
                    print(
                        f"     [AVISO] Tipo '{op_type}' não reconhecido. Operação ignorada."
                    )

            except Exception as e:
                print(f"     [ERRO] Falha ao processar a operação {i}: {e}")

        cols_after = list(current_grid.columns)
        new_columns = [c for c in cols_after if c not in cols_before]

        # 3. Filtrar e Exportar Camada GeoPackage (Regra LuccME)
        if keep_only_updated:
            cols_to_keep = [id_field, "geometry"] + new_columns
            cols_to_keep = list(dict.fromkeys(cols_to_keep))
            export_gdf = current_grid[cols_to_keep]
        else:
            export_gdf = current_grid

        # Garantia de criação de diretório
        target_path = Path(target_gpkg)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Salvando em: {target_gpkg} (Camada: {layer_name})")
        driver = "GPKG" if target_gpkg.endswith(".gpkg") else None
        export_gdf.to_file(target_gpkg, layer=layer_name, driver=driver)

    # 3. Exportação de Topologia Espaço-Temporal 3D
    if cs is not None:
        print("\n[3/3] Exportando topologia espaço-temporal 3D...")
        cs.export_3d_topology_json(
            output_json="dados/topologia_3d.json",
            time_steps=[2015, 2020]
        )
        print("      Topologia 3D salva com sucesso em 'dados/topologia_3d.json'")

    print("\n==================================================")
    print("          TODOS OS ARQUIVOS FORAM GERADOS!        ")
    print("==================================================")


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    run_pipeline(config_file)