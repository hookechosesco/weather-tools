import requests
from bs4 import BeautifulSoup

def get_taf(icao):
    taf_url = f'https://www.aviationweather.gov/metar/data?ids={icao}&format=raw&hours=0&taf=on&layout=off'
    src = requests.get(taf_url).content
    soup = BeautifulSoup(src, "html.parser")

    metar_data = soup.find(id='awc_main_content_wrap')

    obs = ''
    for i, text in enumerate(metar_data):
        # print(i, text)
        if i <= 8: continue
        if str(text).startswith('<code>'):
            line = str(text).lstrip('<code>').rstrip('</code>')
            obs+=line
            obs+='\n'
    obs+=''
    return obs.replace('<br/>', '\n')

    
if __name__ == '__main__':

    icao = input('Enter ICAO: ').upper()
    taf = get_taf(icao)
    print(f'Latest observation(s) from {icao}:\n{taf}')
