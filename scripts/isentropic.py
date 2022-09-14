import metpy.calc as mpcalc
from metpy.units import units
import numpy as np
import xarray as xr
import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import warnings


warnings.simplefilter('ignore')

# open netCDF4 file with xarray and parse data to CF standard using Metpy
ds = xr.open_dataset('data/isentropic_example.nc').metpy.parse_cf()
data_proj = ds.t.metpy.cartopy_crs
time = ds.time.values

# extract atmospehric variables
temperature = ds.t
lat = temperature.metpy.y
lon = temperature.metpy.x
mixing = ds.q
z = ds.z
u = ds.u
v = ds.v

# Can have different vertical levels for wind and thermodynamic variables
# Find and select the common levels
press = temperature.metpy.vertical
common_levels = np.intersect1d(press, u.metpy.vertical)
temperature = temperature.metpy.sel(vertical=common_levels)
u = u.metpy.sel(vertical=common_levels)
v = v.metpy.sel(vertical=common_levels)

# Get common pressure levels as a data array
press = press.metpy.sel(vertical=common_levels)

# Needed to make numpy broadcasting work between 1D pressure and other 3D arrays
# Use .metpy.unit_array to get numpy array with units rather than xarray DataArray
pressure_for_calc = press.metpy.unit_array[:, None, None]  

mixing['units'] = 'dimensionless'

# Interpolate all the data
isen_level = np.array([290, 295, 300, 305, 310]) * units.kelvin

# use Metoy to interpolate data 
ret = mpcalc.isentropic_interpolation(isen_level, press, temperature, mixing, u, v)
isen_press, isen_mixing, isen_u, isen_v = ret


# Squeeze the returned arrays
isen_press = isen_press.squeeze()
isen_mixing = isen_mixing.squeeze()
isen_u = isen_u.squeeze()
isen_v = isen_v.squeeze()

# search through the image directory to see if the plot already exists
for isen_level_idx, isen_lvl in enumerate(isen_level):
    fname = f'imgs/isentropic/{isen_lvl.m}K_{str(time)[0:13]}.png'
    print(fname)
    if os.path.isfile(fname): 
        print('Already have it')
        continue

    # smoothe the data to get a better snapshot of synoptic conditions
    isen_press = mpcalc.smooth_gaussian(isen_press.squeeze(), 9)
    isen_u = mpcalc.smooth_gaussian(isen_u.squeeze(), 9)
    isen_v = mpcalc.smooth_gaussian(isen_v.squeeze(), 9)

    # use .values because we don't care about using DataArray
    dx, dy = mpcalc.lat_lon_grid_deltas(lon.values, lat.values)
    lift = -mpcalc.advection(isen_press[isen_level_idx], [isen_u[isen_level_idx], 
                                                          isen_v[isen_level_idx]], [dx, dy], dim_order='yx')

    # plot isentropic ascent and pressure levels
    fig = plt.figure(figsize=(14, 8), dpi=200)
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.LambertConformal(central_longitude=-100))
    fig.patch.set_facecolor('white')
    ax.add_feature(cfeature.COASTLINE)

    levels = np.arange(300, 1000, 25)
    cntr = ax.contour(lon, lat, isen_press[isen_level_idx], transform=data_proj, colors='black', levels=levels)
    cntr.clabel(fmt='%d')

    # plot isentropic wind in knots
    lon_slice = slice(None, None, 5)
    lat_slice = slice(None, None, 5)
    ax.barbs(lon[lon_slice], lat[lat_slice],
             isen_u[isen_level_idx, lon_slice, lat_slice].to('knots').magnitude,
             isen_v[isen_level_idx, lon_slice, lat_slice].to('knots').magnitude,
             transform=data_proj, zorder=2, length=5, regrid_shape=50)

    # plot isentropic vertical motion in microbar/s
    levels = np.arange(-6, 7)
    cs = ax.contourf(lon, lat, lift.to('microbar/s'), levels=levels, cmap='RdBu',
                     transform=data_proj, extend='both')
    plt.colorbar(cs)

    # add US/State boundaries using Cartopy
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linewidth=2)
    ax.add_feature(cfeature.STATES, linestyle=':')

    ax.set_extent((-120, -70, 25, 55), crs=data_proj)
#         plt.show()
    plt.savefig(fname, bbox_inches='tight')
    plt.close(fig)
