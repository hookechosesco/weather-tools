#!/Users/virgil/anaconda3/envs/metr/bin/python

import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import xarray as xr
import numpy as np
import pandas as pd
import metpy.calc as mpcalc
from metpy.plots import SkewT, Hodograph
from metpy.units import units, concatenate
from datetime import timedelta
from datetime import datetime as dt
from siphon.simplewebservice.wyoming import WyomingUpperAir
from metpy.calc import resample_nn_1d
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


def my_wetbulb(p, T, Td):
    it = np.nditer([p, T, Td, None],
                   op_dtypes=['float', 'float', 'float', 'float'],
                   flags=['buffered'])

    n = 0
    for press, temp, dewp, ret in it:
        n += 1
        press = press * p.units
        temp = temp * T.units
        dewp = dewp * Td.units
        lcl_pressure, lcl_temperature = mpcalc.lcl(press, temp, dewp)
        moist_adiabat_temperatures = mpcalc.moist_lapse(
            concatenate([lcl_pressure, press]), lcl_temperature
        )

        if moist_adiabat_temperatures.size == 0:
            print(f'Dewpoint Depression = 0 at {press}')
#             ret[...] = ((temp.m + dewp.m)/2) * T.units
            ret[...] = np.nan

        else:
            # print(f'{n} {press.m} {temp.m:.2f} {dewp.m:.2f} {moist_adiabat_temperatures.size}')
            ret[...] = moist_adiabat_temperatures[-1].magnitude

    return it.operands[3] * moist_adiabat_temperatures.units


def make_skewt(station, hoursback=None):

    current_date = dt.utcnow()
    if 0 <= current_date.hour < 12:
        format_date = current_date.replace(microsecond=0, second=0, minute=0, hour=0)
    else:
        format_date = current_date.replace(microsecond=0, second=0, minute=0, hour=12)
    if hoursback:
        format_date -= timedelta(hours=hoursback)

    # print(format_date)
    ds = xr.Dataset.from_dataframe(WyomingUpperAir.request_data(format_date, station.strip('K')))
    # Set units for variables
    height = ds.height * units.meter
    p = ds.pressure.values * units.hPa
    T = ds.temperature.values * units.degC
    TK = T.to('kelvin')
    Td = ds.dewpoint.values * units.degC
    TdK = Td.to('kelvin')
    wind_speed = ds.speed.values * units.knots
    wind_dir = ds.direction.values * units.degrees
    u, v = mpcalc.wind_components(wind_speed, np.deg2rad(wind_dir))

    # Drop any rows with all NaN values for T, Td, winds
    ds = ds.dropna(
        'index',
        how='all',
        subset=['temperature', 'dewpoint', 'direction', 'speed', 'u_wind', 'v_wind']
    )

    #Can change the size of the figure by modifying 'figsize' to desired dimensions
    fig = plt.figure(figsize=(12, 12), dpi=300)
    fig.patch.set_facecolor('white')
    skew = SkewT(fig, rotation=45)

    # Plot the data using normal plotting functions, in this case using
    # log scaling in Y, as dictated by the typical meteorological plot
    skew.plot(p, T, 'red')
    skew.plot(p, Td, 'green')

    try:
        # Plot wetbulb as blue line
        # wb = mpcalc.wet_bulb_temperature(p, T, Td)
        wb = my_wetbulb(p, T, Td)
        skew.plot(p, wb, 'blue', linewidth=1, alpha=0.5)
    except (IndexError, RuntimeError, ValueError) as e:
        print(e)

    skew.ax.set_ylim(1050, 100)
    # if (T.min() < -30):
    # skew.ax.set_xlim(T.min()-5, (T.min()-5)+80)
    # else:
    skew.ax.set_xlim(-40, 40)

    # only plot winds every 50 mb. You can modify this if desired.
    interval = np.append(np.arange(0, 850, 50), np.arange(850, 1051, 25)) * units('hPa')
    ix = resample_nn_1d(p, interval)
    skew.plot_barbs(p[ix], u[ix], v[ix])

    # Calculate LCL height and plot as black dot
    lcl_pressure, lcl_temperature = mpcalc.lcl(p[0], T[0], Td[0])
    skew.plot(lcl_pressure, lcl_temperature, 'ko', markerfacecolor='black', markersize=3)
    # Calculate full parcel profile and add to plot as black line
    prof = mpcalc.parcel_profile(p, TK[0], TdK[0]).to('degC')
    skew.plot(p, prof, 'k', linewidth=1)

    # Plot path and LCL as triangle for elevated parcels
    skew.shade_cape(p, T, prof)

    # An example of a slanted line at constant T -- in this case the 0 isotherm
    skew.ax.axvline(0, color='b', linestyle='-', linewidth=1)
    skew.ax.axvline(-12, color='c', linestyle='-', linewidth=1)
    skew.ax.axvline(-17, color='c', linestyle='-', linewidth=1)

    # Add the relevant special lines
    skew.plot_dry_adiabats(t0=np.arange(-40, 200, 10)*units.degC, color='brown', linewidth=0.75, linestyle='-', alpha=0.5)
    skew.plot_moist_adiabats(color='green', linewidth=0.75, linestyle='-', alpha=0.5)

    # Use custom mixing ratio lines. w is kg/kg to begin with, then labeled as g/kg
    p_mix = np.linspace(200*units.hPa, 1000 * units.hPa)
    w_mix = np.array([0.0004, 0.001, 0.002, 0.004, 0.007, 0.010, 0.016, 0.020, 0.032]).reshape(-1, 1)
    td = mpcalc.dewpoint(mpcalc.vapor_pressure(p_mix, w_mix))
    x_text = [t[-1] for t in td.magnitude]
    skew.plot_mixing_lines(w_mix, p_mix, color='green', linewidth=1, alpha=0.5)
    # loop over each array of mixing ratio coords and label as g/kg on the figure
    for i, x in enumerate(x_text):
        skew.ax.text(x, 900, size=6, s=f'{w_mix[i][0]*1000} $g/kg$', horizontalalignment='right',
                     verticalalignment='bottom', rotation=57, alpha=0.5)

    plt.title(f'{station} {format_date.strftime(f"%d%h%Y %HZ").upper()}', weight='bold', size=20)
    skew.ax.set_xlabel('Temperature [$^{\circ}C$]')
    skew.ax.set_ylabel('Pressure [$hPa$]')
    plt.text(1.1, 0.4, 'Wind Speed [$kts$]', rotation=270, transform=skew.ax.transAxes)

    #Change the 30% to alter size, currently plotting in top left (can change loc)
    ax_hod = inset_axes(skew.ax, '25%', '20%', loc='upper left')
    h = Hodograph(ax_hod, component_range=80)  # Change range in windspeeds
    h.add_grid(increment=10)
    try:
        h.plot_colormapped(u, v, height)
    except ValueError as e:
        print(e)
    # Save and show the plot
    fname = f'../imgs/skewt/{station}_{format_date.strftime(f"%d%h%Y_%HZ").upper()}.png'
    plt.savefig(fname, bbox_inches='tight')
    # plt.show()
    plt.close(fig)

    return fname


if __name__ == '__main__':
    icao = input('Enter ICAO: ').upper()
    # icao = 'IAD'
    hoursback = input('Enter hours back (Leave blank for most recent): ')
    fname = make_skewt(icao, hoursback)
    print(f'SkewT created for {icao} saved at {fname}')
