import os
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
import gradio as gr
import docx2txt
import fitz  # PyMuPDF
from docx import Document as DocxWriter

# ----------------- Setup -----------------
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------- Requirement Agent -----------------
class RequirementAgent:
    def validate_input(self, raw_text: str) -> str:
        if not raw_text or not raw_text.strip():
            return "⚠️ Please provide some input text."
        if len(raw_text.split()) < 10:
            return "⚠️ Input seems too short. Add more details."
        return ""

    def process(self, raw_text: str) -> str:
        validation = self.validate_input(raw_text)
        if validation:
            return validation

        prompt = f"""
Convert the following text into clear Agile User Stories with Acceptance Criteria.
Format them in Markdown with headings (###), user story sentence, and Gherkin-style acceptance criteria.

Text:
\"\"\"{raw_text}\"\"\"
"""
        try:
            res = model.generate_content(prompt)
            return res.text.strip() if res and res.text else "⚠️ No output generated."
        except Exception as e:
            return f"❌ Error generating user stories: {e}"

    def enhance(self, stories_text: str, mode: str) -> str:
        if not stories_text.strip():
            return "⚠️ Nothing to enhance."

        prompts = {
            "shorter": f"Rewrite these user stories concisely:\n\n{stories_text}",
            "security": f"Add security-focused acceptance criteria:\n\n{stories_text}",
            "expand": f"Expand with more details, edge cases, and scenarios:\n\n{stories_text}"
        }
        try:
            res = model.generate_content(prompts[mode])
            return res.text.strip() if res and res.text else "⚠️ No enhanced output."
        except Exception as e:
            return f"❌ Error enhancing stories: {e}"

agent = RequirementAgent()

# ----------------- File extraction -----------------
def extract_text_from_file(filepath: str) -> str:
    if not filepath:
        return ""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".txt":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".docx":
            return docx2txt.process(filepath)
        elif ext == ".pdf":
            text = ""
            with fitz.open(filepath) as pdf:
                for page in pdf:
                    text += page.get_text("text") + "\n"
            return text.strip()
        else:
            return "⚠️ Unsupported file type."
    except Exception as e:
        return f"❌ Error reading file: {e}"

# ----------------- Save / Export -----------------
def save_as_md(stories_text: str) -> str:
    if not stories_text.strip():
        return None
    filename = f"user_stories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(stories_text)
    return filename

def save_as_docx(stories_text: str) -> str:
    if not stories_text.strip():
        return None
    filename = f"user_stories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    doc = DocxWriter()
    for block in stories_text.split("\n\n"):
        doc.add_paragraph(block)
    doc.save(filename)
    return filename

# ----------------- App Logic -----------------
def generate_stories(notes: str, file: str):
    text = notes or ""
    if file:
        file_text = extract_text_from_file(file)
        if file_text:
            text = file_text
    return agent.process(text)

def enhance_and_update(stories_text: str, mode: str):
    return agent.enhance(stories_text, mode)

