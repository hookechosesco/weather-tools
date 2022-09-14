import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import metpy.calc as mpcalc
from metpy.cbook import get_test_data
from metpy.interpolate import cross_section

# Load in your dataset, this is prepared ahead of time from the ERA5 reanalysis for May 2015
data = xr.open_dataset('data/isentropic_example.nc').metpy.parse_cf()
data_proj = data.t.metpy.cartopy_crs
print(data)
print('-'*80)

# define the starting and ending locations in lat/lon degrees
start = (24.5561197,-81.7599558) # Key West, FL
end = (44.8074444,-68.8281389) # Bangor, ME

# create a cross section dataset using Metpy
cross = cross_section(data, start, end, steps=500).set_coords(('latitude', 'longitude'))

# make sure atm variables are the same shape so we can perform calculations
temp, pres, q = xr.broadcast(cross['t'], cross['level'], cross['q'])

# calculate potential temperature and relative humidity also using Metpy functions
cross_theta = mpcalc.potential_temperature(pres, temp)
rh = mpcalc.relative_humidity_from_specific_humidity(q, temp, pres)

# you can also add potential tempertaure to the original horizontal dataset
p, t = xr.broadcast(data['level'], data['t'])
theta = mpcalc.potential_temperature(p, t)
data['theta'] = xr.DataArray(theta, coords=data['t'].coords, dims=data['t'].dims, attrs={'units':theta.units})

# add newly derived variables to the cross section dataset
cross['Potential_temperature'] = xr.DataArray(cross_theta, coords=temp.coords, dims=temp.dims, attrs={'units':cross_theta.units})
cross['Relative_humidity'] = xr.DataArray(rh, coords=q.coords, dims=q.dims, attrs={'units':rh.units})

# convert wind units from m/s to kts
cross['u'].metpy.convert_units('knots')
cross['v'].metpy.convert_units('knots')
# can also calculate tangential and normal winds
cross['t_wind'], cross['n_wind'] = mpcalc.cross_section_components(cross['u'],cross['v'])

print(cross)
print('-'*80)

# define the figure object and primary axes
fig = plt.figure(1, figsize=(16, 9))
ax = plt.axes()

# plot RH using contourf
rh_contour = ax.contourf(cross['longitude'], cross['level'], cross['Relative_humidity'],
                         levels=np.arange(0, 1.05, .05), cmap='YlGnBu')
rh_colorbar = fig.colorbar(rh_contour)

# plot potential temperature using contour, with some custom labeling
theta_contour = ax.contour(cross['longitude'], cross['level'], cross['Potential_temperature'],
                           levels=np.arange(250, 450, 5), colors='k', linewidths=2)
theta_contour.clabel(theta_contour.levels[1::2], fontsize=8, colors='k', inline=1,
                     inline_spacing=8, fmt='%i', rightside_up=True, use_clabeltext=True)

# plot winds with some custom indexing to make the barbs less crowded
# wind_slc_vert = list(range(0, 19, 2)) + list(range(19, 29))
wind_slc_horz = slice(0, 500, 25)
# here we will plot horizontal wind onto the cross section
ax.barbs(cross['longitude'][wind_slc_horz], cross['level'][:],
         cross['u'][:, wind_slc_horz],
         cross['v'][:, wind_slc_horz], color='k')

# adjust the y-axis to be logarithmic
ax.set_yscale('symlog')
ax.set_yticklabels(np.arange(1000, 50, -100))
ax.set_ylim(cross['level'].max(), cross['level'].min())
ax.set_yticks(np.arange(1000, 50, -100))

# define the CRS and inset axes
data_crs = data['z'].metpy.cartopy_crs
ax_inset = fig.add_axes([0.125, 0.65, 0.25, 0.25], projection=data_crs)

# plot geopotential height at 500 hPa
z_contour = ax_inset.contour(data['longitude'], data['latitude'], data['z'].sel(level=500.)/100,
                 levels=np.arange(510, 600, 6), colors='black')
z_contour.clabel(z_contour.levels, fontsize=8, colors='k', inline=1,
                     inline_spacing=8, fmt='%i', rightside_up=True, use_clabeltext=True)
# ax_inset.contourf(data['longitude'], data['latitude'], data['theta'].sel(level=1000.), smap='inferno')

# Plot the path of the cross section
endpoints = data_crs.transform_points(ccrs.Geodetic(),*np.vstack([start, end]).transpose()[::-1])
ax_inset.scatter(endpoints[:, 0][0], endpoints[:, 1][0], c='tab:green', zorder=2)
ax_inset.scatter(endpoints[:, 0][1], endpoints[:, 1][1], c='tab:red', zorder=2)
ax_inset.plot(cross['longitude'], cross['latitude'], c='k', zorder=2)

# Add geographic features
ax_inset.coastlines()
ax_inset.add_feature(cfeature.STATES.with_scale('50m'), edgecolor='k', alpha=0.2, zorder=0)

# Set the titles and axes labels
ax_inset.set_title('')
ax.set_title('ERA5 Cross-Section \u2013 {} to {} \u2013 Valid: {}\n'
             'Potential Temperature (K), Horizontal Winds (knots), '
             'Relative Humidity\n'
             'Inset: Cross-Section Path and 500 hPa Geopotential Height'.format(
                 start, end, cross['time'].dt.strftime('%Y-%m-%d %H:%MZ').item()))
ax.set_ylabel('Pressure (hPa)')
ax.set_xlabel('Longitude (degrees east)')
rh_colorbar.set_label('Relative Humidity (dimensionless)')

# save completeed figure in the imgs directory
plt.savefig('imgs/cross_section/cross_section.png', bbox_inches='tight')
# plt.show()
