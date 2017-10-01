from ftplib import FTP

from util.util import get_config

config = get_config(__file__)


def get_data():
    ftp = FTP(config['URL'])
    ftp.login()
    ftp.cwd(config['DIR'])  # Accessing directory

    file_names = [x for x in ftp.nlst() if x.startswith('GMSL') and x.endswith('.txt')]

    data = {};
    temp = []
    ftp.retrbinary('RETR ' + file_names[0], temp.append)
    data[config['FILE']] = temp[0]
    ftp.quit()
    return data


if __name__ == '__main__':
    data = get_data()
    print(data)
