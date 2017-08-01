#!/usr/bin/env python

import getopt
import logging
import os
import sys
import time
from datetime import date, timedelta, datetime
from logging.config import fileConfig
from urllib import request

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

__FINAM_URL = 'https://www.finam.ru/profile/moex-akcii/mosenrg/export/?market=1'
__MARKETS_CLICK = '//div[contains(@class, "finam-ui-quote-selector-market")]/div[1]'
__MARKETS_SELECTOR = '//div[contains(@class,"ui-dropdown-list")][1]/div/ul/li/a'
__INSTRUMENTS_CLICK = '//div[contains(@class, "finam-ui-quote-selector-quote")]/div[1]'
__INSTRUMENTS_SELECTOR = '//div[contains(@class,"ui-dropdown-list")][2]/div/ul/li/a'
__TICKER_SELECTOR = '//*[@id="issuer-profile-export-contract"]'
# __DOWNLOAD_LINK = 'http://export.finam.ru/YNDX_170512_170524.txt?
#                    market=1&em=388383&code=YNDX&apply=0&
#                    df=12&mf=4&yf=2017&from=12.05.2017
#                    &dt=24&mt=4&yt=2017&to=24.05.2017
#                    &p=1&f=YNDX_170512_170524&e=.txt&cn=YNDX
#                    &dtf=1&tmf=1&MSOR=1&mstime=on&mstimever=1&sep=1&sep2=1&datf=6&at=1'
__DOWNLOAD_LINK = 'http://export.finam.ru/%s_%s_%s.csv?' \
                  'market=%s&em=%s&code=%s&apply=0&' \
                  'df=%s&mf=%s&yf=%s&from=%s' \
                  '&dt=%s&mt=%s&yt=%s&to=%s' \
                  '&p=1&f=%s_%s_%s&e=.csv&cn=%s' \
                  '&dtf=1&tmf=1&MSOR=1&mstime=on&mstimever=1&sep=1&sep2=1&datf=6&at=1'
__MAX_TRY_FAILS = 10
__MAX_DATA_FAILS = 60
__NUM_DAYS = 30 * 365

__TIMEOUT = 3

__IGNORE_MARKETS = ['МосБиржа топ', 'ФОРТС Архив', 'Сырье Архив', 'RTS Standard Архив', 'ММВБ Архив',
                    'РТС Архив', 'СПФБ Архив', 'РТС-BOARD Архив', 'Расписки Архив', 'Отрасли', 'РТС-GAZ',
                    'Курс рубля']

__IGNORE_INSTRUMENTS = ['не выбрано']

fileConfig('logging_config.ini')
log = logging.getLogger()
driver = None


def get_topics(m_start, i_start, d_start):
    global driver
    log.debug('Start Selenium')
    driver = webdriver.Chrome()
    try:
        driver.get(__FINAM_URL)
        assert 'Финам.ru - Экспорт котировок' in driver.title
        log.debug('Looking for markets and instruments')
        m_info = market_info()
        total_markets = len(m_info)
        log.info('Total markets: ' + str(total_markets - m_start))
        for m in range(m_start, total_markets):
            market_select(m)
            info = instruments_info()
            total_instruments = len(info)
            instrument_select(i_start)
            market = market_name()
            m_code = m_info[m]
            log.info('Total instruments: %s for %s, index: %s' % (total_instruments - i_start, market, m))

            for i in range(i_start, total_instruments):
                i_code = info[i]
                instrument_select(i)
                instrument = instrument_name()
                ticker = instrument_ticker()
                log.info('Market %s -> instrument %s: %s by %s, index: %s' % (market, instrument, ticker, i_code, i))
                fails = 0
                for day in (d_start - timedelta(days=d) for d in range(0, __NUM_DAYS)):
                    data = load_url(instrument_link(m_code, (ticker, i_code), day, day))
                    if is_valid_data(data):
                        fails = 0
                        day_formatted = day.strftime('%Y-%m-%d')
                        log.info('Saving data for %s by %s, i: %d, m: %d' % (ticker, day_formatted, i, m))
                        folder = 'data/%s/%s' % (market, ticker)
                        if not os.path.exists(folder):
                            os.makedirs(folder)
                        filename = '%s/%s.csv' % (folder, day_formatted)
                        with open(filename, 'w') as f:
                            f.write(data)
                    else:
                        fails += 1

                    if fails >= __MAX_DATA_FAILS:
                        break

                d_start = date.today()

            i_start = 0

        input('Press Enter to close...\n')
    finally:
        log.debug('Close Selenium')
        driver.close()


