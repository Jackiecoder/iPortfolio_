import yfinance as yf
from portfolioManager import PortfolioManager
from databaseViewer import DatabaseViewer
from portfolioChartDrawer import ChartDrawer
from portfolioDisplayer import Displayer

# input data    
TRANSACTIONS_PATH = "transactions/"
CASH_PATH = "transactions/cash/cash.csv"

# output data
ROR_TABLE_PATH = "results/ror_table/"
CHART_PATH = "results/charts/"
DBVIEWER_PATH = "results/dbviewer/"

def load_transactions():
    clear_table()
    pm = PortfolioManager()
    pm.load_transactions_from_folder(TRANSACTIONS_PATH)
    pm.load_daily_cash_from_csv(CASH_PATH)
    pm.close()

def view_database():
    viewer = DatabaseViewer()
    viewer.save_transactions_to_csv(f"{DBVIEWER_PATH}transactions.csv")
    viewer.save_stock_data_to_csv(f"{DBVIEWER_PATH}stock_data.csv")
    viewer.save_daily_cash_to_csv(f"{DBVIEWER_PATH}daily_cash.csv")
    viewer.save_daily_prices_to_csv(f"{DBVIEWER_PATH}daily_prices.csv")
    viewer.save_realized_gain_to_csv(f"{DBVIEWER_PATH}realized_gains.csv")
    viewer.close()

def draw_chart():
    cd = ChartDrawer()
    cd.plot_pie_chart_with_cash(CHART_PATH+"portfolio_pie_chart.png")
    cd.plot_asset_value_vs_cost(CHART_PATH)

def display_portfolio():
    pd = Displayer()
    yyyy_mm_dd = [ ("2024", "11", "15")]
    for yyyy, mm, dd in yyyy_mm_dd:
        print(f"Generating portfolio snapshot for {yyyy}-{mm}-{dd}...")
        ror_df, summary_df = pd.calculate_rate_of_return_v2(f"{yyyy}-{mm}-{dd}")
        print("Generating rate of return chart...")
        pd.save_df_as_png(df = ror_df, 
                          filename=ROR_TABLE_PATH + f"portfolio_rate_of_return_{yyyy}_{mm}_{dd}.png",
                          title=f"Portfolio Rate of Return {yyyy}-{mm}-{dd}")
        print("Generating portfolio summary...")
        pd.save_df_as_png(df = summary_df, 
                          filename=ROR_TABLE_PATH + f"portfolio_summary_{yyyy}_{mm}_{dd}.png",
                          title=f"Portfolio Summary {yyyy}-{mm}-{dd}")

    pd.close()

def clear_table():
    # 初始化 PortfolioManager 并添加一些交易记录
    portfolio = PortfolioManager()
    # 清空 transactions 表
    portfolio.clear_table("transactions")
    # 清空 stock_data 表
    portfolio.clear_table("stock_data")
    # clear daily_cash table
    portfolio.clear_table("daily_cash")
    # clear daily_prices table
    portfolio.clear_table("realized_gains")

def main():
    print("Welcome to Portfolio Manager!")
    # load_transactions()
    view_database()
    # draw_chart()
    display_portfolio()
    

if __name__ == "__main__":
    main()