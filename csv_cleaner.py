import tkinter as tk
from tkinter import ttk, filedialog
import pandas as pd
import os

class CSVCleanerApp:
    def __init__(self, root):
        self.root = root
        
        # DataFrame variables
        self.df = None
        self.original_filename = ""
        
        # Build the user interface
        self.build_ui()
        
    def build_ui(self):
        self.root.title("Visual CSV Cleaner")
        self.root.geometry("950x600")
        self.root.configure(bg="#f0f0f0")
        
        # Grid weight configuration
        self.root.rowconfigure(2, weight=1)  # The table frame gets the space
        self.root.columnconfigure(0, weight=1)
        
        # Title Header
        title_label = tk.Label(
            self.root, 
            text="🧹 VISUAL CSV CLEANER", 
            font=("Helvetica", 14, "bold"), 
            bg="#f0f0f0", 
            fg="#222"
        )
        title_label.grid(row=0, column=0, pady=(15, 5), sticky="n")
        
        # Buttons Frame
        btn_frame = tk.Frame(self.root, bg="#f0f0f0")
        btn_frame.grid(row=1, column=0, pady=(5, 10), padx=20, sticky="w")
        
        # Buttons styling (Flat, colored, with custom padding and cursor)
        self.btn_load = tk.Button(
            btn_frame, 
            text="📁 Load CSV", 
            bg="#0078d4", 
            fg="white", 
            activebackground="#005a9e", 
            activeforeground="white", 
            font=("Helvetica", 10, "bold"), 
            relief=tk.FLAT, 
            padx=15, 
            pady=6,
            cursor="hand2",
            command=self.load_csv
        )
        self.btn_load.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_clean = tk.Button(
            btn_frame, 
            text="✨ Clean Data", 
            bg="#28a745", 
            fg="white", 
            activebackground="#218838", 
            activeforeground="white", 
            font=("Helvetica", 10, "bold"), 
            relief=tk.FLAT, 
            padx=15, 
            pady=6,
            cursor="hand2",
            command=self.clean_data
        )
        self.btn_clean.pack(side=tk.LEFT, padx=10)
        
        self.btn_save = tk.Button(
            btn_frame, 
            text="💾 Save Clean CSV", 
            bg="#ff8c00", 
            fg="white", 
            activebackground="#d97600", 
            activeforeground="white", 
            font=("Helvetica", 10, "bold"), 
            relief=tk.FLAT, 
            padx=15, 
            pady=6,
            cursor="hand2",
            command=self.save_csv
        )
        self.btn_save.pack(side=tk.LEFT, padx=10)
        
        # Table (Treeview) Frame
        table_frame = tk.Frame(self.root, bg="#f0f0f0")
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        # Scrollbars
        ysb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        xsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        self.tree = ttk.Treeview(
            table_frame, 
            show="headings", 
            yscrollcommand=ysb.set, 
            xscrollcommand=xsb.set
        )
        
        # Grid layout for table elements
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        
        ysb.config(command=self.tree.yview)
        xsb.config(command=self.tree.xview)
        
        # Configure Table Header Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#e0e0e0", foreground="#333")
        style.configure("Treeview", font=("Helvetica", 9), rowheight=22)
        
        # Status Log title
        log_title = tk.Label(
            self.root, 
            text="STATUS LOG:", 
            font=("Helvetica", 9, "bold"), 
            bg="#f0f0f0", 
            fg="#333"
        )
        log_title.grid(row=3, column=0, padx=20, pady=(15, 2), sticky="w")
        
        # Log Text Area
        log_frame = tk.Frame(self.root, bg="#f0f0f0")
        log_frame.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        self.log_text = tk.Text(
            log_frame, 
            height=6, 
            font=("Consolas", 9), 
            wrap=tk.WORD, 
            bd=1, 
            relief=tk.SOLID
        )
        self.log_text.grid(row=0, column=0, sticky="ew")
        
        log_sb = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_sb.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_sb.set)
        
        # Set Initial Log Text
        self.log("Ready. Click 'Load CSV' to begin.")
        
    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def load_csv(self):
        filetypes = [("CSV files", "*.csv"), ("All files", "*.*")]
        fname = filedialog.askopenfilename(filetypes=filetypes)
        if fname:
            try:
                self.df = pd.read_csv(fname)
                self.original_filename = os.path.basename(fname)
                self.refresh_table()
                self.log(f"✓ Loaded {self.original_filename} - {len(self.df)} rows")
            except Exception as e:
                self.log(f"❌ Error loading CSV: {e}")
                
    def refresh_table(self):
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        
        if self.df is None:
            return
            
        # Re-populate columns
        cols = list(self.df.columns)
        self.tree['columns'] = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.W)
            
        # Insert rows
        for idx, row in self.df.iterrows():
            values = ["" if pd.isna(val) else str(val) for val in row]
            self.tree.insert("", tk.END, values=values)

    def clean_data(self):
        if self.df is None:
            self.log("❌ No CSV loaded. Please load a CSV file first.")
            return

        self.log("🧹 Starting automatic cleanup...")
        try:
            cleaned_df = self.df.copy()
            original_rows = len(cleaned_df)
            
            # Step 1: Remove completely empty rows
            cleaned_df = cleaned_df.dropna(how='all')
            
            # Step 2: Trim whitespace and clean values column by column
            for col in cleaned_df.columns:
                if cleaned_df[col].dtype == 'object':
                    # Clean string columns
                    cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
                    # Convert 'nan' string values back to actual NaN
                    cleaned_df[col] = cleaned_df[col].replace({'nan': None, 'NaN': None, 'None': None, '': None})
            
            self.log("✓ Trimmed leading/trailing whitespace from all text columns.")

            # Step 3: Handle specific columns if they exist
            # Column: customer_name (Title Case)
            name_col = next((c for c in cleaned_df.columns if c.lower() in ['customer_name', 'name', 'customer']), None)
            if name_col:
                cleaned_df[name_col] = cleaned_df[name_col].apply(lambda x: x.title() if pd.notna(x) else x)
                self.log(f"✓ Standardized '{name_col}' casing to Title Case.")
                
            # Column: product (Title Case)
            prod_col = next((c for c in cleaned_df.columns if c.lower() in ['product', 'item']), None)
            if prod_col:
                cleaned_df[prod_col] = cleaned_df[prod_col].apply(lambda x: x.title() if pd.notna(x) else x)
                self.log(f"✓ Standardized '{prod_col}' casing to Title Case.")

            # Column: category (Title Case)
            cat_col = next((c for c in cleaned_df.columns if c.lower() in ['category', 'genre']), None)
            if cat_col:
                cleaned_df[cat_col] = cleaned_df[cat_col].apply(lambda x: x.title() if pd.notna(x) else x)
                self.log(f"✓ Standardized '{cat_col}' casing to Title Case.")

            # Column: status (Title Case)
            status_col = next((c for c in cleaned_df.columns if c.lower() in ['status', 'state']), None)
            if status_col:
                cleaned_df[status_col] = cleaned_df[status_col].apply(lambda x: x.title() if pd.notna(x) else x)
                self.log(f"✓ Standardized '{status_col}' casing to Title Case.")

            # Column: quantity (convert to numeric, fill missing with 1.0)
            qty_col = next((c for c in cleaned_df.columns if c.lower() in ['quantity', 'qty', 'count']), None)
            if qty_col:
                cleaned_df[qty_col] = pd.to_numeric(cleaned_df[qty_col], errors='coerce')
                nan_count = cleaned_df[qty_col].isna().sum()
                if nan_count > 0:
                    cleaned_df[qty_col] = cleaned_df[qty_col].fillna(1.0)
                    self.log(f"✓ Filled {nan_count} missing values in '{qty_col}' with 1.0.")
                self.log(f"✓ Standardized '{qty_col}' values to numbers.")

            # Column: unit_price / price (strip currency symbols, convert to numeric, fill missing with median)
            price_col = next((c for c in cleaned_df.columns if c.lower() in ['unit_price', 'price', 'cost']), None)
            if price_col:
                def clean_price_val(val):
                    if pd.isna(val) or val is None:
                        return None
                    val_str = str(val).strip()
                    for char in ['$', '£', '€', ' ', ',']:
                        val_str = val_str.replace(char, '')
                    try:
                        return float(val_str)
                    except ValueError:
                        return None
                
                cleaned_df[price_col] = cleaned_df[price_col].apply(clean_price_val)
                nan_count = cleaned_df[price_col].isna().sum()
                if nan_count > 0:
                    median_val = cleaned_df[price_col].median()
                    if pd.isna(median_val):
                        median_val = 0.0
                    cleaned_df[price_col] = cleaned_df[price_col].fillna(median_val)
                    self.log(f"✓ Filled {nan_count} missing values in '{price_col}' with column median ({median_val:.2f}).")
                self.log(f"✓ Standardized and cleaned '{price_col}' values to numeric.")

            # Step 4: Remove duplicates
            duplicate_count = cleaned_df.duplicated().sum()
            if duplicate_count > 0:
                cleaned_df = cleaned_df.drop_duplicates()
                self.log(f"✓ Removed {duplicate_count} duplicate rows.")

            self.df = cleaned_df
            self.refresh_table()
            self.log(f"✨ Cleanup complete! {original_rows} rows processed. {len(self.df)} rows in view.")
        except Exception as e:
            self.log(f"❌ Error during cleanup: {e}")

    def save_csv(self):
        if self.df is None:
            self.log("❌ No data to save. Please load a CSV first.")
            return

        filetypes = [("CSV files", "*.csv"), ("All files", "*.*")]
        fname = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=filetypes)
        if fname:
            try:
                self.df.to_csv(fname, index=False)
                self.log(f"💾 Saved cleaned data to {os.path.basename(fname)}")
            except Exception as e:
                self.log(f"❌ Error saving CSV: {e}")

def main():
    root = tk.Tk()
    app = CSVCleanerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
