import itertools
import os
import sys
import requests
import datetime
from datetime import datetime as dt

import matplotlib.pyplot as plt
import matplotlib.colors
import matplotlib as mpl
import matplotlib.path as mpath
from matplotlib import colors as mcolors
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter
from matplotlib.ticker import MultipleLocator
from matplotlib import patheffects

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

import cartopy.crs as ccrs
import cartopy.feature as cfeat
from cartopy.util import add_cyclic_point
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

from netCDF4 import num2date
import xarray as xr
from xarray.backends import NetCDF4DataStore

import metpy
from metpy import units
from metpy import calc as mpcalc
from metpy.plots.ctables import registry
from siphon.catalog import TDSCatalog


def get_goes_image(date=dt.utcnow(), channel=13, region='CONUS'):
    """Return dataset of GOES-16 data."""
    cat = TDSCatalog('https://thredds.ucar.edu/thredds/catalog/satellite/goes/east/products/'
                     'CloudAndMoistureImagery/{}/Channel{:02d}/{:%Y%m%d}/'
                     'catalog.xml'.format(region, channel, date))

    ds = cat.datasets[0]  # Get most recent dataset
    ds = ds.remote_access(service='OPENDAP')
    ds = NetCDF4DataStore(ds)
    ds = xr.open_dataset(ds)

    return ds


def plot_cities(ax, data_crs, color, label=True):

    cities = {
        # 'Grand Junction':(39.1222, -108.5291), # Grand Junction: 39.1222° N, 108.5291° W
        'Albuquere': (35.0844, -106.6504),  # Albuquere: 35.0844° N, 106.6504° W
        # 'Riverton':(43.0613, -108.4584), # Riverton: 43.0613° N, 108.4584° W
        'Denver': (39.8561, -104.6737),  # Denver: 39.8561° N, 104.6737° W
        # 'North Platte':(41.1327, -100.6980),  # North Platte: 41.1327° N, 100.6980° W
        # 'Dodge City':(37.7602, -99.9674), # Dodge City: 37.7602° N, 99.9674° W
        # 'Rapid City':(44.0384, -103.0605), # Rapid City: 44.0384° N, 103.0605° W
        # 'Philadelphia':(39.87, -75.23), # KPHL
        # 'Baltimore':(39.2904, -76.6122), # KBWI
        'Washington DC': (38.85, -77.03),  # KDCA
        # 'Richmond':(37.51, -77.32), # KRIC
        # 'Norfolk':(36.93, -76.30), # KNGU
        # 'Raleigh':(35.89, -78.78), # KRDU
        # 'Dover':(39.13, -75.47), # KDOV
        'Chicago': (41.8781, -87.6298),
        # 'Bismark':(46.8083, -100.7837),
        'Little Rock': (34.7465, -92.2896),
        'Amarillo': (35.2203, -101.7075),  # Amarillo: 35.2203° N, 101.7075° W
        'Norman': (35.2455556, -97.4721389),  # KOUN
        'Pittsburgh': (40.4914167, -80.2326944),  # KPIT
        # 'Venango':(41.3774167, -79.8606389), # KFKL
        # 'NMB': (33.8117500, -78.7239444),
        # Wind farms
        'Highland': (43.0042, -95.6068),  # KSPW
        'Ashtabula': (47.0975, -97.9106),  # KBAC
        'Thunder Spirit': (46.0453, -102.6003),
    }

    for city, coord in cities.items():
        at_x, at_y = ax.projection.transform_point(coord[1], coord[0], src_crs=data_crs)
        ax.plot(at_x, at_y, 'r*', ms=60, markeredgecolor='black')
        if label:
            if city == 'Thunder Spirit':
                ax.annotate(city, xy=(at_x, at_y), xytext=(-100, -20), textcoords='offset points', ha='center', va='top', size=60, color=color, path_effects=[patheffects.withStroke(linewidth=5, foreground='black')])
            else:
                ax.annotate(city, xy=(at_x, at_y), xytext=(-80, 80), textcoords='offset points', ha='center', va='top', size=60, color=color, path_effects=[patheffects.withStroke(linewidth=5, foreground='black')])

    return cities


