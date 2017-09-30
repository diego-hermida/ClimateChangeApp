from ftplib import FTP

URL = 'podaac.jpl.nasa.gov'
FILES = ['antartica_mass.txt', 'greenland_mass.txt', 'ocean_mass.txt']
DIR = '/allData/tellus/L3/mascon/RL05/JPL/CRI/mass_variability_time_series'


def get_data():
    ftp = FTP(URL)
    ftp.login()
    ftp.cwd(DIR)  # Accessing directory

    file_names = [x for x in ftp.nlst() if x.endswith('.txt')]

    data = {}
    for (index, filename) in enumerate(FILES):
        temp = []
        ftp.retrbinary('RETR ' + file_names[index], temp.append)
        data[FILES[index]] = temp[0]
    ftp.quit()
    return data


if __name__ == '__main__':
    data = get_data()
