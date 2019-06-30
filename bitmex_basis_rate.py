import collections
import datetime
import json
import urllib.request
import sys

SATOSHIS_PER_BITCOIN = 10**8
INDEX_SYMBOL = '.BXBT'
CONTRACT_EXPIRATION_MONTH = {
  'XBTH': 3,
  'XBTM': 6,
  'XBTU': 9,
  'XBTZ': 12,
}
EXPIRATION_DAY_OF_MONTH = 27


def GetDate(str_datetime):
  """Convert the string formatted date to a date object

  Expects format 2019-06-18T00:00:00.000Z
  """
  str_date = str_datetime[:str_datetime.find('T')]
  dt = datetime.datetime.strptime(str_datetime[:str_datetime.find('T')],
                                  '%Y-%m-%d')
  return dt.date()


def GetBTCDailyPrices(symbol, start_date, end_date):
  """Daily price is the closing price of the Bitmex .BXBT index.

  """
  start_str = start_date.isoformat()
  end_str = end_date.isoformat()
  url = ('https://www.bitmex.com/api/v1/trade/bucketed?binSize=1d&partial=false'
         '&symbol=%s&count=500&reverse=false&'
         'startTime=%s&endTime=%s') % (symbol, start_str, end_str)
  prices = {}
  with urllib.request.urlopen(url) as conn:
    for daily in json.loads(conn.read()):
      prices[GetDate(daily['timestamp'])] = daily['close']
  return prices


def GetDailyBasis(expiration_date, daily_prices, daily_index_prices):
  daily_basis = {}
  for day, price in daily_prices.items():
    expiry = expiration_date - day
    if expiry.days == 0:
      continue
    try:
      daily_basis[day] = (
          (price / daily_index_prices[day] - 1) / (expiry.days / 365)
      )
    except KeyError:
      # No price for the given day
      continue

  return daily_basis

def GetContractExpirations(start_date, end_date):
  # Get the futures and expirations we are interested in.
  years= list(range(start_date.year, end_date.year)) + [end_date.year]
  years_suffix = [year - 2000 for year in years]
  contract_expirations = {}
  for year in years_suffix:
    for future, month in CONTRACT_EXPIRATION_MONTH.items():
      contract_expirations[future + str(year)] = (
          datetime.date(month=month, day=EXPIRATION_DAY_OF_MONTH,
                        year=2000 + int(year)))
  return contract_expirations

def GetPrices(contracts, start_date, end_date):
  # Get the index prices and all futures prices
  index_prices = GetBTCDailyPrices(INDEX_SYMBOL, start_date, end_date)
  futures_prices = {}
  for contract in contracts.keys():
    futures_prices[contract] = GetBTCDailyPrices(contract, start_date, end_date)
  return index_prices, futures_prices

def GetBasisRates(contract_expirations, futures_prices, index_prices):
  # Get the daily basis for each future
  futures_basis = {}
  for contract, prices in futures_prices.items():
    futures_basis[contract] = GetDailyBasis(
        contract_expirations[contract], prices, index_prices)
  return futures_basis


if __name__ == '__main__':
  num_days = 10
  end_date = datetime.date.today() - datetime.timedelta(days=1)
  start_date = end_date - datetime.timedelta(days=num_days)
  contract_expirations = GetContractExpirations(start_date, end_date)
  index_prices, futures_prices = GetPrices(contract_expirations, start_date, end_date)
  futures_basis = GetBasisRates(contract_expirations, futures_prices, index_prices)
  for contract, basis in futures_basis.items():
    print(contract)
    print(basis)
    print(futures_prices[contract])
