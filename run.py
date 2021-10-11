import configparser
from telethon import TelegramClient, events
import bina
import re

configParser = configparser.RawConfigParser()   
configFilePath = r'config.txt'
configParser.read(configFilePath)

symbolRegex = re.compile(r'[#,$]\w+')
def get_symbol(msg):  
  comp = symbolRegex.search(msg)
  if comp is None: 
    return None    
  symbol = comp.group()
  return symbol[1:]

def is_buy(msg):
  return 'BUY' in msg

TELE_API_ID = configParser.get('tele', 'ApiId')
TELE_API_HASH = configParser.get('tele', 'ApiHash')
ASSET_RATIO = float(configParser.get('main', 'AssetRatio'))
LEVERAGE = float(configParser.get('main', 'Leverage'))
CHANNEL_NAME = configParser.get('main', 'ChannelName')

print('TELE_API_ID', TELE_API_ID)
print('TELE_API_HASH', TELE_API_HASH)
print('ASSET_RATIO', ASSET_RATIO)
print('LEVERAGE', LEVERAGE)
print('CHANNEL_NAME', CHANNEL_NAME)

client = TelegramClient(str(TELE_API_ID), TELE_API_ID, TELE_API_HASH)

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
  if CHANNEL_NAME not in chat.title:
    return 

  msg = event.raw_text
  print('---- Content Start ----')
  print(msg)
  print('---- Content End ----')

  msg = msg.upper()

  symbol = get_symbol(msg)
  if symbol is None or not is_buy(msg):
    print('Not found symbol or BUY word')
    return

  print('=======> Buy ' + symbol)
  balance = bina.getUSDTBalance()
  budget = balance * ASSET_RATIO / 100 * LEVERAGE
  print('Balance ', str(balance), ' -> buy ', str(budget), ' USDT')

  symbol = symbol + 'USDT'
  bina.placeOrder(symbol, budget)

client.start()
client.run_until_disconnected()
