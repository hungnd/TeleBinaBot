import configparser
from telethon import TelegramClient, events
import cv2
import pytesseract
import time
import pathlib
import bina
import re
import logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

configParser = configparser.RawConfigParser()   
configFilePath = r'config.txt'
configParser.read(configFilePath)

TELE_API_ID = configParser.get('tele', 'ApiId')
TELE_API_HASH = configParser.get('tele', 'ApiHash')
TESSERACT_PATH = configParser.get('tera', 'Path')
ASSET_RATIO = float(configParser.get('main', 'AssetRatio'))
LEVERAGE = float(configParser.get('main', 'Leverage'))
CHANNEL_NAMES = configParser.get('main', 'ChannelName').strip().split(',')
IGNORE_WORDS = configParser.get('main', 'IgnoreWords').strip().split(',')
BUY_WORDS = configParser.get('main', 'BuyWords').strip().split(',')
SYMBOL_MAP = dict(configParser.items('mapsym'))
SYMBOL_LIST = list(SYMBOL_MAP.keys())
SYMBOL_LIST.extend(list(bina.get_symbol_list()))

logging.info('TELE_API_ID %s', TELE_API_ID)
logging.info('TELE_API_HASH %s', TELE_API_HASH)
logging.info('TESSERACT_PATH %s', TESSERACT_PATH)
logging.info('ASSET_RATIO %s', ASSET_RATIO)
logging.info('LEVERAGE %s', LEVERAGE)
logging.info('CHANNEL_NAME %s', CHANNEL_NAMES)
logging.info('BUY_WORDS %s', BUY_WORDS)
logging.info('SYMBOL_MAP %s', SYMBOL_MAP)
logging.info('SYMBOL_LIST %s', SYMBOL_LIST)

if TESSERACT_PATH:
  pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

client = TelegramClient(str(TELE_API_ID), TELE_API_ID, TELE_API_HASH)

def find_pos(haystack, needle):
  match = re.search(needle, haystack, re.IGNORECASE)
  if match is None:
    return None
  return match.span()[0]

def min_pos(haystack, needles):
  m = None
  for nd in needles:
    p = find_pos(haystack, nd)
    if p is not None and (m is None or m > p):
      m = p
  return m

def map_symbol(sym):
  for var in SYMBOL_MAP:
    if var.casefold() == sym.casefold():
      return SYMBOL_MAP.get(var)
  return sym

symbolRegex = re.compile(r'[#,$]\w+')
def get_symbol_sign(msg):  
  comp = symbolRegex.search(msg)
  if comp is None: 
    return None    
  symbol = comp.group()
  return symbol[1:]

plusPercentRegex = re.compile(r'\+([0-9\.])*%')
def ignoreMsg(msg):
  if min_pos(msg, IGNORE_WORDS) is not None:
    return True

  if plusPercentRegex.search(msg) is not None:
    return True

  return False

def get_symbol(msg):
  if ignoreMsg(msg):
    logging.warning('This message should be ignored')
    return None

  kw = min_pos(msg, BUY_WORDS)
  if kw is None:
    return None

  # symbol = get_symbol_sign(msg)
  # if symbol is not None:
  #   return map_symbol(symbol)
  
  sn = msg[0:min(kw+12,len(msg))]
  for bword in BUY_WORDS:
    sn = re.sub(r"(" + bword + "*)\w+", '', sn, flags=re.IGNORECASE)

  cleanDesc = re.sub('[^A-Za-z0-9]+', '', sn)
  
  for symbol in SYMBOL_LIST: 
    if re.search(symbol, cleanDesc, re.IGNORECASE):
      return map_symbol(symbol)

  logging.error('Cannot find symbol')
  return None

def findWholeWord(w):
  return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search

def get_symbol_image(text):
  for symbol in SYMBOL_LIST:     
    if re.search(symbol + 'USD', text, re.IGNORECASE) or findWholeWord(symbol)(text):
      return map_symbol(symbol)
  return None

def crop_image(img):
  height, width, _ = img.shape
  hc = 50
  wc = int(width / 2)
  img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

  crop_img = img_gray[0:0+hc, 0:0+wc]
  cv2.imwrite('tmp/1.jpg', crop_img)
  cv2.imshow('image', crop_img)
  text = pytesseract.image_to_string(crop_img)
  logging.info('Read text from img: %s', text)
  print(text)
  symbol = get_symbol_image(text)
  if symbol:
    return symbol

  crop_img = img_gray[height-hc:height, 0:0+wc]
  cv2.imwrite('tmp/2.jpg', crop_img)
  text = pytesseract.image_to_string(crop_img)
  logging.info('Read text from img: %s', text)
  symbol = get_symbol_image(text)
  if symbol:
    return symbol

  return None
  

async def extract_symbol(event):
  if event.photo:
    filePath = r'tmp/' + str(time.time()) + '.jpg'
    await event.download_media(filePath)
    img = cv2.imread(filePath)
    pathlib.Path(filePath).unlink(missing_ok = True)
    return crop_image(img)

  msg = event.raw_text
  logging.info('---- Content Start ---- \n %s \n ---- Content End ----', msg)
  msg = msg.upper()
  return get_symbol(msg)

@client.on(events.NewMessage)
async def my_event_handler(event):
  chat = await event.get_chat() 
  sender = await event.get_sender()
  chat_id = event.chat_id
  sender_id = event.sender_id
  
  chatType = type(chat).__name__ 
  if chatType != 'Channel':
    return

  logging.info('New message from channel "%s" ...', chat.title)
  wlChannel = False
  for chName in CHANNEL_NAMES:
    if chName in chat.title:
      wlChannel = True
      break
  if not wlChannel: 
    return

  symbol = await extract_symbol(event)
  if symbol is None:
    logging.error('Not found symbol or message is ignored')
    return

  logging.info('=======> Buy %s', symbol)
  balance = bina.getUSDTBalance()
  budget = balance * ASSET_RATIO / 100 * LEVERAGE
  logging.info('Balance %s -> buy %s USDT', str(balance), str(budget))

  symbol = symbol + 'USDT'
  bina.placeOrder(symbol, budget)

client.start()
client.run_until_disconnected()