import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import traceback
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import asyncio
import nest_asyncio
nest_asyncio.apply()
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai

API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

HISTORY_FILE = "ticket_history.json"
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".ai_ticket_classifier_settings.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_to_history(ticket, category, reply, actions):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticket": ticket,
        "category": category,
        "reply": reply,
        "actions": actions,
    }
    history = load_history()
    history.insert(0, entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

def export_history(fmt="json", parent=None):
    history = load_history()
    if not history:
        messagebox.showinfo("Export", "No history to export.")
        return

    if fmt == "json":
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], parent=parent)
        if file:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=4)
            messagebox.showinfo("Export", f"History exported to {file}")
    elif fmt == "csv":
        df = pd.DataFrame(history)
        file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], parent=parent)
        if file:
            df.to_csv(file, index=False)
            messagebox.showinfo("Export", f"History exported to {file}")

def suggest_actions(category):
    actions = {
        "Bug": "Log into bug tracker. Assign to dev team.",
        "Feature Request": "Add to product roadmap. Discuss in next sprint planning.",
        "Question": "Redirect to FAQ or assign to support staff.",
    }
    return actions.get(category, "Review manually.")

_loop = asyncio.get_event_loop()

def run_live_sync(prompt: str, timeout_seconds: int | None = None) -> str:
    async def _collect():
        try:
            res = await model.generate_content_async(prompt)
            return res.text or ""
        except Exception as e:
            return f"Error: {e}"

    try:
        if timeout_seconds:
            return _loop.run_until_complete(asyncio.wait_for(_collect(), timeout_seconds))
        else:
            return _loop.run_until_complete(_collect())
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        return new_loop.run_until_complete(_collect())
    except Exception as e:
        return f"Error: {e}"

