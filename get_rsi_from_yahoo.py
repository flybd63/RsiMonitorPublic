import yfinance as yf
import json
import datetime
import os
import numpy as np
import sys

def load_mst():
    with open("tickers.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_result(date):
    result_file = f"./result/{date}.json"
    if os.path.exists(result_file):
        with open(result_file, "r", encoding="utf-8") as f:
            return json.load(f).get("result", {})
    return {}

def save_json(ticker, data):
    output_path = f"./result/{ticker}.json"
    tmpfile = output_path + "tmp"
    with open(tmpfile, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.rename(tmpfile, output_path)

def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="6mo", interval="1d")
        prices = hist["Close"].dropna().tolist()
        last_end_date = hist.index[-1].strftime("%Y-%m-%dT%H:%M:%S") if len(hist) > 0 else "0"
        return last_end_date, prices
    except Exception as e:
        sys.stderr.write(f"ERROR: {symbol} - {e}\n")
        return "0", []

def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return None
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def main(mode="P"):
    today = datetime.datetime.utcnow().strftime('%Y%m%d')
    tickers = load_mst()
    result = load_result(today)
    
    for count, (ticker, info) in enumerate(tickers.items(), 1):
        if mode == "P" and "プライム" in info["class"]:
            pass
        elif mode == "S" and "スタンダード" in info["class"]:
            pass
        elif mode == "G" and "グロース" in info["class"]:
            pass
        else:
            continue  
        sys.stderr.write(f"{count}/{len(tickers)} t:{ticker} {info['name']} {info['class']}\n")
        #print(f"{count}/{len(tickers)} t:{ticker} {info['name']} {info['class']}")
        symbol = f"{ticker}.T"
        last_end_date, prices = get_stock_data(symbol)
        if len(prices) < 14:
            sys.stderr.write(f"  - prices too short for RSI calculation: {symbol}\n")
            #print("  - prices is short. Skipping.")
            continue
        rsi = calculate_rsi(prices)
        result[ticker] = {"rsi": rsi, "price": prices[-1], "end_date": last_end_date}
    
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    output = {"date_modified": now, "result": result}
    sys.stdout.write(json.dumps(output, indent=4, ensure_ascii=False) + "\n")
    #print(json.dumps(output, indent=4, ensure_ascii=False))
    #save_json("latest", output)

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "P"
    main(mode)
