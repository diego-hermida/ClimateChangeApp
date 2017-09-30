from ftplib import FTP

URL = 'podaac.jpl.nasa.gov'
FILE = 'sea_level_rise.txt'
DIR = '/allData/merged_alt/L2/TP_J1_OSTM/global_mean_sea_level/'


def get_data():
    ftp = FTP(URL)
    ftp.login()
    ftp.cwd(DIR)  # Accessing directory

    file_names = [x for x in ftp.nlst() if x.startswith('GMSL') and x.endswith('.txt')]

    data = {};
    temp = []
    ftp.retrbinary('RETR ' + file_names[0], temp.append)
    data[FILE] = temp[0]
    ftp.quit()
    return data


if __name__ == '__main__':
    data = get_data()
