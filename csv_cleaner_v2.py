import tkinter as tk
from tkinter import ttk, filedialog
import pandas as pd
import os

class CSVCleanerV2App:
    def __init__(self, root):
        self.root = root
        self.root.title("Visual CSV Cleaner - Advanced (v-2)")
        self.root.geometry("1150x650")
        self.root.configure(bg="#f0f0f0")
        
        # Grid weight configuration
        self.root.columnconfigure(1, weight=1)  # Main workspace gets expansion
        self.root.rowconfigure(0, weight=1)
        
        # Data variables
        self.df = None
        self.df_raw = None
        self.original_filename = ""
        
        # Build layout
        self.build_ui()
        
    def build_ui(self):
        # 1. Left Sidebar: Cleanup Configurations
        sidebar = tk.Frame(self.root, bg="#e8e8e8", width=280, padx=15, pady=15, bd=1, relief=tk.SOLID)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        
        # Title of Sidebar
        sb_title = tk.Label(sidebar, text="⚙️ CLEANUP SETTINGS", font=("Helvetica", 11, "bold"), bg="#e8e8e8", fg="#111")
        sb_title.pack(anchor="w", pady=(0, 15))
        
        # Target Column Selector
        lbl_target = tk.Label(sidebar, text="Target Column:", font=("Helvetica", 9, "bold"), bg="#e8e8e8", fg="#333")
        lbl_target.pack(anchor="w", pady=(5, 2))
        self.col_combo = ttk.Combobox(sidebar, state="readonly", font=("Helvetica", 9))
        self.col_combo['values'] = ["<All Columns>"]
        self.col_combo.set("<All Columns>")
        self.col_combo.pack(fill="x", pady=(0, 10))
        
        # Divider 1
        self.add_divider(sidebar)
        
        # String/Text cleaning options
        lbl_text_ops = tk.Label(sidebar, text="Text Cleaning:", font=("Helvetica", 9, "bold"), bg="#e8e8e8", fg="#333")
        lbl_text_ops.pack(anchor="w", pady=(5, 2))
        
        self.var_trim = tk.BooleanVar(value=True)
        chk_trim = tk.Checkbutton(sidebar, text="Trim Whitespace", variable=self.var_trim, bg="#e8e8e8", activebackground="#e8e8e8")
        chk_trim.pack(anchor="w")
        
        lbl_casing = tk.Label(sidebar, text="Casing Transformation:", font=("Helvetica", 9), bg="#e8e8e8")
        lbl_casing.pack(anchor="w", pady=(5, 2))
        self.casing_combo = ttk.Combobox(sidebar, state="readonly", font=("Helvetica", 9))
        self.casing_combo['values'] = ["No Change", "Title Case", "lowercase", "UPPERCASE"]
        self.casing_combo.set("No Change")
        self.casing_combo.pack(fill="x", pady=(0, 10))
        
        # Divider 2
        self.add_divider(sidebar)
        
        # Numeric & Formatting options
        lbl_num_ops = tk.Label(sidebar, text="Numbers & Currency:", font=("Helvetica", 9, "bold"), bg="#e8e8e8", fg="#333")
        lbl_num_ops.pack(anchor="w", pady=(5, 2))
        
        self.var_clean_currency = tk.BooleanVar(value=True)
        chk_currency = tk.Checkbutton(sidebar, text="Clean Currency symbols ($/£/€)", variable=self.var_clean_currency, bg="#e8e8e8", activebackground="#e8e8e8")
        chk_currency.pack(anchor="w")
        
        self.var_cast_number = tk.BooleanVar(value=True)
        chk_cast = tk.Checkbutton(sidebar, text="Cast to Numeric type", variable=self.var_cast_number, bg="#e8e8e8", activebackground="#e8e8e8")
        chk_cast.pack(anchor="w", pady=(0, 10))
        
        # Divider 3
        self.add_divider(sidebar)
        
        # Missing values handling
        lbl_nan_ops = tk.Label(sidebar, text="Missing Values (NaN):", font=("Helvetica", 9, "bold"), bg="#e8e8e8", fg="#333")
        lbl_nan_ops.pack(anchor="w", pady=(5, 2))
        
        self.nan_combo = ttk.Combobox(sidebar, state="readonly", font=("Helvetica", 9))
        self.nan_combo['values'] = ["Mean (Default)", "Median", "Mode", "Constant Value", "Drop rows", "Keep as is"]
        self.nan_combo.set("Mean (Default)")
        self.nan_combo.pack(fill="x", pady=(0, 5))
        self.nan_combo.bind("<<ComboboxSelected>>", self.on_nan_action_changed)
        
        lbl_constant = tk.Label(sidebar, text="Constant Fill Value:", font=("Helvetica", 9), bg="#e8e8e8")
        lbl_constant.pack(anchor="w", pady=(2, 2))
        self.constant_entry = tk.Entry(sidebar, state="disabled", font=("Helvetica", 9))
        self.constant_entry.pack(fill="x", pady=(0, 10))
        
        # Divider 4
        self.add_divider(sidebar)
        
        # Duplicate rows handling
        lbl_dup_ops = tk.Label(sidebar, text="Duplicate Handling:", font=("Helvetica", 9, "bold"), bg="#e8e8e8", fg="#333")
        lbl_dup_ops.pack(anchor="w", pady=(5, 2))
        
        self.var_duplicates = tk.BooleanVar(value=True)
        chk_dup = tk.Checkbutton(sidebar, text="Remove duplicate rows", variable=self.var_duplicates, bg="#e8e8e8", activebackground="#e8e8e8")
        chk_dup.pack(anchor="w", pady=(0, 15))
        
        
        # 2. Right Workspace: Controls, Data Grid and Log
        workspace = tk.Frame(self.root, bg="#f0f0f0")
        workspace.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)
        
        workspace.columnconfigure(0, weight=1)
        workspace.rowconfigure(2, weight=1)  # Table view expands
        
        # Title Header
        title_label = tk.Label(
            workspace, 
            text="🧹 VISUAL CSV CLEANER (V-2)", 
            font=("Helvetica", 14, "bold"), 
            bg="#f0f0f0", 
            fg="#222"
        )
        title_label.grid(row=0, column=0, pady=(0, 5), sticky="n")
        
        # Controls Frame (Row of Buttons)
        btn_frame = tk.Frame(workspace, bg="#f0f0f0")
        btn_frame.grid(row=1, column=0, pady=(5, 10), sticky="w")
        
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

        self.btn_reset = tk.Button(
            btn_frame, 
            text="🔄 Reset View", 
            bg="#6c757d", 
            fg="white", 
            activebackground="#5a6268", 
            activeforeground="white", 
            font=("Helvetica", 10, "bold"), 
            relief=tk.FLAT, 
            padx=15, 
            pady=6,
            cursor="hand2",
            command=self.reset_data
        )
        self.btn_reset.pack(side=tk.LEFT, padx=10)
        
        # Data Grid (Treeview)
        table_frame = tk.Frame(workspace, bg="#f0f0f0")
        table_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        ysb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        xsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        self.tree = ttk.Treeview(
            table_frame, 
            show="headings", 
            yscrollcommand=ysb.set, 
            xscrollcommand=xsb.set
        )
        
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
        
        # Status Log Section
        log_title = tk.Label(
            workspace, 
            text="STATUS LOG:", 
            font=("Helvetica", 9, "bold"), 
            bg="#f0f0f0", 
            fg="#333"
        )
        log_title.grid(row=3, column=0, pady=(15, 2), sticky="w")
        
        log_frame = tk.Frame(workspace, bg="#f0f0f0")
        log_frame.grid(row=4, column=0, sticky="ew")
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
        
        # Initial status
        self.log("Ready. Click 'Load CSV' to begin.")
        
    def add_divider(self, parent):
        divider = tk.Frame(parent, height=1, bg="#ccc", bd=0)
        divider.pack(fill="x", pady=10)
        
    def on_nan_action_changed(self, event=None):
        action = self.nan_combo.get()
        if action == "Constant Value":
            self.constant_entry.config(state=tk.NORMAL)
        else:
            self.constant_entry.delete(0, tk.END)
            self.constant_entry.config(state=tk.DISABLED)
            
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
                self.df_raw = pd.read_csv(fname)
                self.df = self.df_raw.copy()
                self.original_filename = os.path.basename(fname)
                
                # Update sidebar Column dropdown options
                cols = ["<All Columns>"] + list(self.df.columns)
                self.col_combo['values'] = cols
                self.col_combo.set("<All Columns>")
                
                self.refresh_table()
                self.log(f"✓ Loaded {self.original_filename} - {len(self.df)} rows")
            except Exception as e:
                self.log(f"❌ Error loading CSV: {e}")
                
    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        if self.df is None:
            return
            
        cols = list(self.df.columns)
        self.tree['columns'] = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.W)
            
        for idx, row in self.df.iterrows():
            values = ["" if pd.isna(val) else str(val) for val in row]
            self.tree.insert("", tk.END, values=values)

    def clean_data(self):
        if self.df_raw is None:
            self.log("❌ No CSV loaded. Please load a CSV file first.")
            return

        self.log("🧹 Starting parameterized cleanup...")
        try:
            # Copy original loaded dataframe to apply cleanup from scratch
            cleaned_df = self.df_raw.copy()
            original_rows = len(cleaned_df)
            
            target_col = self.col_combo.get()
            trim_whitespace = self.var_trim.get()
            casing_action = self.casing_combo.get()
            clean_currency = self.var_clean_currency.get()
            cast_number = self.var_cast_number.get()
            nan_action = self.nan_combo.get()
            constant_val = self.constant_entry.get()
            remove_dup = self.var_duplicates.get()

            # Determine columns to process
            if target_col == "<All Columns>":
                cols_to_process = list(cleaned_df.columns)
            else:
                if target_col not in cleaned_df.columns:
                    self.log(f"❌ Error: Column '{target_col}' not found.")
                    return
                cols_to_process = [target_col]

            self.log(f"⚙️ Target: {target_col}")

            # 1. Trim whitespace
            if trim_whitespace:
                trimmed_cols = []
                for col in cols_to_process:
                    if cleaned_df[col].dtype == 'object':
                        cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
                        cleaned_df[col] = cleaned_df[col].replace({'nan': None, 'NaN': None, 'None': None, '': None})
                        trimmed_cols.append(col)
                if trimmed_cols:
                    self.log(f"✓ Trimmed whitespace in columns: {', '.join(trimmed_cols)}")

            # 2. Casing standardisation
            if casing_action != "No Change":
                cased_cols = []
                for col in cols_to_process:
                    # Apply casing only to text/object columns or explicit target
                    if cleaned_df[col].dtype == 'object' or target_col != "<All Columns>":
                        if casing_action == "Title Case":
                            cleaned_df[col] = cleaned_df[col].apply(lambda x: str(x).title() if pd.notna(x) else x)
                        elif casing_action == "lowercase":
                            cleaned_df[col] = cleaned_df[col].apply(lambda x: str(x).lower() if pd.notna(x) else x)
                        elif casing_action == "UPPERCASE":
                            cleaned_df[col] = cleaned_df[col].apply(lambda x: str(x).upper() if pd.notna(x) else x)
                        cased_cols.append(col)
                if cased_cols:
                    self.log(f"✓ Applied casing '{casing_action}' to: {', '.join(cased_cols)}")

            # 3. Clean currency and formatting
            if clean_currency:
                currency_chars = ['$', '£', '€', ',', ' ']
                currency_cols = []
                for col in cols_to_process:
                    if cleaned_df[col].dtype == 'object' or target_col != "<All Columns>":
                        def clean_symbols(val):
                            if pd.isna(val) or val is None:
                                return None
                            val_str = str(val).strip()
                            for char in currency_chars:
                                val_str = val_str.replace(char, '')
                            return val_str
                        cleaned_df[col] = cleaned_df[col].apply(clean_symbols)
                        currency_cols.append(col)
                if currency_cols:
                    self.log(f"✓ Stripped currency symbols/formatting from: {', '.join(currency_cols)}")

            # 4. Cast to number
            if cast_number:
                cast_cols = []
                for col in cols_to_process:
                    converted = pd.to_numeric(cleaned_df[col], errors='coerce')
                    # Cast if column is mostly numeric or explicitly targeted
                    if converted.notna().sum() > 0 or target_col != "<All Columns>":
                        cleaned_df[col] = converted
                        cast_cols.append(col)
                if cast_cols:
                    self.log(f"✓ Cast columns to numeric: {', '.join(cast_cols)}")

            # 5. Handle missing values (NaN)
            if nan_action != "Keep as is":
                for col in cols_to_process:
                    nan_count = cleaned_df[col].isna().sum()
                    if nan_count > 0:
                        if nan_action == "Mean (Default)":
                            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                                mean_val = cleaned_df[col].mean()
                                if not pd.isna(mean_val):
                                    cleaned_df[col] = cleaned_df[col].fillna(mean_val)
                                    self.log(f"✓ Filled {nan_count} missing values in '{col}' with Mean ({mean_val:.2f})")
                            else:
                                if target_col != "<All Columns>":
                                    self.log(f"⚠️ Warning: Cannot apply Mean to non-numeric column '{col}'")
                        
                        elif nan_action == "Median":
                            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                                median_val = cleaned_df[col].median()
                                if not pd.isna(median_val):
                                    cleaned_df[col] = cleaned_df[col].fillna(median_val)
                                    self.log(f"✓ Filled {nan_count} missing values in '{col}' with Median ({median_val:.2f})")
                            else:
                                if target_col != "<All Columns>":
                                    self.log(f"⚠️ Warning: Cannot apply Median to non-numeric column '{col}'")
                        
                        elif nan_action == "Mode":
                            mode_series = cleaned_df[col].mode()
                            if not mode_series.empty:
                                mode_val = mode_series.iloc[0]
                                cleaned_df[col] = cleaned_df[col].fillna(mode_val)
                                self.log(f"✓ Filled {nan_count} missing values in '{col}' with Mode ({mode_val})")
                            else:
                                if target_col != "<All Columns>":
                                    self.log(f"⚠️ Warning: Could not find Mode for column '{col}'")
                        
                        elif nan_action == "Constant Value":
                            typed_constant = constant_val
                            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                                try:
                                    typed_constant = float(constant_val)
                                except ValueError:
                                    pass
                            cleaned_df[col] = cleaned_df[col].fillna(typed_constant)
                            self.log(f"✓ Filled {nan_count} missing values in '{col}' with constant '{constant_val}'")
                        
                        elif nan_action == "Drop rows":
                            cleaned_df = cleaned_df.dropna(subset=[col])
                            self.log(f"✓ Dropped {nan_count} rows containing missing values in '{col}'")

            # 6. Remove duplicate rows
            if remove_dup:
                if target_col == "<All Columns>":
                    dup_count = cleaned_df.duplicated().sum()
                    cleaned_df = cleaned_df.drop_duplicates()
                else:
                    dup_count = cleaned_df.duplicated(subset=[target_col]).sum()
                    cleaned_df = cleaned_df.drop_duplicates(subset=[target_col])
                if dup_count > 0:
                    self.log(f"✓ Removed {dup_count} duplicate rows.")

            self.df = cleaned_df
            self.refresh_table()
            self.log(f"✨ Cleanup complete! {original_rows} rows processed. {len(self.df)} rows in view.")
        except Exception as e:
            self.log(f"❌ Error during cleanup: {e}")

    def reset_data(self):
        if self.df_raw is not None:
            self.df = self.df_raw.copy()
            self.refresh_table()
            self.log("🔄 Reset view to original loaded state.")
        else:
            self.log("❌ No CSV loaded to reset.")

    def save_csv(self):
        if self.df is None:
            self.log("❌ No cleaned data to save. Please load and clean a CSV first.")
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
    app = CSVCleanerV2App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
