# import library
import pandas as pd
import sys

# 1. System/Terminal Configuration
def init_terminal_encoding():
    """Configures system stdout and stderr to handle UTF-8 symbols on Windows terminals."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')


def load_all_books(path):
    """Loads csv file containing all scrapped books"""
    df = pd.read_csv(path)
    return df

def show_result(df, header_message, limit=20):
    if header_message:
        print(f"\n {header_message}")
    if df.empty:
        print("No results found\n")
        return

    print()
    print(f"{'#' :<5} {'Title':<40} {'Price':>5} {'Category':>20} {'Rating':<5}")
    print("-" * 85)

    items = df if limit is None else df.head(limit)
    for i, row in items.iterrows():
        title = row['Title']
        if len(title) > 40:
            title = title[:40] + "..."
            
        try:
            rating_val = int(row["Rating"])
            stars = "★" * rating_val
        except (ValueError, TypeError):
            stars = "N/A"
            
        try:
            price_val = float(row['Price'])
            price_str = f"{price_val:>5.2f}"
        except (ValueError, TypeError):
            price_str = "  N/A"
            
        category_str = str(row['Category'])
        print(f"{i :<5} {title :<40} {price_str} {category_str:>20} {stars:<5}")
    print()


def command_search(df, query):
    """Handle searching the database for books base on arguments passed"""
    if not query:
        print(' Usage: search <keyword>')
        return df

    try:
        title_match = df['Title'].str.contains(query, case=False, na=False, regex=False)
        desc_match = df['Description'].str.contains(query, case=False, na=False, regex=False)
        matches = df[title_match | desc_match]
        show_result(matches, f"Found {len(matches)} for '{query}'")
        return matches
    except Exception as e:
        print(f"  Error searching for '{query}': {e}")
        return df


def command_stats(df):
    """Handle statistics of the database"""
    if df.empty:
        print("No books in current view")
        return

    try:
        prices = pd.to_numeric(df['Price'], errors='coerce').dropna()
        ratings = pd.to_numeric(df['Rating'], errors='coerce').dropna()
        categories = df['Category'].dropna()
        stock_counts = pd.to_numeric(df['Stock Count'], errors='coerce').dropna()

        print(f"\n Books:          {len(df)}")
        print(f" Categories:     {categories.nunique()}")
        if not prices.empty:
            print(f" Average Price:  £{prices.mean():.2f}")
            print(f" Price Range:    £{prices.min():.2f} - £{prices.max():.2f}")
        else:
            print(" Average Price:  N/A")
            print(" Price Range:    N/A")
            
        if not ratings.empty:
            print(f" Average Rating: {ratings.mean():.2f} stars")
        else:
            print(" Average Rating: N/A")
            
        if not stock_counts.empty:
            in_stock = (stock_counts > 0).sum()
            print(f" In Stock:       {in_stock} ({in_stock / len(df) * 100:.0f}%)")
        else:
            print(" In Stock:       N/A")
            
        print("\n Rating breakdown:")
        for stars in range(1, 6):
            count = (ratings == stars).sum()
            stars_str = "★" * stars
            print(f"  {stars_str :<5} {count:>5}")
            
        print("\n Top 5 categories by book count")
        all_cats = categories.value_counts().head(5)
        for cat, count in all_cats.items():
            print(f"  {cat:<20} {count:>5}")
        print()
    except Exception as e:
        print(f"  Error calculating statistics: {e}")


def command_reset(df):
    """Handle resetting the database"""
    try:
        new_df = load_all_books('books.csv')
        print("Filters cleared. 1000 books in view")
        return new_df
    except Exception as e:
        print(f"  Error reloading database: {e}")
        return df


def command_show(df, args):
    """Handle showing the first n books of the database"""
    limit = 20
    if args:
        try:
            limit = int(args[0])
            if limit <= 0:
                print("  Warning: Limit must be greater than 0. Showing first 20 books.")
                limit = 20
        except ValueError:
            print(f"  Warning: '{args[0]}' is not a valid number. Defaulting to 20.")
    show_result(df, f"Showing first {limit} books", limit=limit)
    return df


def command_sort(df, args):
    """Handle sorting the database"""
    if not args:
        print("\n  Usage: sort <field> [asc/desc]")
        print("  Available fields: Title, Price, Rating, Category, Stock Count")
        return df
    
    input_field = args[0]
    column_mapping = {col.lower(): col for col in df.columns}
    column_mapping['stock'] = 'Stock Count'
    column_mapping['stock_count'] = 'Stock Count'
    
    field = column_mapping.get(input_field.lower())
    if not field:
        print(f"\n  Error: Field '{input_field}' is not supported. Use one of: {', '.join(df.columns)}")
        return df
        
    ascending = not (len(args) > 1 and args[1].lower() == "desc")
    try:
        sorted_df = df.sort_values(by=field, ascending=ascending)
        direction = "ascending" if ascending else "descending"
        print(f"  Sorted by {field} ({direction}). Showing top 10:")
        show_result(sorted_df, "", limit=10)
    except Exception as e:
        print(f"  Error sorting by '{field}': {e}")
    return df


def command_filter_by(df, args):
    """Handle filtering the database"""
    if not args:
        print("\n  Usage: filter_by <filter1> [filter2] ...")
        print("  Available filters: category=<val>, min_price=<val>, max_price=<val>, rating>=<val>, rating<=<val>")
        return df

    mask = pd.Series(True, index=df.index)   # start: keep everything
    applied = []
    any_applied = False

    for arg in args:
        try:
            if arg.startswith("category="):
                parts = arg.split("=", 1)
                if len(parts) < 2:
                    print(f"  Warning: Invalid category filter format '{arg}'. Expected category=<value>")
                    continue
                value = parts[1]
                mask &= df["Category"].str.contains(value, case=False, na=False, regex=False)
                applied.append(f"category={value}")
                any_applied = True

            elif arg.startswith("min_price="):
                parts = arg.split("=", 1)
                if len(parts) < 2:
                    print(f"  Warning: Invalid min_price filter format '{arg}'. Expected min_price=<value>")
                    continue
                value = float(parts[1])
                mask &= (df["Price"] >= value)
                applied.append(f"price>={value:.2f}")
                any_applied = True

            elif arg.startswith("max_price="):
                parts = arg.split("=", 1)
                if len(parts) < 2:
                    print(f"  Warning: Invalid max_price filter format '{arg}'. Expected max_price=<value>")
                    continue
                value = float(parts[1])
                mask &= (df["Price"] <= value)
                applied.append(f"price<={value:.2f}")
                any_applied = True
            
            elif arg.startswith("rating>="):
                parts = arg.split(">=", 1)
                if len(parts) < 2:
                    print(f"  Warning: Invalid rating filter format '{arg}'. Expected rating>=<value>")
                    continue
                value = int(parts[1])
                mask &= (df["Rating"] >= value)
                applied.append(f"rating>={value}")
                any_applied = True

            elif arg.startswith("rating<="):
                parts = arg.split("<=", 1)
                if len(parts) < 2:
                    print(f"  Warning: Invalid rating filter format '{arg}'. Expected rating<=<value>")
                    continue
                value = int(parts[1])
                mask &= (df["Rating"] <= value)
                applied.append(f"rating<={value}")
                any_applied = True
            
            else:
                print(f"  Warning: Unknown filter format '{arg}'. Skipped.")
        except ValueError:
            print(f"  Warning: Failed to parse filter '{arg}' due to invalid value format. Skipped.")
        except Exception as e:
            print(f"  Warning: Error parsing filter '{arg}': {e}. Skipped.")

    if not any_applied:
        return df

    result = df[mask]
    print(f"    Filter applied: {', '.join(applied)}")
    show_result(result, f"{len(result)} books match")
    return result


def command_save(df, args):
    """Handle saving the filtered database"""
    if not args:
        print('Usage: save <filename>')
        return df
    path = args[0]
    try:
        df.to_csv(path, index=False)
        print(f"  ✓ Exported {len(df)} books to {path}")
    except Exception as e:
        print(f"  Error saving to file '{path}': {e}")
    return df


def handle_command(line, df, current):
    """Handles execution base on users choice of command"""
    parts = line.split()
    if not parts:
        return current
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == 'search':
        return command_search(current, ' '.join(args))
    elif cmd == 'stats':
        command_stats(current)
        return current
    elif cmd == 'reset':
        return command_reset(df)
    elif cmd == 'show':
        return command_show(current, args)
    elif cmd == 'sort':
        return command_sort(current, args)
    elif cmd == 'filter_by':
        return command_filter_by(current, args)
    elif cmd == 'save':
        return command_save(current, args)
    else:
        print(f"Error: Unknown command '{cmd}'. Type 'help' to see available commands.")
        return current


def run_repl(df):
    """Runs the REPL in the terminal"""
    current = df # the current view - starts as the whole dataset
    border = "=" * 90
    print(border)
    print("BOOK CATALOG SEARCH - 1000 books loaded from books.csv")
    print(border)
    print()
    print("Type 'help' for available commands, 'quit' to exit.")
    print()

    while True:
        try:
            line = input('> ').strip()
            if not line:
                continue
            parts = line.split()
            if not parts:
                continue
            cmd = parts[0].lower()
            if cmd == 'quit':
                print('Goodbye!')
                break
            if cmd == 'help':
                print("""
  Available Commands:
    help                                 - Show this help message
    stats                                - Show statistics of the current view
    search <keyword>                     - Search for books by title or description
    reset                                - Reset the view to all 1000 books
    show [<n>]                           - Show the first n books (default 20)
    sort <field> [asc/desc]              - Sort the current view by field
    filter_by <filter1> [filter2] ...    - Filter the current view
                                           Supported filters:
                                             category=<val>
                                             min_price=<val>
                                             max_price=<val>
                                             rating>=<val>
                                             rating<=<val>
    save <filename>                      - Save the current view to a CSV file
    quit                                 - Exit the program
                """)
                continue
            
            # parse the command and dispatch
            current = handle_command(line, df, current)
        except KeyboardInterrupt:
            print('\nGoodbye!')
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


def main():
    init_terminal_encoding()
    try:
        df = load_all_books('books.csv')
    except Exception as e:
        print(f"Critical Error: Could not load 'books.csv': {e}")
        sys.exit(1)
    run_repl(df)

if __name__ == '__main__':
    main()
