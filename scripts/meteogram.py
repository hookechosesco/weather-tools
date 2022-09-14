import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange
import requests
from bs4 import BeautifulSoup
import xarray as xr
import numpy as np
import pandas as pd
import metpy.calc as mpcalc
from metpy.plots import SkewT, Hodograph
from metpy.units import units, concatenate, pandas_dataframe_to_unit_arrays
from datetime import timedelta
from datetime import datetime as dt
from siphon.simplewebservice.wyoming import WyomingUpperAir
import metpy.calc as mpcalc
from metpy.calc import resample_nn_1d
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from metpy.io import parse_metar_to_dataframe
import warnings


def to_heat_index(T, Td):
    T = T*units('degF')
    Td = Td*units('degF')
    RH = mpcalc.relative_humidity_from_dewpoint(T, Td)
    HI = mpcalc.heat_index(T, RH)
    return HI


def to_wind_chill(T, wspd):
    T = T*units('degF')
    wspd = wspd*units('kts').to('mph')
    windchill = mpcalc.windchill(T, wspd)
    return windchill


def get_metar_meteogram(icao, hoursback=None):
    """
    Download METAR from the NOAA Avation Weather Center

    Parameters
    ----------
    icao : str
        ICAO identifier used when reporting METARs
    hoursback : str or int
        Number of hours before present to query

    Returns
    ----------
    obs : str
        str with each observation as a seperate line (\n)
    """

    if hoursback:
        metar_url = f'https://www.aviationweather.gov/metar/data?ids={icao}&format=raw&date=&hours={hoursback}&taf=off'
    else:
        metar_url = f'https://www.aviationweather.gov/metar/data?ids={icao}&format=raw&date=&hours=0&taf=off'
    src = requests.get(metar_url).content
    soup = BeautifulSoup(src, "html.parser")
    metar_data = soup.find(id='awc_main_content_wrap')

    obs = ''
    for i in metar_data:
        if str(i).startswith('<code>'):
            line = str(i).lstrip('<code>').rstrip('</code>')
            obs+=line
            obs+='\n'
    return obs


def meteogram(icao, hoursback):
    icaos = [icao.upper()]
    # z = 19
    for i,icao in enumerate(icaos):
        txt = get_metar_meteogram(icao, hoursback).split('\n')[:-1]
        if i == 0:
            df = parse_metar_to_dataframe(txt[-1])
        for row in txt[::-1]:
      #     if row.startswith(f'{icao} 13{z-1}'):
      #     print(row)
            df = df.append(parse_metar_to_dataframe(row))
      # df = df.set_index('date_time')
      # print(df)
#     df = df.dropna(inplace=True)
    df['tempF'] =  (df['air_temperature'] * 9/5) + 32
    df['dewF'] =  (df['dew_point_temperature'] * 9/5) + 32
    df['heat_index'] = to_heat_index(df['tempF'].values, df['dewF'].values)
    ## nan HI values where air temp < 80 F 
    df.loc[df['tempF'] < 80, ['heat_index']] = np.nan
    df['wind_chill'] = to_wind_chill(df['tempF'].values, df['wind_speed'].values)
    ## nan wind chill values where speed <= 5 mph or air temp > 50
    df.loc[df['wind_speed'] <= 5, ['wind_chill']] = np.nan
    df.loc[df['tempF'] > 50, ['wind_chill']] = np.nan
