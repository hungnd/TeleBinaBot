import configparser
from urllib.parse import urlencode
import urllib3

import requests
import time
import json
import hmac
import hashlib
import math

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

configParser = configparser.RawConfigParser()   
configFilePath = r'config.txt'
configParser.read(configFilePath)

assetApi = 'https://api.binance.com/api/v3/account'
orderApi = 'https://api.binance.com/api/v3/order/test'
exchangeApi = 'https://api.binance.com/api/v3/exchangeInfo'
priceApi = 'https://api.binance.com/api/v3/ticker/price'

BINA_API_KEY = configParser.get('binance', 'ApiKey')
BINA_SECRET_KEY = configParser.get('binance', 'ApiSecret')
print('BINA_API_KEY', BINA_API_KEY)
print('BINA_SECRET_KEY', BINA_SECRET_KEY)

precision = {}
minNotion = {}

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

  response = requests.post(url, headers=headers, verify=False)
  print(response.json())

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
  response = requests.get(url, headers=headers, verify=False)
  return response.json()

def httpReqGetAuthless(url, data):
  query = urlencode(data)
  url = url + '?' + query
  # print('url = ' + url)

  headers = {
    'Content-Type': 'application/json',
  }
  response = requests.get(url, headers=headers, verify=False)
  return response.json()

def getUSDTBalance(): 
  assets = httpReqGet(assetApi, {})
  usd = 0
  # print('Future balance:')
  for e in assets.get('balances'):
    # print(e.get('asset') + ': ' + e.get('balance'))
    if e.get('asset') == 'USDT':
      usd = e.get('free')
  return float(usd)

def placeOrder(symbol, value):
  preci = precision.get(symbol)
  if preci is None: 
    print('Cannot find precision info of', symbol)
    return

  if minNotion.get(symbol) > value:
    print('Not enough money', value, 'for minimum order value', minNotion.get(symbol))
    return

  price = getPrice(symbol)
  quantity = value / price
  quantity = "{:0.0{}f}".format(quantity , preci)
  print('Price ', symbol, price, 'quantity', quantity)
  order = {
    'symbol': symbol,
    'side': 'BUY',
    'type': 'MARKET',
    'quantity': quantity,
  }
  print('Order info: ', order)
  httpReqPost(orderApi, order)
  
def getLotSize(filters):
  for cre in filters:
    if cre.get('filterType') == 'LOT_SIZE':
      x = float(cre.get('stepSize'))
      return int(math.log10(1/x))
  return None

def getMinNotion(filters):
  for cre in filters:
    if cre.get('filterType') == 'MIN_NOTIONAL':
      x = float(cre.get('minNotional'))
      return x
  return None

def loadPrecision():
  exins = httpReqGetAuthless(exchangeApi, {})
  # print(exins)
  for e in exins.get('symbols'):
    precision[e.get('symbol')] = getLotSize(e.get('filters')) 
    minNotion[e.get('symbol')] = getMinNotion(e.get('filters')) 

def getPrice(symbol):
  data = httpReqGetAuthless(priceApi, {'symbol': symbol})
  return float(data.get('price'))

loadPrecision()
# placeOrder('ETHUSDT', 10)