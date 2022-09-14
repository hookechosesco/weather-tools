import requests
from bs4 import BeautifulSoup
# import sys


def get_metar(icao, hoursback=None):
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
            obs += line
            obs += '\n'
    return obs


if __name__ == '__main__':

    icao = input('Enter ICAO: ').upper()
    hoursback = input('Enter hours back (Leave blank for most recent): ')

    # if len(sys.argv) > 1:
    #     icao = str(sys.argv[1]).upper()
    # else:
    #     icao = 'KPIT'

    # if len(sys.argv) > 2:
    #     hoursback = sys.argv[2]
    # else:
    #     hoursback = None

    ob = get_metar(icao, hoursback)
    print(f'Latest observation(s) from {icao}:\n{ob}')
