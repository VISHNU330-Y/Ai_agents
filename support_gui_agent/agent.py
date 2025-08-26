import os
import json
import tkinter as tk
from tkinter import messagebox, filedialog
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import asyncio
import nest_asyncio
import traceback
import google.generativeai as genai

# ----------------- Setup -----------------
nest_asyncio.apply()
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

HISTORY_FILE = "ticket_history.json"

# ----------------- History helpers -----------------
def save_to_history(ticket, category, reply, actions):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticket": ticket,
        "category": category,
        "reply": reply,
        "actions": actions,
    }

    history = load_history()
    history.append(entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def export_history(fmt="json"):
    history = load_history()
    if not history:
        messagebox.showinfo("Export", "No history to export.")
        return

    if fmt == "json":
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if file:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=4)
    elif fmt == "csv":
        df = pd.DataFrame(history)
        file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if file:
            df.to_csv(file, index=False)

    messagebox.showinfo("Export", f"History exported to {file}")

# ----------------- Next actions -----------------
def suggest_actions(category):
    actions = {
        "Bug": "Log into bug tracker . Assign to dev team.",
        "Feature Request": "Add to product roadmap. Discuss in next sprint planning.",
        "Question": "Redirect to FAQ or assign to support staff.",
    }
    return actions.get(category, "Review manually.")

# ----------------- run_live (fixed) -----------------
# Reuse one global event loop instead of closing it each time
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
        # recreate loop if somehow broken
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        return new_loop.run_until_complete(_collect())

# ----------------- Response parsing -----------------
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

# ----------------- GUI actions -----------------
def classify_ticket():
    ticket = entry.get("1.0", tk.END).strip()
    if not ticket:
        messagebox.showwarning("Input Error", "Please enter a ticket.")
        return

    prompt = f"""Classify the following support ticket into one of:
- Bug
- Feature Request
- Question

Respond ONLY in JSON format with:
{{"category": "...", "reply": "..."}}

Ticket: "{ticket}"
"""

    try:
        raw = run_live_sync(prompt, timeout_seconds=60)
        data = parse_response(raw)
        category = data.get("category", "Unknown")
        reply = data.get("reply", raw)
    except Exception as e:
        traceback.print_exc()
        category = "Error"
        reply = f"Error while calling model: {e}"

    actions = suggest_actions(category if category else "Unparsed")
    save_to_history(ticket, category, reply, actions)

    result_label.config(text=f"Category: {category}", fg=color_for_category(category))
    reply_text.config(state="normal")
    reply_text.delete("1.0", tk.END)
    reply_text.insert(tk.END, reply + "\n\nNext Steps: " + actions)
    reply_text.config(state="disabled")

def search_history():
    keyword = search_entry.get().lower().strip()
    history = load_history()
    results = [h for h in history if keyword in h["ticket"].lower() or keyword in h["reply"].lower()]

    reply_text.config(state="normal")
    reply_text.delete("1.0", tk.END)
    if results:
        for r in results:
            reply_text.insert(
                tk.END,
                f"[{r['timestamp']}] {r['ticket']} → {r['category']}\nReply: {r['reply']}\nActions: {r['actions']}\n\n"
            )
    else:
        reply_text.insert(tk.END, "No matching history found.")
    reply_text.config(state="disabled")

def color_for_category(category):
    return {
        "Bug": "red",
        "Feature Request": "blue",
        "Question": "green",
    }.get(category, "black")

# ----------------- GUI -----------------
root = tk.Tk()
root.title("AI Support Ticket Classifier")
root.geometry("700x600")

tk.Label(root, text="Enter Support Ticket:").pack(pady=5)
entry = tk.Text(root, height=5, width=80)
entry.pack(pady=5)

tk.Button(root, text="Classify", command=classify_ticket, bg="lightgreen").pack(pady=5)

result_label = tk.Label(root, text="Category: None", font=("Arial", 14, "bold"))
result_label.pack(pady=5)

reply_text = tk.Text(root, height=15, width=80, state="disabled", wrap="word")
reply_text.pack(pady=5)

tk.Label(root, text="Search Ticket History:").pack(pady=5)
search_entry = tk.Entry(root, width=50)
search_entry.pack(pady=5)
tk.Button(root, text="Search", command=search_history).pack(pady=5)

tk.Button(root, text="Export History (JSON)", command=lambda: export_history("json")).pack(pady=5)
tk.Button(root, text="Export History (CSV)", command=lambda: export_history("csv")).pack(pady=5)

root.mainloop()