#     unit_df = pandas_dataframe_to_unit_arrays(df, column_units=df.units)
    try:
        df['wet_bulb'] = mpcalc.wet_bulb_temperature(df['air_pressure_at_sea_level'].values*units('hPa'),
                                                 df['air_temperature'].values*units('degC'),
                                                 df['dew_point_temperature'].values*units('degC')).to('degF').m
    except ValueError as e:
        print("Can't calculate wet bulb")
        df['wet_bulb'] = np.nan

    WNDDIR = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N']
    WNDDEG = np.arange(0, 361, 22.5)
  # WIND = dict(zip(WNDDIR, WNDDEG))
  # colors = list(mcolors.TABLEAU_COLORS.keys())

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4,1,figsize=(18,18), dpi=150, sharex=True)
    fig.patch.set_facecolor('white')

    ax1.plot(df['date_time'], df['tempF'], label='$T$', linestyle='-', marker='', color='tab:red')
    ax1.plot(df['date_time'], df['wet_bulb'], label='$T_w$', linestyle='-', marker='', color='tab:blue')
    ax1.plot(df['date_time'], df['dewF'], label='$T_d$', linestyle='-', marker='', color='tab:green')
    ax1.plot(df['date_time'], df['heat_index'], label='$RF$', linestyle='-', marker='', color='tab:orange')
    ax1.plot(df['date_time'], df['wind_chill'], label='$WC$', linestyle='-', marker='', color='tab:purple')

    ax1.set_ylabel('Temperature (°F)')
    ax1.set_xlabel('Z-Time (MM-DD HH)')
    ax1.set_title(f"{df['station_id'][0]}\n{df['date_time'][0].strftime('%Y-%m')}")
    ax1.set_xticks(pd.date_range(df['date_time'][0].strftime('%Y-%m-%d %H'), df['date_time'][-1].strftime('%Y-%m-%d %H'), freq='2H'))
    ax1.set_xticklabels(pd.date_range(df['date_time'][0].strftime('%Y-%m-%d %H'), df['date_time'][-1].strftime('%Y-%m-%d %H'), freq='2H').strftime('%m-%d %H%MZ'))
   # ax1.set_ylim([40, 100])
    ax1.grid(which='both')
    ax1.grid(which='major', axis='x', color='black')
    ax1.legend(loc='upper left')

    ax2b = ax2.twinx()
    ax2.plot(df['date_time'], df['wind_speed']*1.15078, label='Speed', linestyle='-', marker='', color='tab:blue')
    lines_1, labels_1 = ax2.get_legend_handles_labels()
    ax2b.plot(df['date_time'], df['wind_direction'], label='Direction', linestyle='', marker='*', color='tab:cyan')
    lines_2, labels_2 = ax2b.get_legend_handles_labels()
    max_wind = df['wind_speed'].max()*1.15078
    if max_wind > 30:
        ax2.set_ylim([0, max_wind+5])
    else:
        ax2.set_ylim([0, 30])
    ax2.set_ylabel('Wind Speed (mph)')
    ax2b.set_ylabel('Wind Direction (°)')
    ax2b.set_ylim([-10,370])
    ax2b.set_yticks(WNDDEG[::4])
    ax2b.set_yticklabels(WNDDIR[::4])
    ax2.grid(which='both')
    ax2.grid(which='major', axis='x', color='black')
    lines = lines_1 + lines_2
    labels = labels_1 + labels_2
    ax2.legend(lines, labels, loc='upper left')

    
    ax3.plot(df['date_time'], df['altimeter'], label='Altimeter', linestyle='-', marker='', color='tab:brown')
    ax3.set_ylabel('Pressure (inHg)')
   # ax3.set_ylim([29.70, 30.10])
    ax3.grid(which='both')
    ax3.grid(which='major', axis='x', color='black')


    ax4.plot(df['date_time'], df['low_cloud_level']/1000, label='Low', linestyle='', marker='*')
    ax4.plot(df['date_time'], df['medium_cloud_level']/1000, label='Medium', linestyle='', marker='*')
    ax4.plot(df['date_time'], df['high_cloud_level']/1000, label='High', linestyle='', marker='*')
    ax4.plot(df['date_time'], df['highest_cloud_level']/1000, label='Highest', linestyle='', marker='*')
    ax4.set_ylim([0, 30])
    ax4.set_ylabel('Cloud Height (kft)')
    ax4.set_xlabel('Date (MM-DD-HH Z)')
    ax4.set_xticks(pd.date_range(df['date_time'][0].strftime('%Y-%m-%d %H'), (df['date_time'][-1]+timedelta(hours=6)).strftime('%Y-%m-%d %H'), freq='6H'))
    ax4.set_xticklabels(pd.date_range(df['date_time'][0].strftime('%Y-%m-%d %H'), (df['date_time'][-1]+timedelta(hours=6)).strftime('%Y-%m-%d %H'), freq='6H').strftime('%d %HZ'))
    ax4.legend(loc='upper left')
    ax4.xaxis.set_major_locator(DayLocator())
    ax4.xaxis.set_minor_locator(HourLocator(range(0, 25, 3)))
    ax4.grid(which='both')
    ax4.grid(which='major', axis='x', color='black')
#     ax4.grid(which='minor', axis='x', linewidth=0.5)
    ax4.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    ax4.xaxis.set_minor_formatter(DateFormatter('%H'))
    fig.autofmt_xdate(rotation=50)
    fname = f"../imgs/meteogram/metorgram_{df['station_id'][0]}.png"
    plt.savefig(fname, bbox_inches='tight')
    plt.close(fig)

    return fname, df


if __name__ == '__main__':
    # suppress warnings about NaNs
    warnings.simplefilter('ignore')

    # check to see if user provided a location
    #if len(sys.argv) > 1:
        # save first command line argument following 'python' as the ICAO
    #    icao = str(sys.argv[1]).upper()
    #else:
        # if no location provided, default to Pittsburgh
    #    icao = 'KPIT'

    # check to see if user provided a time frame
    #if len(sys.argv) > 2:
        # save second command line argument as the hours back in time from present
    #    hoursback = sys.argv[2]
    #else:
        # default hours back in time is one day (24 hours)
    #    hoursback = 24

    # call meteogram plotting function and print file path/name
    icao = input('Enter ICAO: ').upper()
    hoursback = input('Enter hours back (Leave blank for most recent): ')
    fname, df = meteogram(icao, hoursback)
    print(f'Meteogram for {icao} created.\n{fname}\n')

    rmks = df['remarks']
    pk_wnds = [x.split('AO2 PK WND ')[1][0:10] for x in rmks if 'PK WND' in x]
    pk_dict = dict(zip([x.split('/')[1] for x in pk_wnds], [x.split('/')[0] for x in pk_wnds]))
    max_wnds = np.array([x[-2:] for x in pk_dict.values()], dtype=float)
    print(f'Max wind {max_wnds.max()}')