def load_url(url, tries_left=__MAX_TRY_FAILS):
    data = ''
    success = False
    try:
        response = request.urlopen(url)
        data = response.read().decode('utf-8')
        success = True
    except (TimeoutError, ConnectionRefusedError):
        pass
    if success:
        return data
    else:
        if tries_left > 0:
            time.sleep(3)
            return load_url(url, --tries_left)
        else:
            log.error('Can\'t load url: %s' % url)
            return ''


def instrument_link(m_code, instrument, date_from, date_to):
    (ticker, i_code) = instrument
    day_from = date_from.day
    month_from = date_from.month - 1
    year_from = date_from.year
    str_from_dot = date_from.strftime('%d.%m.%Y')
    str_from = date_from.strftime('%y%m%d')
    day_to = date_to.day
    month_to = date_to.month - 1
    year_to = date_to.year
    str_to_dot = date_to.strftime('%d.%m.%Y')
    str_to = date_from.strftime('%y%m%d')
    return __DOWNLOAD_LINK % (ticker, str_from_dot, str_to_dot,
                              m_code, i_code, ticker,
                              day_from, month_from, year_from, str_from_dot,
                              day_to, month_to, year_to, str_to_dot,
                              ticker, str_from, str_to, ticker)


def instruments():
    driver.find_element(By.XPATH, __INSTRUMENTS_CLICK).click()
    return [elem for elem in driver.find_elements(By.XPATH, __INSTRUMENTS_SELECTOR)
            if elem.text not in __IGNORE_INSTRUMENTS]


def instruments_info():
    info = [i.get_attribute('value') for i in instruments()]
    driver.find_element(By.XPATH, __INSTRUMENTS_CLICK).click()
    return info


def instrument_select(index):
    i = instruments()[index]
    driver.execute_script('arguments[0].click()', i)


def markets():
    WebDriverWait(driver, __TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, __MARKETS_CLICK))
    ).click()
    return [elem for elem in driver.find_elements(By.XPATH, __MARKETS_SELECTOR)
            if elem.text not in __IGNORE_MARKETS]


def market_info():
    info = [i.get_attribute('value') for i in markets()]
    driver.find_element(By.XPATH, __MARKETS_CLICK).click()
    return info


def market_name():
    url = driver.current_url
    p = url.find('profile/') + 8
    ps = url[p:].find('/') + p
    return url[p:ps]


def instrument_name():
    url = driver.current_url
    p = url.find('/export/')
    return url[:p].split('/')[-1]


def instrument_ticker():
    t = driver.find_element(By.XPATH, __TICKER_SELECTOR)
    return t.get_attribute('value')


def market_select(index):
    m = markets()[index]
    driver.execute_script('arguments[0].click()', m)


def is_valid_data(data):
    i = data.find('\n')
    return i > 0 and data[i + 1:].find('\n') > 0


if __name__ == '__main__':
    argv = sys.argv[1:]
    market_from = 0
    instr_from = 0
    date_from = date.today()
    usage = 'test.py -m <market_from> -i <instr_from> -d <from_date, YYYY-mm-dd>'
    try:
        opts, args = getopt.getopt(argv, 'hm:i:d:', ['market=', 'instr=', 'from-date'])
    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    try:
        for opt, arg in opts:
            if opt == '-h':
                print(usage)
                sys.exit()
            elif opt in ('-m', '--market'):
                market_from = int(arg)
            elif opt in ('-i', '--instr'):
                instr_from = int(arg)
            elif opt in ('-d', '--from-date'):
                date_from = datetime.strptime(arg, '%Y-%m-%d').date()
    except ValueError as e:
        print(e)
        print(usage)
        sys.exit(1)
    log.debug('Load markets from index: %d' % market_from)
    log.debug('Load instruments from index: %d' % instr_from)
    log.debug('Load data from: %s' % date_from.strftime('%Y-%m-%d'))
    get_topics(market_from, instr_from, date_from)
