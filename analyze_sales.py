import pandas as pd
import sys
import os
import datetime

def init_terminal_encoding():
    """Configures system stdout and stderr to handle UTF-8 symbols on Windows terminals."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def clean_df(df):
    """Clean the raw DataFrame to standardize columns and handle missing data/formatting."""
    cleaned = df.copy()
    
    # 1. Clean and normalize status column
    if "status" in cleaned.columns:
        cleaned["status"] = cleaned["status"].astype(str).str.strip().str.title()
        
    # 2. Clean quantity column and impute missing values with 1.0
    if "quantity" in cleaned.columns:
        cleaned["quantity"] = pd.to_numeric(cleaned["quantity"], errors='coerce').fillna(1.0)
        
    # 3. Clean unit_price column (strip currency symbols and fill NaNs with column median)
    if "unit_price" in cleaned.columns:
        def clean_price(val):
            if pd.isna(val) or val is None:
                return None
            val_str = str(val).strip()
            for char in ['$', '£', '€', ',', ' ']:
                val_str = val_str.replace(char, '')
            try:
                return float(val_str)
            except ValueError:
                return None
        cleaned["unit_price"] = cleaned["unit_price"].apply(clean_price)
        median_price = cleaned["unit_price"].median()
        if pd.isna(median_price):
            median_price = 0.0
        cleaned["unit_price"] = cleaned["unit_price"].fillna(median_price)
        
    # 4. Clean category and product columns to Title Case
    for col in ["category", "product"]:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].astype(str).str.strip().str.title()
            
    # Ensure USB-C Cable is correctly capitalized (e.g. Usb-C -> USB-C)
    if "product" in cleaned.columns:
        cleaned["product"] = cleaned["product"].str.replace("Usb-C", "USB-C", case=False)
            
    return cleaned

def analyze(df, filename):
    """Analyze the sales data and return a formatted report string."""
    df["total_price"] = df["unit_price"] * df["quantity"]

    # Split by status
    orders_completed = df[df["status"] == "Completed"]
    orders_cancelled = df[df["status"] == "Cancelled"]

    # Calculate Headline metrics
    total_orders = len(df)
    completed_orders = len(orders_completed)
    cancelled_orders = len(orders_cancelled)
    cancellation_rate = (cancelled_orders / total_orders * 100) if total_orders else 0

    total_revenue = orders_completed["total_price"].sum()
    average_order = total_revenue / completed_orders if completed_orders else 0
    items_sold = orders_completed["quantity"].sum()

    # Category revenue (descending)
    category_revenue = orders_completed.groupby("category")["total_price"].sum().sort_values(ascending=False)

    # Highest revenue products (top 5)
    product_revenue = orders_completed.groupby("product")["total_price"].sum().sort_values(ascending=False).head(5)

    # Top products by quantity sold (top 5)
    product_qty = orders_completed.groupby("product")["quantity"].sum().sort_values(ascending=False).head(5)

    # Daily trend
    completed = orders_completed.copy()
    completed["order_date"] = pd.to_datetime(completed["order_date"])
    daily_sales = (
        completed.groupby("order_date")["total_price"]
        .sum()
        .sort_index()
    )

    source_name = os.path.basename(filename)
    generated_date = datetime.date.today().strftime("%Y-%m-%d")

    # Format the report string matching the screenshot layout
    border_double = "=" * 80
    border_single = "-" * 80

    report = f"""{border_double}
SALES ANALYSIS REPORT
{border_double}

Source: {source_name}
Generated: {generated_date}

{border_single}
HEADLINE METRICS
{border_single}

  Total orders:      {total_orders}
  Completed orders:  {completed_orders}
  Cancelled orders:  {cancelled_orders}
  Cancellation rate: {cancellation_rate:.1f}%

  Total revenue:      ${total_revenue:,.2f}
  Average order value: ${average_order:,.2f}
  Items sold:         {items_sold:.0f}

{border_single}
REVENUE BY CATEGORY
{border_single}

"""
    for cat, rev in category_revenue.items():
        pct = (rev / total_revenue * 100) if total_revenue else 0
        report += f"  {cat:<20} $ {rev:>7.2f}    ({pct:>4.1f}%)\n"

    report += f"""
{border_single}
TOP PRODUCTS BY REVENUE
{border_single}

"""
    for idx, (prod, rev) in enumerate(product_revenue.items(), 1):
        report += f"  {idx}. {prod:<20} $ {rev:>7.2f}\n"

    report += f"""
{border_single}
TOP PRODUCTS BY QUANTITY SOLD
{border_single}

"""
    for idx, (prod, qty) in enumerate(product_qty.items(), 1):
        report += f"  {idx}. {prod:<19} {qty:>2.0f} units\n"

    report += f"""
{border_single}
DAILY SALES TREND
{border_single}

"""
    for date, amt in daily_sales.items():
        date_str = date.strftime('%Y-%m-%d')
        report += f"  {date_str}   $ {amt:>7.2f}\n"

    return report

def main():
    init_terminal_encoding()
    if len(sys.argv) < 2:
        print("\n  Usage: python analyze_sales.py <filename>")
        return
    
    filename = sys.argv[1]
    try:
        df = pd.read_csv(filename)
    except Exception as e:
        print(f"Error loading file '{filename}': {e}")
        return

    # Pre-clean the raw data before analysis
    df_clean = clean_df(df)
    report = analyze(df_clean, filename)
    print(report)

    # Save report to sales_report.txt
    try:
        with open("sales_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        print("✓ Saved report to sales_report.txt")
    except Exception as e:
        print(f"Error saving report to file: {e}")

if __name__ == "__main__":
    main()