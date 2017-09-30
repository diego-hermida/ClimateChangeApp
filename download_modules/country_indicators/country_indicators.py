import requests

BASE_URL = 'http://api.worldbank.org/{LANG}/countries/{COUNTRY}/indicators/{INDICATOR}?date={BEGIN_DATE}:{END_DATE}' \
           '&format=json&?per_page=1000000'
LANG = 'EN'
COUNTRIES = ['ES', 'FR']  # ISO2 Country Codes
INDICATORS = ['SP.POP.TOTL', 'SP.POP.GROW', 'SP.URB.TOTL', 'SP.URB.GROW', 'EN.ATM.CO2E.KT', 'EN.ATM.METH.KT.CE',
              'EN.ATM.NOXE.KT.CE', 'EN.ATM.GHGO.KT.CE']
BEGIN_DATE = '1900'
END_DATE = '2017'


def get_data():
    data = {}
    for indicator in INDICATORS:
        indicator_data = []
        for country in COUNTRIES:
            url = BASE_URL.replace('{LANG}', LANG).replace('{COUNTRY}', country).replace('{INDICATOR}', indicator). \
                replace('{BEGIN_DATE}', BEGIN_DATE).replace('{END_DATE}', END_DATE)
            r = requests.get(url)
            indicator_data.append(r.content)
        data[indicator] = indicator_data
    return data


if __name__ == '__main__':
    data = get_data()
