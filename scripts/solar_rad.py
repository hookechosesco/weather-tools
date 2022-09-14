import matplotlib.pyplot as plt
import xarray as xr
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeat
from cartopy.util import add_cyclic_point
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import matplotlib.colors
import metpy
from metpy import units
from metpy import calc as mpcalc
import itertools
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
from xarray.backends import NetCDF4DataStore
from netCDF4 import num2date
from siphon.catalog import TDSCatalog
from metpy.plots.ctables import registry
from matplotlib import patheffects
from datetime import datetime as dt
from matplotlib import colors as mcolors
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter
from matplotlib.ticker import MultipleLocator


def getTimeInHours(td):
    """
    Convert datetime object into hours. Used in calculating solar parameters
    """
    a, b, c, d = td.day*24, td.hour, td.minute/60, td.second/3600
    result = float(a+b+c+d)
    
    return result


def convTime(dtz, deglat, deglon, local):
    """
    convert local time to local solar time
    equations are explained in detail on Christiana Hinsberg and Stuart Bowden's website linked below
    https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time#:~:text=Local%20Solar%20Time%20(LST)%20and,time%20zones%20and%20daylight%20saving.
    """
    lat = np.deg2rad(deglat)
    lon = np.deg2rad(deglon)
    # local standard time meridian
    LSTM = np.deg2rad(15)*dtz
    d = local.timetuple().tm_yday
    B = np.deg2rad((360/365)*(d-81))
    # equation of time
    EoT = 9.87*np.sin(2*B) - 7.53*np.cos(B) - 1.5*np.sin(B)
    # time correction factor
    TC = np.deg2rad(4)*(lon-LSTM)+EoT
    # local solar time
    LST = local+datetime.timedelta(minutes=TC/60)
    # hour angle
    HRA = np.deg2rad(15)*getTimeInHours(LST - datetime.timedelta(hours=12))
    # sun declination
    decl = np.deg2rad(23.45)*(np.sin(np.deg2rad((360/365)*(d-81))))
    # sun elevation
    elev = np.arcsin(np.sin(decl)*np.sin(lat) + np.cos(decl)*np.cos(lat)*np.cos(HRA))
    # su azimuth
    if getTimeInHours(LST) < 12 or HRA < 0:
        azi = np.arccos((np.sin(decl)*np.sin(lat) - np.cos(decl)*np.sin(lat)*np.cos(HRA))/np.cos(elev))
    elif getTimeInHours(LST) > 12 or HRA > 0:
        azi = np.deg2rad(360) - np.arccos((np.sin(decl)*np.sin(lat) - np.cos(decl)*np.sin(lat)*np.cos(HRA))/np.cos(elev))
    
    # return declination, azimuth, and elevation in degrees, as well as time correction factor
    return np.rad2deg(decl), np.rad2deg(azi), np.rad2deg(elev), TC

    
def plotSolar(year, month, day, lat, lon):
    hours = np.arange(0, 24)
    minutes = np.arange(60)

    # create a "smooth" theoretical max line using minute increments
    # use the convTime function to get declination, azimuth, and elevation
    x = np.arange(0,24,1/60)
    time = [convTime(-4, lat, lon, datetime.datetime(year, month, day, i, j))[3] for i, j in itertools.product(hours, minutes)]
    elev = [convTime(-4, lat, lon, datetime.datetime(year, month, day, i, j))[2] for i, j in itertools.product(hours, minutes)]
    azi = [convTime(-4, lat, lon, datetime.datetime(year, month, day, i, j))[1] for i, j in itertools.product(hours, minutes)]

    # emperical formula for theoretica max surface solar radiation based off elevation
    # of the sun at a given time throughout the year, latitude, and longitude
    maxsolar =  1367*(np.sin(np.deg2rad(elev))+0.033*np.cos(np.deg2rad((360*80)/360))) # formula to get max solar rad

    fig, ax = plt.subplots(figsize=(9,6), dpi=100)
    ax2 = ax.twinx()
    h1 = ax.plot(x-dtime, elev, label='Elevation', color='tab:blue')
    idx = np.where(maxsolar > 0)[0]
    h2 = ax2.plot(x-dtime, maxsolar, label='Max Solar', color='tab:orange')
    ax.set_xlim([0,24])
    ax.set_ylim([0,90])
    ax2.set_ylim([0,1367])
    ax.set_xticks(np.arange(25)[::6])
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Sun Elevation (°)')
    ax.set_title(f'Solar noon at {datetime.datetime(year, month, day, 12, 0)-datetime.timedelta(hours=dtime)}')
    lns = h1+h2
    labs = [l.get_label() for l in lns]
    plt.legend(lns, labs)
    plt.show(block=False)


if __name__ == '__main__':
    cities = { 
        'Norman':(35.2455556, -97.4721389), # KOUN
        # 'Pittsburgh':(40.4914167, -80.2326944), # KPIT
        }

    # 24 hour forecast start date. As of right now, this only is set up to start at 00Z
    year, month, day = 2021, 4, 24
    fcst_time = datetime.datetime(year, month, day, 0, 0)

    # percent of the sky covered for each hour
    sky_coverage = np.append(np.linspace(100, 90, 12), np.linspace(90, 10, 12))
    
    # weights are based off of cloud type: thick low level cumulus block more solar, thin high cirrus blocks the least
    # weight = 1 means maximum solar blocking, weight = 0 no solar blocking (clear skies... sort of atmospheric chemistry also plays a role)
    weights = np.append(np.linspace(1, 0.8, 12), np.linspace(0.8, 0.1, 12))

    # multiply sky coverage by weights to estimate how much solar will reache the ground
    sky_coverage *= weights

    fig, ax = plt.subplots(figsize=(9,6), dpi=100)
    fig.patch.set_facecolor('white')
    colors = list(mcolors.TABLEAU_COLORS.keys())

    for i, city in enumerate(list(cities.keys())):
        lat, lon = cities[city]
        hours = np.arange(0, 24)
        minutes = np.arange(60)
        elev = [convTime(-4, lat, lon, datetime.datetime(2021, 4, 13, i, j))[2] for i, j in itertools.product(hours, minutes)]
        maxsolar =  1367*(np.sin(np.deg2rad(elev))+0.033*np.cos(np.deg2rad((360*80)/360))) # formula to get max solar rad
        fcst_solar = (1-sky_coverage/100)*maxsolar[::60]
        diff = (maxsolar[::60] - fcst_solar)/maxsolar[::60]
        print(fcst_solar)
        
        ax.plot(np.arange(24), fcst_solar, color=colors[i], label='Forecast')
        ax.plot(np.arange(24), maxsolar[::60], color=colors[i+1], label='Theoretical Max')
        ax.set_title(f'Solar Forecast {fcst_time.strftime(f"%m-%d-%Y")} at {city}')

    ax.set_ylim([0,1300])
    ax.legend(loc='upper left')
    ax.set_ylabel('Solar Irradiance (W/m$^{2}$)')
    fig.autofmt_xdate()
    ax.set_xlabel('Time')
    ax.set_xticks(np.arange(25)[::4])
    plt.savefig('imgs/solar/SolarFcst.png',dpi=300)
    plt.show(block=False)