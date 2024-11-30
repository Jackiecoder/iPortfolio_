import matplotlib.pyplot as plt
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.dates as mdates


class ChartDrawer:
    def __init__(self, db_name="portfolio.db"):
      self.conn = sqlite3.connect(db_name)


    def fetch_and_store_price(self, ticker, date):
        """
        从 Yahoo Finance 获取指定日期的股票价格，并存储到 daily_prices 表。
        """
        try:
            stock = yf.Ticker(ticker)
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

            history = yf.download(ticker, start_date, end_date)
            if not history.empty:
                price_series = history['Close']
                price = list(round(price_series.iloc[-1], 8))[0]
                with self.conn:
                    self.conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                      (date, ticker, price))
                print(f"Fetched and stored price for {ticker} on {date}: {price}")
                return price
            print(f"No price data found for {ticker} on {date}")
            return None

        except Exception as e:
            print(f"Error fetching price for {ticker} on {date}: {e}")
            return None


    def fetch_and_store_latest_price(self, ticker):
        today = datetime.now().strftime("%Y-%m-%d")

        # 检查是否已有最新价格
        existing_price = self.conn.execute("""
            SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
        """, (today, ticker)).fetchone()

        if existing_price:
            print(f"Price for {ticker} on {today} already exists: {existing_price[0]}")
            return existing_price[0]

        return self.fetch_and_store_price(ticker, today)


    def plot_pie_chart_with_cash(self, file_name="results/portfolio_pie_chart.png"):
        """
        绘制一个饼图，显示最新的 stock_data,包括现金余额。
        """
        tickers = set(row[0] for row in self.conn.execute("SELECT DISTINCT ticker FROM stock_data"))

        # 获取现金余额
        latest_cash_date = self.conn.execute("SELECT MAX(date) FROM daily_cash").fetchone()[0]
        cash_row = self.conn.execute("""
            SELECT cash_balance FROM daily_cash WHERE date = ?
        """, (latest_cash_date,)).fetchone()
        cash_balance = cash_row[0] if cash_row else 0

        # 计算各股票的总价值
        labels = []
        values = []

        for ticker in tickers:
            # 获取最新价格并尝试存储到 daily_prices 表
            latest_price = self.fetch_and_store_latest_price(ticker)

            # 获取最新一天的持仓数量和成本基础
            stock_row = self.conn.execute("""
                SELECT total_quantity, cost_basis FROM stock_data WHERE ticker = ? ORDER BY date DESC LIMIT 1
            """, (ticker,)).fetchone()
            total_quantity_ticker = stock_row[0] if stock_row[0] else 0
            total_value_ticker = (latest_price * total_quantity_ticker) if latest_price else 0
            if total_value_ticker > 0:
                labels.append(ticker)
                values.append(total_value_ticker)

        # 添加现金到图表
        if cash_balance > 0:
            labels.append("Cash")
            values.append(cash_balance)

        # 按比例从高到低排序
        values, labels = zip(*sorted(zip(values, labels), reverse=False))

        # 创建颜色渐变从深到浅
        cmap = plt.get_cmap("Blues")
        colors = [cmap(i / len(values)) for i in range(len(values))]

        # 绘制饼图
        plt.figure(figsize=(8, 8))
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
        plt.title("Portfolio Distribution (Latest Data)")
        plt.tight_layout()
        plt.savefig(file_name)
        plt.show()

    def plot_asset_value_vs_cost(self, file_name = "results/portfolio_line_chart.png"):
        dates = sorted(set(row[0] for row in self.conn.execute("SELECT date FROM transactions")))
        total_values = []
        total_costs = []

        # 获取所有出现过的ticker列表
        tickers = set(row[0] for row in self.conn.execute("SELECT DISTINCT ticker FROM stock_data"))

        for date in dates:
            total_value = 0
            total_cost = 0

            for ticker in tickers:
                # 获取当天或最近的有效 cost_basis 和 quantity
                row = self.conn.execute("""
                    SELECT cost_basis, total_quantity FROM stock_data
                    WHERE ticker = ? AND date <= ?
                    ORDER BY date DESC LIMIT 1
                """, (ticker, date)).fetchone()

                if row:
                    cost_basis, quantity = row
                    total_cost += cost_basis * quantity

                    # 尝试从 daily_prices 表读取价格
                    price_row = self.conn.execute("""
                        SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
                    """, (date, ticker)).fetchone()

                    if price_row:
                        price = price_row[0]
                    else:
                        # 如果表中没有数据，从 Yahoo Finance 下载价格
                        price = self.fetch_and_store_price(ticker, date)
                        # # 获取价格信息
                        # price = self.fetch_price_without_dbwrite(ticker, date)
                    if price is not None and quantity is not None:
                        total_value += price * quantity

            total_values.append(total_value)
            total_costs.append(total_cost)
        

        file_name = ("results/portfolio_line_chart_YTD.png", \
                     "results/portfolio_line_chart_1M.png", \
                     "results/portfolio_line_chart_3M.png", \
                     "results/portfolio_line_chart_6M.png")
        today = datetime.now()
        start_date =  (datetime(2024, 1, 1), \
                        today - timedelta(days=30), \
                        today - timedelta(days=90), \
                        today - timedelta(days=180))
        for i in range(3):
            self.plot_asset_value_vs_cost_util(total_values, total_costs, dates, file_name[i], start_date[i])
        # self.plot_asset_value_vs_cost_util(total_values, total_costs, file_name, date)

    def plot_asset_value_vs_cost_util(self, total_values, total_costs, dates, \
                                        file_name="results/portfolio_line_chart.png", \
                                        start_date=datetime(2024, 1, 1)):

        # 转换日期为 datetime 对象
        dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        filtered_data = [(d, v, c) for d, v, c in zip(dates, total_values, total_costs) if d >= start_date]

        if not filtered_data:
            print("No data available from 2024-01-01 onwards.")
            return

        dates, total_values, total_costs = zip(*filtered_data)

        # 绘制线性图
        plt.figure(figsize=(12, 6))
        plt.plot(dates, total_values, label="Total Asset Value (Including Cash)", linestyle='-')
        plt.plot(dates, total_costs, label="Total Cost (Excluding Cash)", linestyle='-')
        # 在每个点上标注数值
        for i, (x, y_value, y_cost) in enumerate(zip(dates, total_values, total_costs)):
            if i % 10 == 0:  # 每 10 个点标注一次
                plt.text(x, y_value, f"{y_value:.2f}", fontsize=8, ha='center', va='bottom', color='green')  # 标注总资产值
                plt.text(x, y_cost, f"{y_cost:.2f}", fontsize=8, ha='center',  va='top', color='blue')    # 标注总成本

        # Always show the value of the last data point
        last_date = dates[-1]
        last_value = total_values[-1]
        last_cost = total_costs[-1]
        plt.text(last_date, last_value, f"{last_value:.2f}", fontsize=10, ha='center', va='bottom', color='red', fontweight='bold')
        plt.text(last_date, last_cost, f"{last_cost:.2f}", fontsize=10, ha='center', va='top', color='red', fontweight='bold')

        # Calculate and show percentage of profit increase
        start_value = total_values[0]
        start_cost = total_costs[0]
        start_profit = start_value - start_cost
        end_profit = last_value - last_cost
        profit_increase_percentage = ((end_profit - start_profit) / start_profit) * 100 if start_profit != 0 else 0

        # profit_text = f"Profit Increase: {profit_increase_percentage:.2f}%"
        # plt.text(last_date, last_value, profit_text, fontsize=10, ha='center', va='top', color='purple', fontweight='bold')
        plt.text(dates[0], total_values[0], f"Profit: {start_profit:.2f}", fontsize=10, ha='center', va='top', color='orange', fontweight='bold')
        plt.text(last_date, last_value, f"Profit: {end_profit:.2f}", fontsize=10, ha='center', va='top', color='orange', fontweight='bold')


        # 设置 x 轴为日期格式
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gcf().autofmt_xdate()  # 自动调整日期显示的角度

        # 保存/显示线性图
        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.title("Portfolio Asset Value vs Total Cost Over Time")
        plt.legend()

        # Show percentage of profit increase under the legend
        plt.text(0.5, -0.1, f"Profit Increase: {profit_increase_percentage:.2f}%", fontsize=12, ha='center', va='center', transform=plt.gca().transAxes, color='purple', fontweight='bold')

        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(file_name)
        plt.show()

    def close(self):
        self.conn.close()
        print("Database connection closed.")