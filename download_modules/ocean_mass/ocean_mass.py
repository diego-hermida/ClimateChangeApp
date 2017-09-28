from ftplib import FTP

URL = 'podaac.jpl.nasa.gov'
FILES = ['antartica_mass.txt', 'greenland_mass.txt', 'ocean_mass.txt']
DIR = '/allData/tellus/L3/mascon/RL05/JPL/CRI/mass_variability_time_series'

def save_data():

    # Connecting to FTP server
    ftp = FTP(URL)

    # Login to FTP server
    ftp.login()

    # Accessing directory
    ftp.cwd(DIR)

    # Retrieving requested filename
    l = [x for x in ftp.nlst() if x.endswith('.txt')]

    # Downloading content to file
    for (index, filename) in enumerate(FILES):
        with open(filename, 'wb') as f:
            ftp.retrbinary('RETR ' + l[index], f.write)

    # Disconnecting from FTP server
    ftp.quit()


if __name__ == '__main__' :
    save_data()