def plotGOES(channel, cities=True):
    # channel 9 in mid WV, channel 13 is clean LWIR
    ds = get_goes_image(channel=channel)
    # Parse out the projection data from the satellite file
    dat = ds.metpy.parse_cf('Sectorized_CMI')
    proj = dat.metpy.cartopy_crs
    # Pull out what we need from the GOES netCDF file
    x = dat['x']
    y = dat['y']

    # Make the plot
    fig = plt.figure(figsize=(1.375 * 40, 40))
    fig.patch.set_facecolor('white')
    ax = fig.add_subplot(1, 1, 1, projection=proj)
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)

    im = ax.imshow(dat, extent=(x.min(), x.max(), y.min(), y.max()), origin='upper')
    if channel == 9:  # water vapor image
        tickmin, tickmax = 160, 280
        norm, cmap = registry.get_with_range('WVCIMSS_r', tickmin, tickmax)
        fname = 'WVsat'

    elif channel == 13:  # infrared image
        tickmin, tickmax = 160, 330
        norm, cmap = registry.get_with_range('ir_drgb', tickmin, tickmax)
        fname = 'IRsat'

    else:
        tickmin, tickmax = dat.min(), dat.max()
        cmap = 'Greys'
        norm = mpl.colors.Normalize(tickmin, tickmax)
        fname = 'sat'

    tickloc = np.arange(tickmin, tickmax+1, 20)
    im.set_cmap(cmap)
    im.set_norm(norm)

    cbar = fig.colorbar(im, ax=ax, shrink=.6, pad=0.01)
    cbar.set_label('Temperature (K)', size=60)
    cbar.ax.tick_params(labelsize=60, direction='out', length=50, width=5)
    cbar.set_ticks(tickloc)

    ax.add_feature(cfeat.BORDERS, linewidth=8, edgecolor='black')
    ax.add_feature(cfeat.STATES.with_scale('50m'), linestyle='-',
                   edgecolor='black', linewidth=4)
    ax.set_extent([-110, -70, 50, 25])

    timestamp = datetime.datetime.strptime(ds.start_date_time, '%Y%j%H%M%S')
    text_time = ax.text(0.01, 0.01, timestamp.strftime('%d %B %Y %H%MZ'),
                        horizontalalignment='left', transform=ax.transAxes,
                        color='white', fontsize=100, weight='bold')

    outline_effect = [patheffects.withStroke(linewidth=15, foreground='black')]
    text_time.set_path_effects(outline_effect)

    lon_grid = np.arange(-180, 181, 5)
    lat_grid = np.arange(-90, 91, 5)
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                      linewidth=5, color='gray', alpha=0.7, linestyle='--',
                      xlocs=lon_grid, ylocs=lat_grid, x_inline=False, y_inline=False,)
    gl.bottom_labels = False
    gl.right_labels = False
    gl.xlines = True
    # gl.xlocator = mticker.FixedLocator([-110, -105, -100, -95, -90, -85])
    # gl.ylocator = mticker.FixedLocator([25, 30, 35])
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlabel_style = {'rotation': 0, 'size': 30, 'color': 'red'}
    gl.ylabel_style = {'rotation': 0, 'size': 30, 'color': 'blue'}

#     xloc = [x for x in range(0, 90, 10)]
#     yloc = [x for x in range(-150, -50, 10)]
#     ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, xlocs=xloc, ylocs=yloc, linestyle=':', color='black', linewidth=2)

    if cities:
        cities = plot_cities(ax, ccrs.PlateCarree(), 'white', label=True)
    fpath = f'../imgs/satellite/{fname}_{timestamp.strftime("%Y%m%dT%H%MZ")}.png'
    plt.savefig(fpath, bbox_inches='tight')
    plt.show(block=False)

    return cities, fpath


if __name__ == '__main__':
    # plot a goes east image from cahnnel 9 (mid-level water vapor)
    # channel 13 is infrared
    # channel 2 is traditional daytime visibile (black and white)
    channel = int(input('Enter GOES channel (Visible=2, Mid-level WV=9, IR=13): '))
    success = False
    i = 0
    while not success:
        if i == 3:
            print('I/O error. Try again later.')
            sys.exit(1)
        try:
            cities, fpath = plotGOES(channel=channel)
            success = True
            print(f'Satellite image saved at {fpath}')
        except OSError as e:
            print(f'Download failed, trying again... ({x}/3 tries)')
            time.sleep(2)
            i += 1










