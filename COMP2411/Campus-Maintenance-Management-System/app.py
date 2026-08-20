import json
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
from datetime import datetime

from db import fetch_all, fetch_one, describe_table, execute, executemany, get_tables


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Campus Maintenance and Management System (CMMS)")
        self.geometry("1200x800")

        # Global styling
        self._init_styles()

        # App title
        title = ttk.Label(self, text="Campus Maintenance and Management System", style="Title.TLabel")
        title.pack(fill=tk.X, padx=16, pady=(12, 0))

        # Toolbar
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(fill=tk.X, padx=12, pady=8)
        self.refresh_btn = ttk.Button(self.toolbar, text="🔄 Refresh", command=self._refresh_active_tab)
        self.refresh_btn.pack(side=tk.LEFT)
        ttk.Separator(self.toolbar, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=8)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.crud_tab = CrudTab(notebook)
        self.bulk_tab = BulkInsertTab(notebook)
        self.sql_tab = SqlRunnerTab(notebook)
        self.cleaning_tab = CleaningSearchTab(notebook)
        self.reports_tab = ReportsTab(notebook)

        notebook.add(self.crud_tab, text="CRUD")
        notebook.add(self.bulk_tab, text="Bulk Insert")
        notebook.add(self.sql_tab, text="SQL Runner")
        notebook.add(self.cleaning_tab, text="Cleaning Schedule")
        notebook.add(self.reports_tab, text="Reports")

        # Status bar
        self.status = ttk.Label(self, text="Ready", anchor=tk.W, style="Status.TLabel")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _init_styles(self) -> None:
        style = ttk.Style()
        # Prefer a modern theme if available
        try:
            style.theme_use('clam')
        except Exception:
            pass

        base_font = tkfont.nametofont("TkDefaultFont")
        base_font.configure(size=10)
        mono_font = tkfont.Font(family="Consolas", size=10)
        self._mono_font = mono_font

        # Light palette
        primary = '#2563eb'  # blue-600
        primary_active = '#1d4ed8'
        style.configure("TLabel", padding=2)
        style.configure("TButton", padding=(10, 6))
        style.map("TButton", relief=[("pressed", "sunken"), ("!pressed", "raised")])
        style.configure("Primary.TButton", padding=(12, 6), foreground='white', background=primary)
        style.map("Primary.TButton", background=[('active', primary_active)])
        style.configure("Title.TLabel", font=(base_font.actual("family"), 14, "bold"), padding=(4, 6), foreground=primary_active)
        style.configure("Status.TLabel", padding=(8, 4))
        # Treeview styling
        style.configure("Treeview", rowheight=24, background='white', fieldbackground='white')
        style.configure("Treeview.Heading", font=(base_font.actual("family"), 10, "bold"))
        # Group frames
        style.configure("TLabelframe", borderwidth=1)
        style.configure("TLabelframe.Label", foreground=primary_active)

    def _refresh_active_tab(self):
        try:
            # If active tab has refresh/load function, call it
            # For CRUD, reload selected table; for others, no-op
            if isinstance(self.crud_tab, CrudTab) and self.crud_tab.table_var.get():
                self.crud_tab.load_table()
            self.status.configure(text="Refreshed")
        except Exception as e:
            messagebox.showerror("Refresh", str(e))


class CrudTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.table_var = tk.StringVar()
        self.fields_frame = ttk.LabelFrame(self, text="Fields")
        self.inputs: dict[str, tk.Widget] = {}
        self.pk_fields: set[str] = set()
        self.columns: list[str] = []

        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=10)
        ttk.Label(top, text="Table:").pack(side=tk.LEFT)
        self.table_combo = ttk.Combobox(top, textvariable=self.table_var, values=get_tables(), state="readonly")
        self.table_combo.pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="Load", command=self.load_table).pack(side=tk.LEFT)

        self.fields_frame.pack(fill=tk.X, padx=12, pady=10)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, padx=12, pady=10)
        ttk.Button(btns, text="➕ Insert", style="Primary.TButton", command=self.insert_row).pack(side=tk.LEFT)
        ttk.Button(btns, text="✎ Update (by PK)", command=self.update_row).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="🗑 Delete (by PK)", command=self.delete_row).pack(side=tk.LEFT)

        self.results_group = ttk.LabelFrame(self, text="Rows")
        self.results_group.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.results = ResultsTable(self.results_group)
        self.results.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def load_table(self):
        table = self.table_var.get()
        if not table:
            return
        for child in self.fields_frame.winfo_children():
            child.destroy()
        self.inputs.clear()
        self.pk_fields.clear()

        desc = describe_table(table)
        self.columns = [col[0] for col in desc]
        grid = ttk.Frame(self.fields_frame)
        grid.pack(fill=tk.X)
        for idx, (field, col_type, is_null, key, default, extra) in enumerate(desc):
            ttk.Label(grid, text=field).grid(row=idx, column=0, sticky=tk.W, padx=4, pady=2)
            widget = self._make_input_widget(grid, self.table_var.get(), field, col_type)
            widget.grid(row=idx, column=1, sticky=tk.EW, padx=4, pady=2)
            grid.grid_columnconfigure(1, weight=1)
            self.inputs[field] = widget
            if key == 'PRI':
                self.pk_fields.add(field)

        # Show current rows
        cols, rows = fetch_all(f"SELECT * FROM `{table}` LIMIT 200")
        self.results.set_data(cols, rows)

    def _collect_values(self) -> dict:
        values = {}
        for k, widget in self.inputs.items():
            v = self._get_widget_value(widget)
            if v == "":
                values[k] = None
            else:
                values[k] = v
        return values

    def _get_widget_value(self, widget: tk.Widget) -> str:
        if isinstance(widget, ttk.Combobox):
            return widget.get().strip()
        if isinstance(widget, tk.Entry):
            return widget.get().strip()
        if isinstance(widget, ttk.Frame):
            # Datetime composite (Entry inside or Spinboxes)
            # Look for an Entry child if present
            for ch in widget.winfo_children():
                if isinstance(ch, tk.Entry):
                    return ch.get().strip()
        return ""

    def _make_input_widget(self, parent: tk.Misc, table: str, field: str, col_type: str) -> tk.Widget:
        # ENUM → Combobox
        if col_type.lower().startswith('enum('):
            opts = self._parse_enum_options(col_type)
            cb = ttk.Combobox(parent, values=opts, state='readonly')
            return cb
        # DATE/DATETIME → entry with Now button
        if col_type.lower().startswith('datetime'):
            wrap = ttk.Frame(parent)
            e = ttk.Entry(wrap)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            def set_now():
                e.delete(0, tk.END)
                e.insert(0, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ttk.Button(wrap, text='Now', command=set_now).pack(side=tk.LEFT, padx=4)
            return wrap
        if col_type.lower().startswith('date'):
            wrap = ttk.Frame(parent)
            e = ttk.Entry(wrap)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            def set_today():
                e.delete(0, tk.END)
                e.insert(0, datetime.now().strftime('%Y-%m-%d'))
            ttk.Button(wrap, text='Today', command=set_today).pack(side=tk.LEFT, padx=4)
            return wrap
        # FK selector heuristic: *_id referencing another table
        if field.endswith('_id'):
            # Map field names to table names
            ref_table_map = {
                'emp_id': 'Employee',
                'manager_id': 'Employee',
                'created_by': 'Employee',
                'manager_emp_id': 'Employee',
                'building_id': 'Building',
                'location_building_id': 'Building',
                'level_id': 'Level',
                'location_level_id': 'Level',
                'contractor_id': 'Contractor',
                'activity_id': 'Activity',
                'chemical_id': 'Chemical'
            }
            ref_table = ref_table_map.get(field, field[:-3].capitalize())
            try:
                cols, rows = fetch_all(f"SHOW COLUMNS FROM `{ref_table}`")
                # Pick display column: first 'name' column else second column
                display_col = None
                for r in rows:
                    if 'name' in r[0].lower():
                        display_col = r[0]
                        break
                if not display_col and len(rows) > 1:
                    display_col = rows[1][0]
                if display_col:
                    pass
            except Exception:
                display_col = None
            # Simpler: query ref table directly
            try:
                cols, opts = fetch_all(f"SELECT `{field}`, * FROM `{ref_table}`")
            except Exception:
                opts = []
            values = []
            ids = []
            if opts:
                # build 'id - label'
                for row in opts:
                    rid = row[0]
                    label = None
                    for col_val in row[1:]:
                        if isinstance(col_val, str):
                            label = col_val
                            break
                    values.append(f"{rid}") if label is None else values.append(f"{rid} - {label}")
                    ids.append(str(rid))
            cb = ttk.Combobox(parent, values=values)
            return cb
        # Default: simple entry
        return ttk.Entry(parent)

    def _parse_enum_options(self, col_type: str) -> list[str]:
        inside = col_type[col_type.find('(')+1:col_type.rfind(')')]
        raw = []
        cur = ''
        in_quote = False
        for ch in inside:
            if ch == "'":
                in_quote = not in_quote
            elif ch == ',' and not in_quote:
                raw.append(cur)
                cur = ''
            else:
                cur += ch
        if cur:
            raw.append(cur)
        return [s.replace("'", "").strip() for s in raw]

    def insert_row(self):
        table = self.table_var.get()
        if not table:
            return
        values = self._collect_values()
        # Enforce limits for Employee role inserts
        if table == 'Employee' and values.get('role') in ('MANAGER', 'WORKER'):
            role = values.get('role')
            if not self._check_role_limit(role, adding_one=True):
                messagebox.showerror("Limit Exceeded", f"Inserting {role} exceeds configured limit in Config")
                return
        # Validate Activity location fields
        if table == 'Activity':
            if not self._validate_activity_location(values):
                return
        cols = [c for c, v in values.items() if v is not None]
        params = [values[c] for c in cols]
        if not cols:
            messagebox.showwarning("Insert", "No values provided")
            return
        placeholders = ",".join(["%s"] * len(cols))
        col_list = ",".join([f"`{c}`" for c in cols])
        q = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"
        try:
            execute(q, tuple(params))
            self.load_table()
            messagebox.showinfo("Insert", "Row inserted")
        except Exception as e:
            messagebox.showerror("Insert Error", str(e))

    def update_row(self):
        table = self.table_var.get()
        if not table:
            return
        if not self.pk_fields:
            messagebox.showwarning("Update", "Table has no primary key; update not supported")
            return
        values = self._collect_values()
        # Enforce limits when changing Employee.role to MANAGER/WORKER
        if table == 'Employee' and values.get('role') in ('MANAGER', 'WORKER'):
            role = values.get('role')
            if not self._check_role_limit(role, adding_one=False, updating_to_role=True, pk_values=[values.get(c) for c in self.pk_fields]):
                messagebox.showerror("Limit Exceeded", f"Updating to {role} exceeds configured limit in Config")
                return
        # Validate Activity location fields
        if table == 'Activity':
            # Get current values for fields not being updated
            where_cols = [c for c in self.pk_fields if values.get(c) is not None]
            if len(where_cols) == len(self.pk_fields):
                where_clause = " AND ".join([f"`{c}`=%s" for c in where_cols])
                where_params = tuple([values[c] for c in where_cols])
                cols, current_row = fetch_one(f"SELECT * FROM `{table}` WHERE {where_clause}", where_params)
                if current_row:
                    # Merge current values with new values
                    current_values = dict(zip(cols, current_row))
                    for k, v in current_values.items():
                        if values.get(k) is None:
                            values[k] = v
            if not self._validate_activity_location(values):
                return
        set_cols = [c for c in self.columns if c not in self.pk_fields and values.get(c) is not None]
        if not set_cols:
            messagebox.showwarning("Update", "Provide values to update (non-PK fields)")
            return
        where_cols = [c for c in self.pk_fields if values.get(c) is not None]
        if len(where_cols) != len(self.pk_fields):
            messagebox.showwarning("Update", "Provide all primary key values")
            return
        set_clause = ", ".join([f"`{c}`=%s" for c in set_cols])
        where_clause = " AND ".join([f"`{c}`=%s" for c in where_cols])
        params = [values[c] for c in set_cols] + [values[c] for c in where_cols]
        q = f"UPDATE `{table}` SET {set_clause} WHERE {where_clause}"
        try:
            execute(q, tuple(params))
            self.load_table()
            messagebox.showinfo("Update", "Row(s) updated")
        except Exception as e:
            messagebox.showerror("Update Error", str(e))

    def delete_row(self):
        table = self.table_var.get()
        if not table:
            return
        values = self._collect_values()
        where_cols = [c for c in self.pk_fields if values.get(c) is not None]
        if len(where_cols) != len(self.pk_fields):
            messagebox.showwarning("Delete", "Provide all primary key values")
            return
        where_clause = " AND ".join([f"`{c}`=%s" for c in where_cols])
        params = [values[c] for c in where_cols]
        q = f"DELETE FROM `{table}` WHERE {where_clause}"
        try:
            execute(q, tuple(params))
            self.load_table()
            messagebox.showinfo("Delete", "Row(s) deleted")
        except Exception as e:
            messagebox.showerror("Delete Error", str(e))

    def _validate_activity_location(self, values: dict) -> bool:
        """Validate Activity location fields consistency"""
        room_no = values.get('location_room_no')
        level_id = values.get('location_level_id')
        building_id = values.get('location_building_id')
        
        # If room_no is specified, level_id and building_id must also be specified
        if room_no and room_no != '':
            if not level_id or level_id == '':
                messagebox.showerror("Validation Error", 
                    "If location_room_no is specified, location_level_id must also be specified")
                return False
            if not building_id or building_id == '':
                messagebox.showerror("Validation Error", 
                    "If location_room_no is specified, location_building_id must also be specified")
                return False
        
        # If level_id is specified, building_id must also be specified
        if level_id and level_id != '':
            if not building_id or building_id == '':
                messagebox.showerror("Validation Error", 
                    "If location_level_id is specified, location_building_id must also be specified")
                return False
        
        return True

    def _check_role_limit(self, role: str, adding_one: bool, updating_to_role: bool = False, pk_values: list[str] | None = None) -> bool:
        # Fetch limits from Config (key-value pairs)
        _, max_mgr_row = fetch_one("SELECT config_value FROM Config WHERE config_key='max_managers'")
        _, max_wkr_row = fetch_one("SELECT config_value FROM Config WHERE config_key='max_workers'")
        if not max_mgr_row or not max_wkr_row:
            return True  # No limits configured
        try:
            max_managers = int(max_mgr_row[0])
            max_workers = int(max_wkr_row[0])
        except (ValueError, TypeError):
            return True
        # Current counts
        _, mgr_row = fetch_one("SELECT COUNT(*) FROM Employee WHERE role='MANAGER'")
        _, wkr_row = fetch_one("SELECT COUNT(*) FROM Employee WHERE role='WORKER'")
        mgr_cnt = mgr_row[0] if mgr_row else 0
        wkr_cnt = wkr_row[0] if wkr_row else 0
        # If updating, check if current record already in that role to avoid double counting
        delta = 1 if adding_one else 0
        if updating_to_role and pk_values:
            where_clause = " AND ".join([f"`{c}`=%s" for c in self.pk_fields])
            cols, row_old = fetch_one(f"SELECT role FROM Employee WHERE {where_clause}", tuple(pk_values))
            if row_old and row_old[0] == role:
                delta = 0
            else:
                delta = 1
        if role == 'MANAGER':
            return (mgr_cnt + delta) <= max_managers
        if role == 'WORKER':
            return (wkr_cnt + delta) <= max_workers
        return True


class BulkInsertTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.table_var = tk.StringVar()
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=10)
        ttk.Label(top, text="Table:").pack(side=tk.LEFT)
        self.table_combo = ttk.Combobox(top, textvariable=self.table_var, values=get_tables(), state="readonly")
        self.table_combo.pack(side=tk.LEFT, padx=8)
        self.format_var = tk.StringVar(value="CSV")
        ttk.Radiobutton(top, text="CSV", variable=self.format_var, value="CSV").pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(top, text="JSON Lines", variable=self.format_var, value="JSON").pack(side=tk.LEFT)
        ttk.Button(top, text="⬇ Insert Rows", style="Primary.TButton", command=self.insert_bulk).pack(side=tk.RIGHT)

        self.help = tk.Text(self, height=6)
        self.help.pack(fill=tk.X, padx=12)
        self.help.insert(tk.END, "CSV: header row with column names, subsequent rows with values.\n")
        self.help.insert(tk.END, "JSON Lines: one JSON object per line with column:value pairs.\n")

        self.text = tk.Text(self)
        mono_font = getattr(self.winfo_toplevel(), "_mono_font", tkfont.nametofont("TkFixedFont"))
        self.text.configure(font=mono_font)
        self.text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def insert_bulk(self):
        table = self.table_var.get()
        if not table:
            return
        body = self.text.get("1.0", tk.END).strip()
        if not body:
            return
        try:
            desc = describe_table(table)
            all_cols = [c[0] for c in desc]
            if self.format_var.get() == "CSV":
                lines = [ln for ln in body.splitlines() if ln.strip()]
                header = [h.strip() for h in lines[0].split(",")]
                for h in header:
                    if h not in all_cols:
                        raise ValueError(f"Unknown column: {h}")
                rows = []
                for ln in lines[1:]:
                    parts = [p.strip() for p in self._split_csv(ln)]
                    rows.append(tuple(None if p=="" else p for p in parts))
                col_list = ",".join([f"`{c}`" for c in header])
                placeholders = ",".join(["%s"] * len(header))
                q = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"
                executemany(q, rows)
            else:
                rows_json = [json.loads(ln) for ln in body.splitlines() if ln.strip()]
                if not rows_json:
                    return
                header = list(rows_json[0].keys())
                for h in header:
                    if h not in all_cols:
                        raise ValueError(f"Unknown column: {h}")
                rows = []
                for obj in rows_json:
                    rows.append(tuple(None if obj.get(c) in ("", None) else obj.get(c) for c in header))
                col_list = ",".join([f"`{c}`" for c in header])
                placeholders = ",".join(["%s"] * len(header))
                q = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"
                executemany(q, rows)
            messagebox.showinfo("Bulk Insert", "Rows inserted")
        except Exception as e:
            messagebox.showerror("Bulk Insert Error", str(e))

    def _split_csv(self, line: str) -> list[str]:
        # Safe splitter supporting quoted commas
        result, cur, in_quotes = [], [], False
        for ch in line:
            if ch == '"':
                in_quotes = not in_quotes
            elif ch == ',' and not in_quotes:
                result.append(''.join(cur))
                cur = []
            else:
                cur.append(ch)
        result.append(''.join(cur))
        return result


class SqlRunnerTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=10)
        ttk.Button(top, text="▶ Run", style="Primary.TButton", command=self.run_query).pack(side=tk.RIGHT)
        editor_group = ttk.LabelFrame(self, text="SQL Editor")
        editor_group.pack(fill=tk.X, padx=12)
        self.sql_text = tk.Text(editor_group, height=8)
        mono_font = getattr(self.winfo_toplevel(), "_mono_font", tkfont.nametofont("TkFixedFont"))
        self.sql_text.configure(font=mono_font)
        self.sql_text.pack(fill=tk.X, padx=12)
        results_group = ttk.LabelFrame(self, text="Results")
        results_group.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.results = ResultsTable(results_group)
        self.results.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def run_query(self):
        sql = self.sql_text.get("1.0", tk.END).strip()
        if not sql:
            return
        try:
            cols, rows = fetch_all(sql)
            self.results.set_data(cols, rows)
        except Exception as e:
            messagebox.showerror("SQL Error", str(e))


class CleaningSearchTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()
        self.buildings_list = None

        filt = ttk.LabelFrame(self, text="Filters")
        filt.pack(fill=tk.X, padx=12, pady=10)
        ttk.Label(filt, text="From:").pack(side=tk.LEFT)
        self.from_widget = self._make_dt_picker(filt, self.from_var)
        ttk.Label(filt, text="To:").pack(side=tk.LEFT, padx=(12, 0))
        self.to_widget = self._make_dt_picker(filt, self.to_var)
        ttk.Button(filt, text="🔍 Search", style="Primary.TButton", command=self.search).pack(side=tk.RIGHT)

        mid = ttk.Frame(self)
        mid.pack(fill=tk.X, padx=12, pady=10)
        ttk.Label(mid, text="Buildings:").pack(side=tk.LEFT)
        self.buildings_list = tk.Listbox(mid, selectmode=tk.MULTIPLE, height=6)
        self.buildings_list.pack(fill=tk.X, expand=True)
        self._load_buildings()

        self.results = ResultsTable(self)
        self.results.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def _load_buildings(self):
        cols, rows = fetch_all("SELECT building_id, name FROM Building ORDER BY name")
        self.buildings_list.delete(0, tk.END)
        for r in rows:
            self.buildings_list.insert(tk.END, f"{r[0]} - {r[1]}")

    def _make_dt_picker(self, parent, var: tk.StringVar):
        wrap = ttk.Frame(parent)
        wrap.pack(side=tk.LEFT)
        # Date spinboxes
        y = tk.Spinbox(wrap, from_=2000, to=2100, width=4)
        m = tk.Spinbox(wrap, from_=1, to=12, width=2)
        d = tk.Spinbox(wrap, from_=1, to=31, width=2)
        h = tk.Spinbox(wrap, from_=0, to=23, width=2)
        mi = tk.Spinbox(wrap, from_=0, to=59, width=2)
        for w in (y, m, d, h, mi):
            w.configure(justify='center')
        y.pack(side=tk.LEFT)
        ttk.Label(wrap, text='-').pack(side=tk.LEFT)
        m.pack(side=tk.LEFT)
        ttk.Label(wrap, text='-').pack(side=tk.LEFT)
        d.pack(side=tk.LEFT)
        ttk.Label(wrap, text=' ').pack(side=tk.LEFT)
        h.pack(side=tk.LEFT)
        ttk.Label(wrap, text=':').pack(side=tk.LEFT)
        mi.pack(side=tk.LEFT)
        def set_now():
            now = datetime.now()
            y.delete(0, tk.END); y.insert(0, now.year)
            m.delete(0, tk.END); m.insert(0, f"{now.month:02d}")
            d.delete(0, tk.END); d.insert(0, f"{now.day:02d}")
            h.delete(0, tk.END); h.insert(0, f"{now.hour:02d}")
            mi.delete(0, tk.END); mi.insert(0, f"{now.minute:02d}")
            var.set(f"{y.get()}-{int(m.get()):02d}-{int(d.get()):02d} {int(h.get()):02d}:{int(mi.get()):02d}")
        def apply():
            var.set(f"{y.get()}-{int(m.get()):02d}-{int(d.get()):02d} {int(h.get()):02d}:{int(mi.get()):02d}")
        ttk.Button(wrap, text='Now', command=set_now).pack(side=tk.LEFT, padx=4)
        ttk.Button(wrap, text='OK', command=apply).pack(side=tk.LEFT)
        # initialize empty
        return wrap

    def search(self):
        try:
            from_dt = datetime.strptime(self.from_var.get().strip(), "%Y-%m-%d %H:%M")
            to_dt = datetime.strptime(self.to_var.get().strip(), "%Y-%m-%d %H:%M")
        except Exception:
            messagebox.showwarning("Input", "Use datetime format YYYY-MM-DD HH:MM")
            return
        sel = [self.buildings_list.get(i) for i in self.buildings_list.curselection()]
        building_ids = [int(s.split(" - ")[0]) for s in sel]
        if not building_ids:
            messagebox.showwarning("Input", "Select at least one building")
            return
        placeholders = ",".join(["%s"] * len(building_ids))
        # Overlap condition and cleaning activities only
        sql = f"""
        SELECT a.activity_id,
               a.`type`,
               v.location_label,
               a.scheduled_start,
               a.scheduled_end,
               CASE WHEN EXISTS (
                 SELECT 1 FROM ActivityChemical ac
                 JOIN Chemical c ON c.chemical_id = ac.chemical_id
                 WHERE ac.activity_id = a.activity_id AND c.hazard_class IN ('MEDIUM','HIGH')
               ) THEN 'YES' ELSE 'NO' END AS harmful_chemicals
        FROM Activity a
        LEFT JOIN v_activity_location v ON v.activity_id = a.activity_id
        WHERE a.`type` = 'CLEANING'
          AND a.status IN ('SCHEDULED','ONGOING')
          AND a.scheduled_start < %s AND a.scheduled_end > %s
          AND (
            (a.location_building_id IN ({placeholders})) OR
            (a.location_level_id IS NOT NULL AND (SELECT building_id FROM Level WHERE level_id=a.location_level_id) IN ({placeholders})) OR
            (a.location_room_no IS NOT NULL AND a.location_level_id IS NOT NULL AND (SELECT l.building_id FROM Room r JOIN Level l ON l.level_id=r.level_id WHERE r.level_id=a.location_level_id AND r.room_no=a.location_room_no) IN ({placeholders}))
          )
        ORDER BY a.scheduled_start
        """
        params = [to_dt, from_dt] + building_ids + building_ids + building_ids
        cols, rows = fetch_all(sql, tuple(params))
        self.results.set_data(cols, rows)


class ReportsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=10)
        ttk.Button(top, text="Generate Workers by Activity Type & Location", style="Primary.TButton", command=self.generate).pack(side=tk.LEFT)
        group = ttk.LabelFrame(self, text="Report")
        group.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.results = ResultsTable(group)
        self.results.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def generate(self):
        sql = """
        SELECT a.`type`,
               CASE 
                 WHEN a.location_room_no IS NOT NULL THEN 'ROOM'
                 WHEN a.location_level_id IS NOT NULL THEN 'LEVEL'
                 WHEN a.location_building_id IS NOT NULL THEN 'BUILDING'
                 ELSE 'NONE'
               END AS location_type,
               COUNT(DISTINCT asg.emp_id) AS workers_count,
               COUNT(DISTINCT a.activity_id) AS activities_count
        FROM Activity a
        LEFT JOIN Assignment asg ON asg.activity_id = a.activity_id
        GROUP BY a.`type`, 
                 CASE 
                   WHEN a.location_room_no IS NOT NULL THEN 'ROOM'
                   WHEN a.location_level_id IS NOT NULL THEN 'LEVEL'
                   WHEN a.location_building_id IS NOT NULL THEN 'BUILDING'
                   ELSE 'NONE'
                 END
        ORDER BY a.`type`, location_type
        """
        cols, rows = fetch_all(sql)
        self.results.set_data(cols, rows)


