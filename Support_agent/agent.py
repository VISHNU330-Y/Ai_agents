import os
import json
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import google.generativeai as genai
import gradio as gr
import plotly.express as px
import plotly.graph_objects as go

# ----------------- Setup -----------------
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")
HISTORY_FILE = "ticket_history.json"

# ----------------- History helpers -----------------
def save_to_history(ticket, category, reply, actions, priority="Medium"):
    entry = {
        "id": len(load_history()) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticket": ticket,
        "category": category,
        "priority": priority,
        "reply": reply,
        "actions": actions,
        "status": "Open"
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
        return "⚠️ No history to export.", ""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if fmt == "json":
        filename = f"ticket_history_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
        return f"✅ Exported as {filename}", filename
    elif fmt == "csv":
        filename = f"ticket_history_{timestamp}.csv"
        df = pd.DataFrame(history)
        df.to_csv(filename, index=False)
        return f"✅ Exported as {filename}", filename

def get_analytics():
    history = load_history()
    if not history:
        return None, "📊 No data available for analytics"
    
    df = pd.DataFrame(history)
    
    # Category distribution
    cat_counts = df['category'].value_counts()
    fig_pie = px.pie(values=cat_counts.values, names=cat_counts.index, 
                     title="Ticket Distribution by Category",
                     color_discrete_map={
                         'Bug': '#ff4444',
                         'Feature Request': '#4444ff', 
                         'Question': '#44ff44',
                         'Unparsed': '#888888'
                     })
    fig_pie.update_layout(height=400, font_size=12)
    
    # Timeline chart
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    daily_counts = df.groupby(['date', 'category']).size().reset_index(name='count')
    fig_timeline = px.line(daily_counts, x='date', y='count', color='category',
                          title="Ticket Volume Over Time")
    fig_timeline.update_layout(height=400)
    
    # Stats summary
    total_tickets = len(history)
    today_tickets = len(df[df['date'] == datetime.now().date()])
    stats = f"""
    📈 **Analytics Summary**
    - **Total Tickets**: {total_tickets}
    - **Today's Tickets**: {today_tickets}
    - **Most Common**: {cat_counts.index[0] if len(cat_counts) > 0 else 'N/A'}
    - **Categories**: {len(cat_counts)} types
    """
    
    return fig_pie, fig_timeline, stats

# ----------------- Enhanced actions -----------------
def suggest_actions(category, priority="Medium"):
    base_actions = {
        "Bug": "🐛 Log into bug tracker → Assign to dev team → Set priority",
        "Feature Request": "💡 Add to product roadmap → Schedule sprint planning → Stakeholder review", 
        "Question": "❓ Check FAQ → Assign to support → Provide documentation"
    }
    
    priority_actions = {
        "High": " → ⚠️ URGENT: Escalate immediately",
        "Medium": " → 📋 Standard processing",
        "Low": " → 📅 Schedule for next cycle"
    }
    
    base = base_actions.get(category, "🔍 Manual review required")
    return base + priority_actions.get(priority, "")

def determine_priority(ticket_text, category):
    """Simple priority detection based on keywords"""
    high_priority_keywords = ["urgent", "critical", "broken", "down", "crash", "error", "bug", "not working"]
    low_priority_keywords = ["feature", "suggestion", "improvement", "nice to have", "question"]
    
    text_lower = ticket_text.lower()
    
    if category == "Bug" and any(word in text_lower for word in ["critical", "urgent", "crash", "down"]):
        return "High"
    elif any(word in text_lower for word in high_priority_keywords):
        return "High" 
    elif any(word in text_lower for word in low_priority_keywords):
        return "Low"
    else:
        return "Medium"

def category_styling(category, priority="Medium"):
    colors = {
        "Bug": "#ff4444",
        "Feature Request": "#4444ff", 
        "Question": "#44ff44",
        "Unparsed": "#888888",
        "Error": "#ff8800"
    }
    
    priority_icons = {
        "High": "🔴",
        "Medium": "🟡", 
        "Low": "🟢"
    }
    
    color = colors.get(category, "#666666")
    icon = priority_icons.get(priority, "⚪")
    
    return f"""
    <div style="background: linear-gradient(135deg, {color}15, {color}05); 
                border-left: 4px solid {color}; 
                padding: 12px; 
                border-radius: 8px; 
                margin: 8px 0;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 18px;">{icon}</span>
            <span style="color: {color}; font-weight: bold; font-size: 16px;">{category}</span>
            <span style="color: #666; font-size: 12px;">({priority} Priority)</span>
        </div>
    </div>
    """

# ----------------- Enhanced ticket classification -----------------
def classify_ticket(ticket):
    ticket = ticket.strip()
    if not ticket:
        return "⚠️ Please enter a ticket description.", "", "", "", "", None, None, ""

    prompt = f"""Classify this support ticket and provide a helpful response:

Categories: Bug, Feature Request, Question

Ticket: "{ticket}"

Respond in JSON format:
{{
    "category": "...",
    "reply": "Professional response addressing the user's concern",
    "confidence": 0.95
}}
"""
    
    try:
        res = model.generate_content(prompt)
        raw = res.text or ""
        
        # Clean JSON response
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
            
        try:
            data = json.loads(raw.strip())
            category = data.get("category", "Unparsed")
            reply = data.get("reply", raw)
            confidence = data.get("confidence", 0.8)
        except Exception:
            category = "Unparsed"
            reply = raw
            confidence = 0.5
            
    except Exception as e:
        category = "Error"
        reply = f"❌ Error calling AI model: {e}"
        confidence = 0.0

    # Determine priority
    priority = determine_priority(ticket, category)
    
    # Get actions
    actions = suggest_actions(category, priority)
    
    # Save to history
    save_to_history(ticket, category, reply, actions, priority)
    
    # Style the output
    styled_category = category_styling(category, priority)
    
    # Get updated analytics
    pie_chart, timeline_chart, analytics_text = get_analytics()
    
    # Format history for display
    history = load_history()
    recent_history = history[-5:] if history else []  # Show last 5
    
    history_display = ""
    for entry in reversed(recent_history):
        status_icon = "🟢" if entry.get('status') == 'Open' else "🔵"
        history_display += f"""
**#{entry.get('id', 'N/A')} {status_icon}** - {entry.get('timestamp', 'N/A')}
**Category**: {entry.get('category', 'N/A')} | **Priority**: {entry.get('priority', 'N/A')}
**Ticket**: {entry.get('ticket', 'N/A')[:100]}...
---
"""
    
    return (
        styled_category,
        reply, 
        actions,
        history_display,
        "",  # Clear input
        pie_chart,
        timeline_chart,
        analytics_text
    )

def create_custom_css():
    return """
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .header-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 30px;
        text-align: center;
    }
    
    .stats-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 10px 0;
    }
    
    .input-section {
        background: #f8f9fa;
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    
    .results-section {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    """

# ----------------- Gradio Interface -----------------
with gr.Blocks(css=create_custom_css(), theme=gr.themes.Soft(), title="AI Support Ticket Classifier") as demo:
    
    # Header
    gr.HTML("""
    <div class="header-section">
        <h1>🎫 AI Support Ticket Classifier</h1>
        <p>Intelligent ticket classification and routing system powered by SPARK SQUAD</p>
    </div>
    """)
    
    with gr.Row():
        # Left column - Input and Classification
        with gr.Column(scale=2):
            gr.HTML("<div class='input-section'>")
            gr.Markdown("### 📝 Submit New Ticket")
            
            with gr.Group():
                ticket_input = gr.Textbox(
                    label="Ticket Description", 
                    placeholder="Describe the issue, feature request, or question in detail...",
                    lines=6,
                    show_label=True
                )
                
                with gr.Row():
                    classify_btn = gr.Button(
                        "🚀 Classify Ticket", 
                        variant="primary", 
                        size="lg"
                    )
                    clear_btn = gr.Button("🗑️ Clear", variant="secondary")
            
            gr.HTML("</div>")
            
            # Results section
            gr.HTML("<div class='results-section'>")
            gr.Markdown("### 📊 Classification Results")
            
            category_output = gr.HTML(label="Category & Priority")
            
            with gr.Row():
                with gr.Column():
                    reply_output = gr.Textbox(
                        label="📧 Suggested Reply", 
                        lines=6,
                        show_copy_button=True
                    )
                with gr.Column():
                    actions_output = gr.Textbox(
                        label="📋 Next Steps", 
                        lines=6,
                        show_copy_button=True
                    )
            gr.HTML("</div>")
        
        # Right column - Analytics and History
        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.TabItem("📈 Analytics"):
                    analytics_text = gr.Markdown("📊 Loading analytics...")
                    pie_chart = gr.Plot(label="Category Distribution")
                    timeline_chart = gr.Plot(label="Timeline")
                
                with gr.TabItem("📚 Recent History"):
                    history_output = gr.Markdown("📋 Recent tickets will appear here...")
                    
                    with gr.Row():
                        export_json_btn = gr.Button("📄 Export JSON", size="sm")
                        export_csv_btn = gr.Button("📊 Export CSV", size="sm")
                    
                    export_status = gr.Textbox(
                        label="Export Status",
                        lines=2,
                        visible=False
                    )

    # Event handlers
    classify_btn.click(
        classify_ticket,
        inputs=[ticket_input],
        outputs=[
            category_output, 
            reply_output, 
            actions_output, 
            history_output, 
            ticket_input,
            pie_chart,
            timeline_chart,
            analytics_text
        ]
    )
    
    clear_btn.click(
        lambda: ("", "", "", "", ""),
        outputs=[ticket_input, category_output, reply_output, actions_output, history_output]
    )
    
    def handle_export(fmt):
        status, filename = export_history(fmt)
        return status, gr.update(visible=True)
    
    export_json_btn.click(
        lambda: handle_export("json"),
        outputs=[export_status, export_status]
    )
    
    export_csv_btn.click(
        lambda: handle_export("csv"), 
        outputs=[export_status, export_status]
    )
    
    # Load initial analytics
    demo.load(
        get_analytics,
        outputs=[pie_chart, timeline_chart, analytics_text]
    )


demo.launch()