# ----------------- Fixed CSS Styles (Clear Output) -----------------
advanced_css = """
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global Styles */
* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    margin: 0;
    padding: 0;
}

.gradio-container {
    max-width: 1400px !important;
    margin: 20px auto !important;
    padding: 20px !important;
    background: rgba(255, 255, 255, 0.1) !important;
    border-radius: 24px !important;
    backdrop-filter: blur(20px) !important;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

/* Fixed Header - No Tilt */
.header-3d {
    background: linear-gradient(135deg, #667eea, #764ba2, #f093fb, #f5576c);
    background-size: 400% 400%;
    animation: gradient-shift 8s ease infinite;
    padding: 40px;
    border-radius: 24px;
    margin-bottom: 30px;
    text-align: center;
    position: relative;
    overflow: hidden;
    box-shadow: 
        0 20px 40px rgba(102, 126, 234, 0.3),
        0 10px 20px rgba(118, 75, 162, 0.2),
        inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.header-3d::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.1) 50%, transparent 70%);
    transform: translateX(-100%);
    animation: shine 3s ease-in-out infinite;
}

.header-3d h1 {
    font-size: 3.5rem !important;
    font-weight: 700 !important;
    color: white !important;
    margin: 0 0 10px 0 !important;
    text-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    letter-spacing: -0.02em;
}

.header-3d p {
    font-size: 1.2rem !important;
    color: rgba(255, 255, 255, 0.9) !important;
    margin: 0 !important;
    font-weight: 400;
}

/* Fixed Cards - No Tilt */
.card-3d {
    background: rgba(255, 255, 255, 0.15) !important;
    border-radius: 20px !important;
    padding: 30px !important;
    backdrop-filter: blur(15px) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    box-shadow: 
        0 15px 35px rgba(0, 0, 0, 0.1),
        0 5px 15px rgba(0, 0, 0, 0.08),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.card-3d:hover {
    transform: translateY(-5px);
    box-shadow: 
        0 25px 50px rgba(0, 0, 0, 0.15),
        0 10px 20px rgba(0, 0, 0, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.card-3d::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
    transition: left 0.5s;
}

.card-3d:hover::before {
    left: 100%;
}

/* Enhanced Input Fields */
.gradio-textbox, .gradio-file {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 2px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.3s ease !important;
}

.gradio-textbox:focus, .gradio-file:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1) !important;
    transform: translateY(-2px);
}

.gradio-textbox textarea, .gradio-textbox input {
    background: transparent !important;
    color: white !important;
    border: none !important;
    font-size: 16px !important;
    font-weight: 400 !important;
}

.gradio-textbox textarea::placeholder, .gradio-textbox input::placeholder {
    color: rgba(255, 255, 255, 0.6) !important;
}

.gradio-textbox label, .gradio-file label {
    color: white !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    margin-bottom: 12px !important;
}

/* Fixed Buttons - No Tilt */
button {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    border: none !important;
    border-radius: 16px !important;
    padding: 14px 28px !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    color: white !important;
    cursor: pointer !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
    box-shadow: 
        0 8px 16px rgba(102, 126, 234, 0.3),
        0 4px 8px rgba(118, 75, 162, 0.2) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

button:hover {
    transform: translateY(-4px) !important;
    box-shadow: 
        0 15px 30px rgba(102, 126, 234, 0.4),
        0 8px 16px rgba(118, 75, 162, 0.3) !important;
    background: linear-gradient(135deg, #7c8cfc, #8a5eb8) !important;
}

button:active {
    transform: translateY(-2px) !important;
}

button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

button:hover::before {
    left: 100%;
}

/* Special Button Styles */
.btn-primary {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
}

.btn-secondary {
    background: linear-gradient(135deg, #f093fb, #f5576c) !important;
}

.btn-success {
    background: linear-gradient(135deg, #4facfe, #00f2fe) !important;
}

.btn-warning {
    background: linear-gradient(135deg, #ff9a9e, #fad0c4) !important;
}

/* FIXED OUTPUT AREA - NO BLUR, CLEAN AND READABLE */
.output-3d {
    background: rgba(30, 30, 30, 0.95) !important; /* Dark solid background */
    border: 2px solid rgba(255, 255, 255, 0.3) !important;
    border-radius: 16px !important;
    padding: 30px !important;
    min-height: 400px !important;
    max-height: 600px !important;
    overflow-y: auto !important;
    box-shadow: 
        0 8px 32px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease !important;
    /* REMOVED BLUR FILTER FOR CLEAN TEXT */
}

.output-3d:hover {
    border-color: rgba(255, 255, 255, 0.4) !important;
    box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.5),
        inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

/* Enhanced text styling for better readability */
.output-3d h1 {
    color: #4facfe !important;
    font-weight: 700 !important;
    font-size: 2rem !important;
    margin-bottom: 16px !important;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.output-3d h2 {
    color: #667eea !important;
    font-weight: 600 !important;
    font-size: 1.5rem !important;
    margin: 20px 0 12px 0 !important;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.output-3d h3 {
    color: #f093fb !important;
    font-weight: 600 !important;
    font-size: 1.25rem !important;
    margin: 16px 0 8px 0 !important;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.output-3d h4, .output-3d h5, .output-3d h6 {
    color: #fad0c4 !important;
    font-weight: 600 !important;
    margin: 12px 0 6px 0 !important;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.output-3d p {
    color: rgba(255, 255, 255, 0.95) !important;
    line-height: 1.7 !important;
    font-size: 16px !important;
    margin-bottom: 12px !important;
    font-weight: 400 !important;
}

.output-3d li {
    color: rgba(255, 255, 255, 0.9) !important;
    line-height: 1.6 !important;
    font-size: 15px !important;
    margin-bottom: 6px !important;
    padding-left: 8px !important;
}

.output-3d ul, .output-3d ol {
    margin: 12px 0 !important;
    padding-left: 24px !important;
}

.output-3d strong {
    color: #4facfe !important;
    font-weight: 600 !important;
}

.output-3d em {
    color: #f093fb !important;
    font-style: italic !important;
}

.output-3d code {
    background: rgba(102, 126, 234, 0.2) !important;
    padding: 4px 8px !important;
    border-radius: 6px !important;
    color: #4facfe !important;
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace !important;
    font-size: 14px !important;
    border: 1px solid rgba(102, 126, 234, 0.3) !important;
}

.output-3d pre {
    background: rgba(20, 20, 20, 0.9) !important;
    padding: 16px !important;
    border-radius: 8px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    overflow-x: auto !important;
    margin: 16px 0 !important;
}

.output-3d blockquote {
    border-left: 4px solid #667eea !important;
    padding-left: 16px !important;
    margin: 16px 0 !important;
    color: rgba(255, 255, 255, 0.85) !important;
    font-style: italic !important;
    background: rgba(102, 126, 234, 0.1) !important;
    border-radius: 0 8px 8px 0 !important;
    padding: 12px 16px !important;
}

/* Custom Scrollbar for Output */
.output-3d::-webkit-scrollbar {
    width: 12px;
}

.output-3d::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
}

.output-3d::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-radius: 10px;
    border: 2px solid rgba(30, 30, 30, 0.95);
}

.output-3d::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #7c8cfc, #8a5eb8);
}

/* Footer */
.footer-3d {
    text-align: center;
    padding: 20px;
    margin-top: 30px;
    color: rgba(255, 255, 255, 0.8);
    font-weight: 500;
    font-size: 16px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Animations */
@keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes shine {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
}

/* Responsive Design */
@media (max-width: 768px) {
    .gradio-container {
        margin: 10px !important;
        padding: 15px !important;
    }
    
    .header-3d h1 {
        font-size: 2.5rem !important;
    }
    
    .card-3d {
        padding: 20px !important;
    }
    
    button {
        padding: 12px 24px !important;
        font-size: 14px !important;
    }
    
    .output-3d {
        padding: 20px !important;
    }
    
    .output-3d h1 {
        font-size: 1.5rem !important;
    }
    
    .output-3d h2 {
        font-size: 1.25rem !important;
    }
}

/* File Upload Styling - Fixed X Mark Issue */
.gradio-file {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 2px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.3s ease !important;
}

.gradio-file input[type="file"] {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 2px dashed rgba(255, 255, 255, 0.3) !important;
    border-radius: 16px !important;
    padding: 20px !important;
    transition: all 0.3s ease !important;
    color: white !important;
}

.gradio-file input[type="file"]:hover {
    border-color: #667eea !important;
    background: rgba(102, 126, 234, 0.1) !important;
}

/* Fix file display after upload */
.gradio-file .file {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    margin: 8px 0 !important;
    color: white !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
}

.gradio-file .file-name {
    color: white !important;
    font-weight: 500 !important;
    flex-grow: 1 !important;
    margin-right: 12px !important;
}

.gradio-file .file-size {
    color: rgba(255, 255, 255, 0.7) !important;
    font-size: 12px !important;
    margin-right: 12px !important;
}

.gradio-file button {
    background: rgba(239, 68, 68, 0.8) !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 6px 8px !important;
    color: white !important;
    font-size: 12px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    min-width: auto !important;
    width: auto !important;
    text-transform: none !important;
    letter-spacing: normal !important;
}

.gradio-file button:hover {
    background: rgba(220, 38, 38, 0.9) !important;
    transform: none !important;
    box-shadow: none !important;
}

/* Hide the default X mark styling */
.gradio-file .clear-button {
    display: none !important;
}

/* Loading Animation */
.loading {
    animation: float 2s ease-in-out infinite;
}

/* Ensure all elements stay properly aligned */
.main-row, .info-row, .btn-row {
    gap: 15px !important;
}

.main-row > div, .info-row > div {
    align-self: stretch !important;
}

/* Enhanced markdown styling for better readability */
.markdown {
    font-family: 'Inter', sans-serif !important;
}

/* Table styling if present in output */
.output-3d table {
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    overflow: hidden;
}

.output-3d th, .output-3d td {
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 12px 16px;
    text-align: left;
}

.output-3d th {
    background: rgba(102, 126, 234, 0.2);
    color: #4facfe !important;
    font-weight: 600;
}

.output-3d td {
    color: rgba(255, 255, 255, 0.9) !important;
}
"""