class ResultsTable(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vsb.set)
        self.vsb.place(relx=1.0, rely=0, relheight=1.0, anchor='ne')
        self._data = []
        self._columns = []
        self._sort_state: dict[str, bool] = {}
        self._sorted_col: str | None = None

        # Right-click menu
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Copy Row", command=self._copy_row)
        self.menu.add_command(label="Copy Cell", command=self._copy_cell)
        self.menu.add_separator()
        self.menu.add_command(label="💾 Export CSV...", command=self._export_csv)
        self.tree.bind("<Button-3>", self._open_menu)
        self.tree.bind('<Motion>', self._on_motion)
        self._last_hover = None

    def set_data(self, columns: list[str], rows: list[tuple]):
        for c in self.tree.get_children():
            self.tree.delete(c)
        self._columns = columns
        self._data = rows
        self.tree["columns"] = columns
        for col in columns:
            label = self._heading_label(col)
            self.tree.heading(col, text=label, command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=120, anchor=tk.W, stretch=True)
        # Insert rows with zebra striping
        for idx, r in enumerate(rows):
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree.insert('', tk.END, values=r, tags=(tag,))
        # Configure tag colors
        self.tree.tag_configure('odd', background='#f7f7f7')
        self.tree.tag_configure('even', background='#ffffff')
        # Auto-size columns up to a max width
        self._autosize_columns(columns, rows)

    def _autosize_columns(self, columns: list[str], rows: list[tuple]):
        font = tkfont.nametofont("TkDefaultFont")
        max_width = 320
        padding = 24
        # Calculate width based on sampled data
        samples = rows[:200]
        for i, col in enumerate(columns):
            texts = [str(col)] + [str(r[i]) if i < len(r) and r[i] is not None else '' for r in samples]
            width_px = max(font.measure(t) for t in texts) + padding
            self.tree.column(col, width=min(max(100, width_px), max_width))

    def _sort_by(self, column: str):
        if column not in self._columns:
            return
        idx = self._columns.index(column)
        asc = not self._sort_state.get(column, False)
        def sort_key(row):
            val = row[idx]
            # Try to sort numbers/datetimes if possible
            try:
                return float(val)
            except Exception:
                try:
                    return datetime.fromisoformat(str(val))
                except Exception:
                    return str(val)
        sorted_rows = sorted(self._data, key=sort_key, reverse=asc)
        self._sort_state[column] = asc
        self._sorted_col = column
        self.set_data(self._columns, sorted_rows)

    def _heading_label(self, col: str) -> str:
        if self._sorted_col == col:
            return f"{col} {'▼' if self._sort_state.get(col, False) else '▲'}"
        return col

    def _open_menu(self, event):
        try:
            row_id = self.tree.identify_row(event.y)
            if row_id:
                self.tree.selection_set(row_id)
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _on_motion(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id != self._last_hover:
            if self._last_hover:
                # remove hover tag
                cur_tags = list(self.tree.item(self._last_hover, 'tags'))
                if 'hover' in cur_tags:
                    cur_tags.remove('hover')
                    self.tree.item(self._last_hover, tags=tuple(cur_tags))
            if row_id:
                tags = list(self.tree.item(row_id, 'tags'))
                if 'hover' not in tags:
                    tags.append('hover')
                self.tree.item(row_id, tags=tuple(tags))
            self._last_hover = row_id
            self.tree.tag_configure('hover', background='#eef2ff')

    def _copy_row(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], 'values')
        text = '\t'.join(str(v) for v in values)
        self.clipboard_clear()
        self.clipboard_append(text)

    def _copy_cell(self):
        sel = self.tree.selection()
        if not sel:
            return
        row = self.tree.item(sel[0], 'values')
        # Identify column under mouse if possible; fallback to first
        # Treeview lacks direct cell selection; copy first column
        val = row[0] if row else ''
        self.clipboard_clear()
        self.clipboard_append(str(val))

    def _export_csv(self):
        import csv
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV Files', '*.csv')])
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self._columns)
                for row in self._data:
                    writer.writerow(row)
            messagebox.showinfo("Export", f"Exported to {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()


