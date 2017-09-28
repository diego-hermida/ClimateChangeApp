from ftplib import FTP

URL = 'podaac.jpl.nasa.gov'
FILE = 'sea_level_rise.txt'
DIR = '/allData/merged_alt/L2/TP_J1_OSTM/global_mean_sea_level/'

def save_data():

    # Connecting to FTP server
    ftp = FTP(URL)

    # Login to FTP server
    ftp.login()

    # Accessing directory
    ftp.cwd(DIR)

    # Retrieving requested filename
    l = [x for x in ftp.nlst() if x.startswith('GMSL') and x.endswith('.txt')]

    # Downloading content to file
    with open(FILE, 'wb') as f:
        ftp.retrbinary('RETR ' + l[0], f.write)

    # Disconnecting from FTP server
    ftp.quit()


if __name__ == '__main__' :
    save_data()