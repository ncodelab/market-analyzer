from io import BytesIO
from urllib import request
from zipfile import ZipFile, BadZipFile


def download_zip_archive(year, month, day):
    """
    :param int year: full year
    :param int month: month as 2 digit string
    :param int day: day as 2 digit string
    :return:
    """
    y = 'YYYY'
    m = 'MM'
    d = 'DD'
    url_template = 'http://www.moex.com/iss/downloads/engines/stock/markets/shares/years/' \
                   '%s/months/%s/days/%s/trades_micex_stock_shares_%s_%s_%s.csv.zip' % (y, m, d, y, m, d)
    url = url_template.replace(y, '%04d' % year).replace(m, '%02d' % month).replace(d, '%02d' % day)
    print(url)
    response = request.urlopen(url)
    try:
        data = BytesIO(response.read())
        archive = ZipFile(data)
        return [archive.read(name) for name in archive.namelist()]
    except BadZipFile:
        return []


if __name__ == '__main__':
    print(download_zip_archive(2017, 5, 22))
