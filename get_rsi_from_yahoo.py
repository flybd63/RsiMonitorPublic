import yfinance as yf
import json
import datetime
import os
import numpy as np
import sys

def load_mst():
    # ファイルがない場合のエラーハンドリングを追加
    if not os.path.exists("tickers.json"):
        sys.stderr.write("ERROR: tickers.json not found.\n")
        return {}
    with open("tickers.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_result(date):
    result_file = f"./result/{date}.json"
    if os.path.exists(result_file):
        with open(result_file, "r", encoding="utf-8") as f:
            return json.load(f).get("result", {})
    return {}

def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        # 6ヶ月分取得
        hist = stock.history(period="6mo", interval="1d")
        
        # データがない、または少なすぎる場合のチェック
        if hist.empty:
             return "0", [], []

        # NaNを含む行を削除
        clean_hist = hist[["Close"]].dropna()
        
        prices = clean_hist["Close"].tolist()
        
        # index(Timestamp)を文字列(YYYY-MM-DD)のリストに変換
        dates = [d.strftime('%Y-%m-%d') for d in clean_hist.index]
        
        last_end_date = clean_hist.index[-1].strftime("%Y-%m-%dT%H:%M:%S") if len(clean_hist) > 0 else "0"
        
        return last_end_date, prices, dates
    except Exception as e:
        sys.stderr.write(f"ERROR: {symbol} - {e}\n")
        return "0", [], []

def calculate_rsi_history(prices, dates, period=14):
    """
    価格リストと日付リストから、日々のRSI履歴を計算して返す
    Returns: (最新のRSI, 履歴データのリスト)
    """
    if len(prices) < period:
        return None, []
    
    # numpy配列に変換（計算高速化のため）
    np_prices = np.array(prices)
    deltas = np.diff(np_prices)
    
    history = []
    
    # 期間(14日)以降のデータについて、1日ずつずらしながらRSIを計算
    # i は「その日の価格」のインデックス
    for i in range(period, len(prices)):
        # i番目の日のRSIを計算するために、直近14日分の変動(delta)を取得
        # deltaのインデックスは priceより1つずれるため、i-period から i まで
        subset_deltas = deltas[i-period : i]
        
        gains = np.where(subset_deltas > 0, subset_deltas, 0)
        losses = np.where(subset_deltas < 0, -subset_deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        
        # JSONシリアライズ用にPythonのfloat型に変換して追加
        history.append({
            "d": dates[i],# date
            "p": round(float(prices[i]), 1), # price
            "r": round(float(rsi), 1) # rsi
        })

    # 最新のRSI（リスト表示用）
    current_rsi = history[-1]['r'] if history else None
    
    return current_rsi, history

def main(mode="P"):
    today = datetime.datetime.utcnow().strftime('%Y%m%d')
    tickers = load_mst()
    result = load_result(today)
    
    # グラフ用データが増えるため、JSONサイズが大きくなります。
    # 必要に応じてhistoryの長さを制限（例: history[-60:]）してください。
    
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
        
        symbol = f"{ticker}.T"
        last_end_date, prices, dates = get_stock_data(symbol)
        
        if len(prices) < 14:
            sys.stderr.write(f"  - prices too short for RSI calculation: {symbol}\n")
            continue
            
        # 履歴データを含めてRSIを計算
        current_rsi, history_data = calculate_rsi_history(prices, dates)
        
        if current_rsi is None:
            continue

        result[ticker] = {
            "rsi": current_rsi, 
            "price": prices[-1], 
            "end_date": last_end_date,
            "history": history_data[-30:]  # ★ここに追加されました
        }
    
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    output = {"date_modified": now, "result": result}    
    sys.stdout.write(json.dumps(output, ensure_ascii=False, separators=(',', ':')) + "\n")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "P"
    main(mode)
