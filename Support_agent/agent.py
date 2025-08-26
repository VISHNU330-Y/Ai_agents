import os
import json
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import google.generativeai as genai
import gradio as gr

# ----------------- Setup -----------------
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
        return "No history to export."
    if fmt == "json":
        with open("ticket_history_export.json", "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
        return "Exported as ticket_history_export.json"
    elif fmt == "csv":
        df = pd.DataFrame(history)
        df.to_csv("ticket_history_export.csv", index=False)
        return "Exported as ticket_history_export.csv"

# ----------------- Next actions -----------------
def suggest_actions(category):
    actions = {
        "Bug": "Log into bug tracker. Assign to dev team.",
        "Feature Request": "Add to product roadmap. Discuss in next sprint planning.",
        "Question": "Redirect to FAQ or assign to support staff.",
    }
    return actions.get(category, "Review manually.")

def category_color(category):
    return {
        "Bug": "red",
        "Feature Request": "blue",
        "Question": "green",
        "Unparsed": "gray",
        "Error": "gray"
    }.get(category, "black")

# ----------------- Ticket classification -----------------
def classify_ticket(ticket):
    ticket = ticket.strip()
    if not ticket:
        return "Please enter a ticket.", "", "", "", ""

    prompt = f"""Classify the following support ticket into one of:
- Bug
- Feature Request
- Question

Respond ONLY in JSON format with:
{{"category": "...", "reply": "..."}}

Ticket: "{ticket}"
"""
    try:
        res = model.generate_content(prompt)
        raw = res.text or ""
        try:
            data = json.loads(raw)
            category = data.get("category", "Unparsed")
            reply = data.get("reply", raw)
        except Exception:
            category = "Unparsed"
            reply = raw
    except Exception as e:
        category = "Error"
        reply = f"Error calling AI model: {e}"

    actions = suggest_actions(category)
    save_to_history(ticket, category, reply, actions)

    colored_category = f"<span style='color:{category_color(category)}; font-weight:bold'>{category}</span>"
    history_json = json.dumps(load_history(), indent=2)
    return colored_category, reply, actions, history_json, ticket

# ----------------- Gradio Interface -----------------
with gr.Blocks() as demo:
    gr.Markdown("## AI Support Ticket Classifier")

    # Ticket input section
    with gr.Group():
        ticket_input = gr.Textbox(label="Enter Support Ticket", lines=5)
        classify_btn = gr.Button("Classify Ticket")

    # Classification result section
    with gr.Row():
        with gr.Column():
            category_output = gr.HTML(label="Category")
            actions_output = gr.Textbox(label="Next Steps", lines=3)
        with gr.Column():
            reply_output = gr.Textbox(label="Reply", lines=8)

    # History display section
    history_output = gr.Textbox(label="Ticket History", lines=10)

    # Export buttons
    with gr.Row():
        export_json_btn = gr.Button("Export History (JSON)")
        export_csv_btn = gr.Button("Export History (CSV)")

    # Button actions
    classify_btn.click(
        classify_ticket,
        inputs=[ticket_input],
        outputs=[category_output, reply_output, actions_output, history_output, ticket_input]
    )
    export_json_btn.click(lambda: export_history("json"), inputs=None, outputs=history_output)
    export_csv_btn.click(lambda: export_history("csv"), inputs=None, outputs=history_output)

demo.launch()
