import configparser
from telethon import TelegramClient, events
import bina
import re

configParser = configparser.RawConfigParser()   
configFilePath = r'config.txt'
configParser.read(configFilePath)

TELE_API_ID = configParser.get('tele', 'ApiId')
TELE_API_HASH = configParser.get('tele', 'ApiHash')
ASSET_RATIO = float(configParser.get('main', 'AssetRatio'))
LEVERAGE = float(configParser.get('main', 'Leverage'))
CHANNEL_NAMES = configParser.get('main', 'ChannelName').strip().split(',')
IGNORE_WORDS = configParser.get('main', 'IgnoreWords').strip().split(',')
SYMBOL_MAP = dict(configParser.items('mapsym'))

print('TELE_API_ID', TELE_API_ID)
print('TELE_API_HASH', TELE_API_HASH)
print('ASSET_RATIO', ASSET_RATIO)
print('LEVERAGE', LEVERAGE)
print('CHANNEL_NAME', CHANNEL_NAMES)
print('SYMBOL_MAP', SYMBOL_MAP)

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

plusPercentRegex = re.compile(r'\+([0-9]\.)\w+%')
def ignoreMsg(msg):
  if min_pos(msg, IGNORE_WORDS) is not None:
    return True

  if plusPercentRegex.search(msg) is not None:
    return True

  return False

def get_symbol(msg):
  if ignoreMsg(msg):
    print('This message should be ignored')
    return None

  kw = min_pos(msg, ['buy', 'scalp'])
  if kw is None:
    return None

  symbol = get_symbol_sign(msg)
  if symbol is not None:
    return map_symbol(symbol)
  
  sn = msg[0:kw]
  symbol = re.sub('[^A-Za-z0-9]+', '', sn)
  return map_symbol(symbol)

@client.on(events.NewMessage)
async def my_event_handler(event):
  chat = await event.get_chat()
  sender = await event.get_sender()
  chat_id = event.chat_id
  sender_id = event.sender_id
  
  chatType = type(chat).__name__
  if chatType != 'Channel':
    return

  print('New message from channel "', chat.title, '" ...')
  wlChannel = False
  for chName in CHANNEL_NAMES:
    if chName in chat.title:
      wlChannel = True
      break
  if not wlChannel: 
    return

  msg = event.raw_text
  print('---- Content Start ----')
  print(msg)
  print('---- Content End ----')

  msg = msg.upper()

  symbol = get_symbol(msg)
  if symbol is None:
    print('Not found symbol or message is ignored')
    return

  print('=======> Buy ' + symbol)
  balance = bina.getUSDTBalance()
  budget = balance * ASSET_RATIO / 100 * LEVERAGE
  print('Balance ', str(balance), ' -> buy ', str(budget), ' USDT')

  symbol = symbol + 'USDT'
  bina.placeOrder(symbol, budget)

client.start()
client.run_until_disconnected()

