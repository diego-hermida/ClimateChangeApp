from ftplib import FTP

from util.util import get_config

config = get_config(__file__)


def get_data():
    ftp = FTP(config['URL'])
    ftp.login()
    ftp.cwd(config['DIR'])  # Accessing directory

    file_names = [x for x in ftp.nlst() if x.endswith('.txt')]

    data = {}
    for (index, filename) in enumerate(config['FILES']):
        temp = []
        ftp.retrbinary('RETR ' + file_names[index], temp.append)
        data[config['FILES'][index]] = temp[0]
    ftp.quit()
    return data


if __name__ == '__main__':
    data = get_data()