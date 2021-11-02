import configparser
from urllib.parse import urlencode
import urllib3

import requests
import time
import json
import hmac
import hashlib
import threading
import logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

configParser = configparser.RawConfigParser()   
configFilePath = r'config.txt'
configParser.read(configFilePath)

assetApi = 'https://fapi.binance.com/fapi/v2/balance'
orderApi = 'https://fapi.binance.com/fapi/v1/order'
exchangeApi = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
priceApi = 'https://fapi.binance.com/fapi/v1/ticker/price'

BINA_API_KEY = configParser.get('binance', 'ApiKey')
BINA_SECRET_KEY = configParser.get('binance', 'ApiSecret')
logging.info('BINA_API_KEY %s', BINA_API_KEY)
logging.info('BINA_SECRET_KEY %s', BINA_SECRET_KEY)

precision = {}
maxQtty = {}
walletBalance = 0

def current_milli_time():
  return round(time.time() * 1000)

def httpReqPost(url, body):
  body['timestamp'] = current_milli_time()
  query = urlencode(body)
  signature = hmac.new(bytes(BINA_SECRET_KEY , 'latin-1'), msg = bytes(query , 'latin-1'), digestmod = hashlib.sha256).hexdigest().upper()
  url = url + '?' + query + '&signature=' + signature
  # print('url = ' + url)

  headers = {
    'Content-Type': 'application/json',
    'X-MBX-APIKEY': BINA_API_KEY
  }

  logging.info('request: %s', url)
  response = requests.post(url, headers=headers, verify=False)
  logging.info('response: %s', response.json())

def httpReqGet(url, data):
  data['timestamp'] = current_milli_time()
  query = urlencode(data)
  signature = hmac.new(bytes(BINA_SECRET_KEY , 'latin-1'), msg = bytes(query , 'latin-1'), digestmod = hashlib.sha256).hexdigest().upper()
  
  url = url + '?' + query + '&signature=' + signature
  # print('url = ' + url)

  headers = {
    'Content-Type': 'application/json',
    'X-MBX-APIKEY': BINA_API_KEY
  }
  logging.info('request: %s', url)
  response = requests.get(url, headers=headers, verify=False)
  logging.info('response: %s', response)
  return response.json()

def getUSDTBalance(): 
  global walletBalance
  if walletBalance > 0:
    return walletBalance
  walletBalance = queryUSDTBalance()
  return walletBalance

def queryUSDTBalance(): 
  assets = httpReqGet(assetApi, {})
  usd = 0
  for e in assets:
    # print(e.get('asset') + ': ' + e.get('balance'))
    if e.get('asset') == 'USDT':
      usd = e.get('balance')
  logging.info("Your current balance: %s USDT", walletBalance)
  return float(usd)

def placeOrder(symbol, value):
  preci = precision.get(symbol)
  if preci is None: 
    logging.warning('Cannot find precision info of %s', symbol)
    return

  price = getPrice(symbol)
  quantity = min(maxQtty[symbol], value / price)
  logging.info('Price %s = %s, quantity = %s', symbol, price, quantity)
  order = {
    'symbol': symbol,
    'side': 'BUY',
    # 'positionSide': 'LONG',
    'type': 'MARKET',
    'quantity': "{:0.0{}f}".format(quantity , preci),
  }
  logging.info('Order info: %s', order)
  httpReqPost(orderApi, order)
  queryUSDTBalance()
  
def loadPrecision():
  exins = httpReqGet(exchangeApi, {})
  for e in exins.get('symbols'):
    precision[e.get('symbol')] = e.get('quantityPrecision')
    maxQtty[e.get('symbol')] = int(filter(e.get('filters'), 'MARKET_LOT_SIZE', 'maxQty'))

def filter(data, key, value):
  for f in data:
    if f.get('filterType') == key:
      return f.get(value)
  return None

def getPrice(symbol):
  data = httpReqGet(priceApi, {'symbol': symbol})
  return float(data.get('price'))

def get_symbol_list():
  newlist = list()
  for sym in precision.keys(): 
    if '_' in sym or sym[-4:] != 'USDT': 
      continue
    newlist.append(sym[:-4])
  return newlist

loadPrecision()

interval = 60

def intervalQueryBalance():
  global walletBalance
  walletBalance = queryUSDTBalance()  

def startTimer():
  t = threading.Timer(interval, startTimer)
  t.daemon = True
  t.start()
  intervalQueryBalance()

startTimer()