import yfinance as yf
import pandas as pd
import ta

# 코스피 종목 리스트 가져오기
url = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download"
df_krx = pd.read_html(url, header=0)[0]

df_krx["종목코드"] = df_krx["종목코드"].map('{:06d}'.format)
tickers = df_krx["종목코드"].apply(lambda x: x + ".KS").tolist()

print(f"총 종목 수: {len(tickers)}")

results = []

# 시장 필터
kospi = yf.download("^KS11", period="3mo", progress=False)
kospi_ma60 = kospi["Close"].rolling(60).mean().iloc[-1]
market_ok = kospi["Close"].iloc[-1] > kospi_ma60

if not market_ok:
    print("시장 하락 추세 → 스킵")
else:
    print("시장 상승 추세 → 스캔 시작")

    for ticker in tickers[:300]:  # 속도 고려 (300개 제한)
        try:
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)

            if len(df) < 60:
                continue

            df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
            df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=20).cci()
            df["ATR"] = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"], window=14).average_true_range()

            df["ATR_pct"] = df["ATR"] / df["Close"] * 100
            df["MA20"] = df["Close"].rolling(20).mean()
            df["MA60"] = df["Close"].rolling(60).mean()
            df["Volume_MA20"] = df["Volume"].rolling(20).mean()

            latest = df.iloc[-1]

            high_60 = df["Close"].rolling(60).max().iloc[-1]
            drawdown = (latest["Close"] - high_60) / high_60 * 100

            if (
                50 <= latest["RSI"] <= 60 and
                df["CCI"].iloc[-3:].min() < 0 and latest["CCI"] > 0 and
                latest["ATR_pct"] > df["ATR_pct"].rolling(5).mean().iloc[-1] and
                -10 <= drawdown <= -5 and
                latest["MA20"] > latest["MA60"] and
                latest["Close"] > latest["MA20"] and
                latest["Volume"] > latest["Volume_MA20"]
            ):
                results.append({
                    "Ticker": ticker,
                    "Price": latest["Close"],
                    "RSI": round(latest["RSI"], 1),
                    "CCI": round(latest["CCI"], 1),
                    "ATR%": round(latest["ATR_pct"], 2),
                    "Drawdown%": round(drawdown, 2)
                })

        except Exception:
            continue

# 결과 저장
result_df = pd.DataFrame(results)

if len(result_df) > 0:
    result_df = result_df.sort_values(by="ATR%", ascending=False)
    result_df.to_csv("result.csv", index=False)
    print(result_df)
else:
    print("조건 만족 종목 없음")