# ----------------- Gradio UI -----------------
with gr.Blocks(
    theme=gr.themes.Soft(),
    css=advanced_css,
    title="🚀 Advanced Requirement Agent - Spark Squad"
) as demo:

    # Enhanced Header
    gr.HTML("""
    <div class="header-3d">
      <h1> Requirement Agent</h1>
      <p>Transform notes or documents into polished Agile User Stories with AI-powered precision</p>
      <p>🌟 Made with ❤️ by <strong>Spark Squad</strong></p>
    </div>
    """)

    # Main Content Area
    with gr.Row(equal_height=True, elem_classes="main-row", variant="compact"):
        # Input Column
        with gr.Column(scale=2, elem_classes="card-3d"):
            gr.HTML("<h2 style='color: white; text-align: center; margin-bottom: 15px; font-weight: 600;'>📝 Input Section</h2>")
            
            notes_input = gr.Textbox(
                label="💭 Meeting Notes / Requirements", 
                placeholder="Paste your meeting notes, requirements, or any text here...",
                lines=14,
                elem_classes="input-field"
            )
            
            file_input = gr.File(
                label="📂 Upload Document", 
                file_types=[".txt", ".docx", ".pdf"], 
                type="filepath",
                elem_classes="file-upload"
            )
            
            with gr.Row(equal_height=True, elem_classes="btn-row"):
                generate_btn = gr.Button("🚀 Generate Stories", variant="primary", elem_classes="btn-primary")
                clear_btn = gr.Button("🧹 Clear All", elem_classes="btn-secondary")

        # Output Column
        with gr.Column(scale=3, elem_classes="card-3d"):
            gr.HTML("<h2 style='color: white; text-align: center; margin-bottom: 15px; font-weight: 600;'>📋 Generated User Stories</h2>")
            
            stories_md = gr.Markdown(
                "## 🎯 Your User Stories Will Appear Here\n\nOnce you provide input text or upload a document and click **Generate Stories**, results will show here.",
                elem_classes="output-3d"
            )
            
            # Enhancement Buttons
            gr.HTML("<h3 style='color: white; text-align: center; margin: 15px 0 10px; font-weight: 600;'>🛠️ Enhancement Options</h3>")
            with gr.Row(equal_height=True, elem_classes="btn-row"):
                shorter_btn = gr.Button("✂️ Make Concise", elem_classes="btn-warning")
                security_btn = gr.Button("🔒 Add Security", elem_classes="btn-success")
                expand_btn = gr.Button("🎯 Expand Details", elem_classes="btn-primary")
            
            # Export Buttons
            gr.HTML("<h3 style='color: white; text-align: center; margin: 15px 0 10px; font-weight: 600;'>💾 Export Options</h3>")
            with gr.Row(equal_height=True, elem_classes="btn-row"):
                download_md_btn = gr.Button("📄 Download Markdown", elem_classes="btn-success")
                download_docx_btn = gr.Button("📝 Download Word Doc", elem_classes="btn-primary")
            
            # Hidden file outputs
            download_md_file = gr.File(label="📄 Markdown File", visible=False)
            download_docx_file = gr.File(label="📝 Word Document", visible=False)

    # Info Cards Row
    with gr.Row(equal_height=True, elem_classes="info-row"):
        with gr.Column(scale=1, elem_classes="card-3d"):
            gr.HTML("""
            <div style="text-align: center; padding: 15px;">
                <h3 style="color: white; margin-bottom: 12px;">📊 Features</h3>
                <ul style="color: rgba(255,255,255,0.9); text-align: left; margin: 0; padding-left: 20px; line-height: 1.6;">
                    <li>🤖 AI-powered story generation</li>
                    <li>📁 Multiple file format support</li>
                    <li>🎨 Markdown formatting</li>
                    <li>🔄 Real-time enhancements</li>
                </ul>
            </div>
            """)

        with gr.Column(scale=1, elem_classes="card-3d"):
            gr.HTML("""
            <div style="text-align: center; padding: 15px;">
                <h3 style="color: white; margin-bottom: 12px;">📈 Benefits</h3>
                <ul style="color: rgba(255,255,255,0.9); text-align: left; margin: 0; padding-left: 20px; line-height: 1.6;">
                    <li>⚡ Save hours of manual work</li>
                    <li>✅ Consistent story format</li>
                    <li>🎯 Professional acceptance criteria</li>
                    <li>📤 Ready-to-use exports</li>
                </ul>
            </div>
            """)

        with gr.Column(scale=1, elem_classes="card-3d"):
            gr.HTML("""
            <div style="text-align: center; padding: 15px;">
                <h3 style="color: white; margin-bottom: 12px;">🚀 Getting Started</h3>
                <ol style="color: rgba(255,255,255,0.9); text-align: left; margin: 0; padding-left: 20px; line-height: 1.6;">
                    <li>📝 Enter your requirements</li>
                    <li>🔄 Click Generate Stories</li>
                    <li>🛠️ Enhance as needed</li>
                    <li>💾 Export your results</li>
                </ol>
            </div>
            """)

    # Enhanced Footer
    gr.HTML("""
    <div class="footer-3d">
        <p>🌟 Made with ❤️ by <strong>Spark Squad</strong></p>
        <p style="font-size: 14px; margin-top: 8px; opacity: 0.8;">
            Transform your requirements into professional user stories instantly
        </p>
    </div>
    """)

    # Event handlers
    generate_btn.click(
        fn=generate_stories,
        inputs=[notes_input, file_input],
        outputs=[stories_md]
    )
    
    clear_btn.click(
        fn=lambda: ("", None, "## 🎯 Your User Stories Will Appear Here\n\nOnce you provide input text or upload a document and click **Generate Stories**, results will show here."),
        outputs=[notes_input, file_input, stories_md]
    )
    
    shorter_btn.click(
        fn=lambda x: agent.enhance(x, "shorter"),
        inputs=[stories_md],
        outputs=[stories_md]
    )
    
    security_btn.click(
        fn=lambda x: agent.enhance(x, "security"),
        inputs=[stories_md],
        outputs=[stories_md]
    )
    
    expand_btn.click(
        fn=lambda x: agent.enhance(x, "expand"),
        inputs=[stories_md],
        outputs=[stories_md]
    )
    
    download_md_btn.click(
        fn=save_as_md,
        inputs=[stories_md],
        outputs=[download_md_file]
    )
    
    download_docx_btn.click(
        fn=save_as_docx,
        inputs=[stories_md],
        outputs=[download_docx_file]
    )

# ----------------- Run -----------------
demo.launch()