def parse_response(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return {"category": "Unparsed", "reply": ""}
    try:
        return json.loads(raw)
    except Exception:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            return {"category": "Unparsed", "reply": raw}

def color_for_category(category):
    return {
        "Bug": "#e74c3c",
        "Feature Request": "#3498db",
        "Question": "#2ecc71",
    }.get(category, "#333333")

def draw_gradient(canvas, color1, color2):
    canvas.delete("gradient")
    canvas.update_idletasks()
    width = max(canvas.winfo_width(), 2)
    height = max(canvas.winfo_height(), 2)
    (r1, g1, b1) = canvas.winfo_rgb(color1)
    (r2, g2, b2) = canvas.winfo_rgb(color2)
    r_ratio = float(r2 - r1) / height
    g_ratio = float(g2 - g1) / height
    b_ratio = float(b2 - b1) / height
    for i in range(height):
        nr = int(r1 + (r_ratio * i)) // 256
        ng = int(g1 + (g_ratio * i)) // 256
        nb = int(b1 + (b_ratio * i)) // 256
        color = f"#{nr:02x}{ng:02x}{nb:02x}"
        canvas.create_line(0, i, width, i, fill=color, tags=("gradient",))
    canvas.lower("gradient")

class AdvancedTicketGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Support Ticket Classifier — Advanced")
        self.geometry("900x680")
        self.minsize(820, 560)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.executor = ThreadPoolExecutor(max_workers=3)
        self.settings = self._load_settings()
        self.bg_canvas = tk.Canvas(self, highlightthickness=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)
        self._win_id = None
        self.bg_canvas.bind("<Configure>", self._on_canvas_configure)

        self.main_frame = ttk.Frame(self.bg_canvas)
        self._win_id = self.bg_canvas.create_window((0, 0), window=self.main_frame, anchor="nw",
                                                    width=self.winfo_width(), height=self.winfo_height())

        self._build_ui()
        self._apply_theme(self.settings.get("theme", "light"))

        draw_gradient(self.bg_canvas, self.settings.get("bg_start", "#6dd5ed"), self.settings.get("bg_end", "#2193b0"))

        
        self._refresh_history()
        self._refresh_stats()

    
    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # defaults
        return {"theme": "light", "bg_start": "#6dd5ed", "bg_end": "#2193b0"}

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    
    def _on_canvas_configure(self, event):
        
        draw_gradient(self.bg_canvas, self.settings.get("bg_start", "#6dd5ed"), self.settings.get("bg_end", "#2193b0"))
        
        try:
            self.bg_canvas.itemconfigure(self._win_id, width=event.width, height=event.height)
        except Exception:
            pass

    
    def _build_ui(self):
        
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(6, 0))

        ttk.Button(toolbar, text="Classify", command=self._on_classify_click).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Reclassify Selected", command=self._reclassify_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Export JSON", command=lambda: export_history("json", parent=self)).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Export CSV", command=lambda: export_history("csv", parent=self)).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Clear History", command=self._clear_history_confirm).pack(side=tk.LEFT, padx=4)

        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        
        tab_classify = ttk.Frame(self.notebook)
        self.notebook.add(tab_classify, text="Classify")

        ttk.Label(tab_classify, text="Enter Support Ticket:").pack(anchor=tk.W, padx=8, pady=(8, 0))
        self.ticket_entry = tk.Text(tab_classify, height=6, wrap="word")
        self.ticket_entry.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(tab_classify, text="Classify Ticket", command=self._on_classify_click).pack(padx=8, pady=4)

        self.result_label = ttk.Label(tab_classify, text="Category: None", font=("Arial", 12, "bold"))
        self.result_label.pack(anchor=tk.W, padx=8, pady=(4, 0))

        ttk.Label(tab_classify, text="Reply / Next Steps:").pack(anchor=tk.W, padx=8, pady=(6, 0))
        self.reply_text = tk.Text(tab_classify, height=10, state="disabled", wrap="word")
        self.reply_text.pack(fill=tk.BOTH, padx=8, pady=6, expand=True)

        
        tab_history = ttk.Frame(self.notebook)
        self.notebook.add(tab_history, text="History")

        search_frame = ttk.Frame(tab_history)
        search_frame.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(search_frame, text="Go", command=self._on_search).pack(side=tk.LEFT, padx=4)
        ttk.Button(search_frame, text="Reset", command=self._on_search_reset).pack(side=tk.LEFT, padx=4)

        cols = ("timestamp", "category", "ticket_preview")
        self.tree = ttk.Treeview(tab_history, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("category", text="Category")
        self.tree.heading("ticket_preview", text="Ticket (preview)")
        self.tree.column("timestamp", width=150, anchor=tk.W)
        self.tree.column("category", width=120, anchor=tk.W)
        self.tree.column("ticket_preview", width=400, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_history_select)

        details_frame = ttk.Frame(tab_history)
        details_frame.pack(fill=tk.BOTH, padx=8, pady=(0,8), expand=False)
        ttk.Label(details_frame, text="Selected Ticket Details:").pack(anchor=tk.W)
        self.detail_text = tk.Text(details_frame, height=8, state="disabled", wrap="word")
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        
        tab_stats = ttk.Frame(self.notebook)
        self.notebook.add(tab_stats, text="Stats")
        self.stats_frame = ttk.Frame(tab_stats)
        self.stats_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        ttk.Button(tab_stats, text="Refresh Stats", command=self._refresh_stats).pack(pady=4)

        
        tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(tab_settings, text="Settings")
        ttk.Label(tab_settings, text="Theme:").pack(anchor=tk.W, padx=8, pady=(8,0))
        theme_frame = ttk.Frame(tab_settings)
        theme_frame.pack(anchor=tk.W, padx=8, pady=6)
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        ttk.Radiobutton(theme_frame, text="Light", value="light", variable=self.theme_var, command=self._on_theme_change).pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(theme_frame, text="Dark", value="dark", variable=self.theme_var, command=self._on_theme_change).pack(side=tk.LEFT, padx=6)

        ttk.Label(tab_settings, text="Gradient Start Color (hex):").pack(anchor=tk.W, padx=8, pady=(8,0))
        self.bgstart_var = tk.StringVar(value=self.settings.get("bg_start", "#6dd5ed"))
        ttk.Entry(tab_settings, textvariable=self.bgstart_var).pack(anchor=tk.W, padx=8, pady=4)
        ttk.Label(tab_settings, text="Gradient End Color (hex):").pack(anchor=tk.W, padx=8, pady=(8,0))
        self.bgend_var = tk.StringVar(value=self.settings.get("bg_end", "#2193b0"))
        ttk.Entry(tab_settings, textvariable=self.bgend_var).pack(anchor=tk.W, padx=8, pady=4)
        ttk.Button(tab_settings, text="Apply Gradient", command=self._apply_gradient_from_settings).pack(padx=8, pady=8)
        ttk.Button(tab_settings, text="Save Settings", command=self._save_settings_from_ui).pack(padx=8, pady=4)

        
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status.pack(side=tk.BOTTOM, fill=tk.X)

    
    def _apply_theme(self, theme: str):
        style = ttk.Style(self)
        try:
            style.theme_use("default")
        except Exception:
            pass
        if theme == "dark":
            style.configure("TFrame", background="#1f1f1f")
            style.configure("TLabel", background="#1f1f1f", foreground="#e6e6e6")
            style.configure("TButton", background="#333333", foreground="#ffffff")
            self.reply_text.configure(bg="#222222", fg="#e6e6e6", insertbackground="#e6e6e6")
            self.ticket_entry.configure(bg="#222222", fg="#e6e6e6", insertbackground="#e6e6e6")
            self.detail_text.configure(bg="#222222", fg="#e6e6e6", insertbackground="#e6e6e6")
        else:
            style.configure("TFrame", background="white")
            style.configure("TLabel", background="white", foreground="black")
            style.configure("TButton", background="#f0f0f0", foreground="black")
            self.reply_text.configure(bg="white", fg="black", insertbackground="black")
            self.ticket_entry.configure(bg="white", fg="black", insertbackground="black")
            self.detail_text.configure(bg="white", fg="black", insertbackground="black")

        self.settings["theme"] = theme
        self._save_settings()

    def _on_theme_change(self):
        t = self.theme_var.get()
        self._apply_theme(t)
        self._log_status(f"Theme set to {t}")

    def _apply_gradient_from_settings(self):
        start = self.bgstart_var.get().strip() or "#6dd5ed"
        end = self.bgend_var.get().strip() or "#2193b0"
        self.settings["bg_start"] = start
        self.settings["bg_end"] = end
        draw_gradient(self.bg_canvas, start, end)
        self._save_settings()
        self._log_status("Applied gradient")

    def _save_settings_from_ui(self):
        self.settings["theme"] = self.theme_var.get()
        self.settings["bg_start"] = self.bgstart_var.get().strip() or "#6dd5ed"
        self.settings["bg_end"] = self.bgend_var.get().strip() or "#2193b0"
        self._save_settings()
        self._log_status("Settings saved")

    def _log_status(self, msg: str):
        self.status_var.set(msg)
        self.update_idletasks()


    def _on_classify_click(self):
        ticket = self.ticket_entry.get("1.0", tk.END).strip()
        if not ticket:
            messagebox.showwarning("Input Error", "Please enter a ticket.")
            return
        self._log_status("Classifying...")
        
        self.executor.submit(self._classify_worker, ticket)

    def _classify_worker(self, ticket: str):
        prompt = (
            "Classify the following support ticket into one of:\n"
            "- Bug\n- Feature Request\n- Question\n\n"
            "Respond ONLY in JSON format with:\n"
            "{\"category\": \"...\", \"reply\": \"...\"}\n\n"
            f"Ticket: \"{ticket}\"\n"
        )
        try:
            raw = run_live_sync(prompt, timeout_seconds=60)
            data = parse_response(raw)
            category = data.get("category", "Unparsed")
            reply = data.get("reply", raw)
        except Exception as e:
            traceback.print_exc()
            category = "Error"
            reply = f"Error while calling model: {e}"

        actions = suggest_actions(category)
        save_to_history(ticket, category, reply, actions)
        
        self.after(0, lambda: self._on_classify_result(category, reply, actions))

    def _on_classify_result(self, category, reply, actions):
        self.result_label.config(text=f"Category: {category}", foreground=color_for_category(category))
        self.reply_text.config(state="normal")
        self.reply_text.delete("1.0", tk.END)
        self.reply_text.insert(tk.END, reply + "\n\nNext Steps: " + actions)
        self.reply_text.config(state="disabled")
        self._log_status(f"Last classified: {category}")
        self._refresh_history()
        self._refresh_stats()

    
    def _refresh_history(self, filter_keyword: str | None = None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        history = load_history()
        for idx, e in enumerate(history):
            if filter_keyword:
                k = filter_keyword.lower()
                if k not in e.get("ticket", "").lower() and k not in e.get("reply", "").lower():
                    continue
            preview = (e.get("ticket") or "")[:120].replace("\n", " ")
            self.tree.insert("", tk.END, iid=str(idx), values=(e.get("timestamp"), e.get("category"), preview))

    def _on_search(self):
        key = self.search_var.get().strip()
        self._refresh_history(filter_keyword=key)
        self._log_status("Filtered history" if key else "Ready")

    def _on_search_reset(self):
        self.search_var.set("")
        self._refresh_history()
        self._log_status("Ready")

    def _on_history_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        history = load_history()
        try:
            idx = int(iid)
            if idx < len(history):
                e = history[idx]
                self.detail_text.config(state="normal")
                self.detail_text.delete("1.0", tk.END)
                self.detail_text.insert(tk.END, f"[{e.get('timestamp')}]\n")
                self.detail_text.insert(tk.END, f"Ticket:\n{e.get('ticket')}\n\n")
                self.detail_text.insert(tk.END, f"Category: {e.get('category')}\n\n")
                self.detail_text.insert(tk.END, f"Reply:\n{e.get('reply')}\n\n")
                self.detail_text.insert(tk.END, f"Actions:\n{e.get('actions')}\n")
                self.detail_text.config(state="disabled")
        except Exception:
            pass

    def _reclassify_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Reclassify", "Please select a history item to reclassify.")
            return
        iid = sel[0]
        history = load_history()
        try:
            idx = int(iid)
            ticket = history[idx].get("ticket", "")
            self.notebook.select(0)  
            self.ticket_entry.delete("1.0", tk.END)
            self.ticket_entry.insert(tk.END, ticket)
            self._on_classify_click()
        except Exception:
            messagebox.showerror("Error", "Could not reclassify selected item.")

    def _clear_history_confirm(self):
        if messagebox.askyesno("Confirm", "Clear all history? This cannot be undone."):
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception:
                pass
            self._refresh_history()
            self._refresh_stats()
            self._log_status("History cleared")

    
    def _refresh_stats(self):
        for w in self.stats_frame.winfo_children():
            w.destroy()

        history = load_history()
        if not history:
            ttk.Label(self.stats_frame, text="No history yet.").pack()
            return

        df = pd.DataFrame(history)
        counts = df["category"].value_counts()

        stats_text = ttk.Frame(self.stats_frame)
        stats_text.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        for cat, cnt in counts.items():
            lbl = ttk.Label(stats_text, text=f"{cat}: {cnt}")
            lbl.pack(anchor=tk.W)

        fig = Figure(figsize=(4,3), tight_layout=True)
        ax = fig.add_subplot(111)
        try:
            counts.plot(kind="pie", autopct="%1.1f%%", ax=ax)
            ax.set_ylabel("")
            ax.set_title("Ticket categories")
        except Exception:
            ax.clear()
            counts.plot(kind="bar", ax=ax)
            ax.set_ylabel("Count")
            ax.set_title("Ticket categories")

        canvas = FigureCanvasTkAgg(fig, master=self.stats_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

    
    def _on_close(self):
        self.settings["theme"] = self.theme_var.get() if hasattr(self, "theme_var") else self.settings.get("theme", "light")
        self.settings["bg_start"] = self.bgstart_var.get() if hasattr(self, "bgstart_var") else self.settings.get("bg_start", "#6dd5ed")
        self.settings["bg_end"] = self.bgend_var.get() if hasattr(self, "bgend_var") else self.settings.get("bg_end", "#2193b0")
        self._save_settings()
        try:
            self.executor.shutdown(wait=False)
        except Exception:
            pass
        self.destroy()

root = AdvancedTicketGUI()
root.mainloop()
