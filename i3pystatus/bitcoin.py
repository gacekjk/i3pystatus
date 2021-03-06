import urllib.request
import json
import time

from i3pystatus import IntervalModule
from i3pystatus.core.util import internet, require, user_open


class Bitcoin(IntervalModule):

    """
    This module fetches and displays current Bitcoin market prices and
    optionally monitors transactions to and from a list of user-specified
    wallet addresses. Market data is pulled from the BitcoinAverage Price
    Index API <https://bitcoinaverage.com> while transaction data is pulled
    from blockchain.info <https://blockchain.info/api/blockchain_api>.

    .. rubric:: Available formatters

    * {last_price}
    * {ask_price}
    * {bid_price}
    * {daily_average}
    * {volume}
    * {status}
    * {last_tx_type}
    * {last_tx_addr}
    * {last_tx_value}
    * {balance_btc}
    * {balance_fiat}
    * {symbol}

    """

    settings = (
        ("format", "Format string used for output."),
        ("currency", "Base fiat currency used for pricing."),
        ("wallet_addresses", "List of wallet address(es) to monitor."),
        ("color", "Standard color"),
        ("colorize", "Enable color change on price increase/decrease"),
        ("color_up", "Color for price increases"),
        ("color_down", "Color for price decreases"),
        ("leftclick", "URL to visit or command to run on left click"),
        ("rightclick", "URL to visit or command to run on right click"),
        ("interval", "Update interval."),
        ("symbol", "Symbol for bitcoin sign"),
        "status"
    )
    format = "{symbol} {status}{last_price}"
    currency = "USD"
    symbol = "฿"
    wallet_addresses = ""
    color = "#FFFFFF"
    colorize = False
    color_up = "#00FF00"
    color_down = "#FF0000"
    leftclick = "electrum"
    rightclick = "https://bitcoinaverage.com/"
    interval = 600
    status = {
        "price_up": "▲",
        "price_down": "▼",
    }

    on_leftclick = "handle_leftclick"
    on_rightclick = "handle_rightclick"

    _price_prev = 0

    def _fetch_price_data(self):
        api = "https://api.bitcoinaverage.com/ticker/global/"
        url = "{}{}".format(api, self.currency.upper())
        return json.loads(urllib.request.urlopen(url).read().decode("utf-8"))

    def _fetch_blockchain_data(self):
        api = "https://blockchain.info/multiaddr?active="
        addresses = "|".join(self.wallet_addresses)
        url = "{}{}".format(api, addresses)
        return json.loads(urllib.request.urlopen(url).read().decode("utf-8"))

    @require(internet)
    def run(self):
        price_data = self._fetch_price_data()
        fdict = {
            "symbol": self.symbol,
            "daily_average": price_data["24h_avg"],
            "ask_price": price_data["ask"],
            "bid_price": price_data["bid"],
            "last_price": price_data["last"],
            "volume": price_data["volume_btc"],
        }

        if self._price_prev and fdict["last_price"] > self._price_prev:
            color = self.color_up
            fdict["status"] = self.status["price_up"]
        elif self._price_prev and fdict["last_price"] < self._price_prev:
            color = self.color_down
            fdict["status"] = self.status["price_down"]
        else:
            color = self.color
            fdict["status"] = ""
        self._price_prev = fdict["last_price"]

        if not self.colorize:
            color = self.color

        if self.wallet_addresses:
            blockchain_data = self._fetch_blockchain_data()
            wallet_data = blockchain_data["wallet"]
            balance_btc = wallet_data["final_balance"] / 100000000
            fdict["balance_btc"] = round(balance_btc, 2)
            balance_fiat = fdict["balance_btc"] * fdict["last_price"]
            fdict["balance_fiat"] = round(balance_fiat, 2)
            fdict["total_sent"] = wallet_data["total_sent"]
            fdict["total_received"] = wallet_data["total_received"]
            fdict["transactions"] = wallet_data["n_tx"]

            if fdict["transactions"]:
                last_tx = blockchain_data["txs"][0]
                fdict["last_tx_addr"] = last_tx["out"][0]["addr"]
                fdict["last_tx_value"] = last_tx["out"][0]["value"] / 100000000
                if fdict["last_tx_addr"] in self.wallet_addresses:
                    fdict["last_tx_type"] = "recv"
                else:
                    fdict["last_tx_type"] = "sent"

        self.output = {
            "full_text": self.format.format(**fdict),
            "color": color,
        }

    def handle_leftclick(self):
        user_open(self.leftclick)

    def handle_rightclick(self):
        user_open(self.rightclick)
