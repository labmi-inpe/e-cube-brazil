from gpkg_to_netcdf import build_netcdf_cube_from_annual_gpkgs

# ------------------------------------------------------------------------------
# 1. Cubo Observado (Histórico)
# ------------------------------------------------------------------------------
observed_files = {
    2015: "dados/observed/ecube_2015.gpkg",
    2020: "dados/observed/ecube_2020.gpkg",
}

observed_layers = {2015: "cs_2015", 2020: "cs_2020"}

build_netcdf_cube_from_annual_gpkgs(
    file_year_map=observed_files,
    layer_map=observed_layers,
    out_nc_path="dados/nc_cubes/ecube_observed.nc",
)

# ------------------------------------------------------------------------------
# 2. Cenário VE (Transição Ecológica)
# ------------------------------------------------------------------------------
ve_scenario_files = {
    2027: "dados/scenarios/VE/ecube_2027.gpkg",
    2030: "dados/scenarios/VE/ecube_2030.gpkg",
    2035: "dados/scenarios/VE/ecube_2035.gpkg",
}

ve_layers = {2027: "cs_2027", 2030: "cs_2030", 2035: "cs_2035"}

build_netcdf_cube_from_annual_gpkgs(
    file_year_map=ve_scenario_files,
    layer_map=ve_layers,
    out_nc_path="dados/nc_cubes/ecube_scenario_VE.nc",
)

# ------------------------------------------------------------------------------
# 3. Cenário CV (Conservador)
# ------------------------------------------------------------------------------
cv_scenario_files = {
    2027: "dados/scenarios/CV/ecube_2027.gpkg",
    2030: "dados/scenarios/CV/ecube_2030.gpkg",
    2035: "dados/scenarios/CV/ecube_2035.gpkg",
}

cv_layers = {2027: "cs_2027", 2030: "cs_2030", 2035: "cs_2035"}

build_netcdf_cube_from_annual_gpkgs(
    file_year_map=cv_scenario_files,
    layer_map=cv_layers,
    out_nc_path="dados/nc_cubes/ecube_scenario_CV.nc",
)

# ------------------------------------------------------------------------------
# 4. Cenário TE (Tendencial)
# ------------------------------------------------------------------------------
te_scenario_files = {
    2027: "dados/scenarios/TE/ecube_2027.gpkg",
    2035: "dados/scenarios/TE/ecube_2035.gpkg",
}

te_layers = {2027: "cs_2027", 2035: "cs_2035"}

build_netcdf_cube_from_annual_gpkgs(
    file_year_map=te_scenario_files,
    layer_map=te_layers,
    out_nc_path="dados/nc_cubes/ecube_scenario_TE.nc",
)