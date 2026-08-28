import markdown
from xhtml2pdf import pisa
from io import BytesIO

def markdown_to_pdf(topic, report_md):
    html_body = markdown.markdown(
        report_md,
        extensions=["tables", "fenced_code"]
    )

    html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1a1a1a; }}
        h1 {{ color: #4b3ccf; font-size: 20pt; border-bottom: 2px solid #4b3ccf; padding-bottom: 6px; }}
        h2 {{ color: #2d2d6b; font-size: 15pt; margin-top: 20px; }}
        h3 {{ color: #333; font-size: 12.5pt; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ccc; padding: 6px 8px; font-size: 9.5pt; }}
        th {{ background-color: #eef0ff; }}
        code, pre {{ background-color: #f5f5f5; padding: 4px; font-size: 9pt; }}
        .cover {{ text-align: center; margin-bottom: 40px; }}
        .cover h1 {{ border: none; font-size: 26pt; }}
        .cover p {{ color: #666; }}
    </style>
    </head>
    <body>
        <div class="cover">
            <h1>AgentX Research Report</h1>
            <p>Topic: {topic}</p>
        </div>
        {html_body}
    </body>
    </html>
    """

    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer.read()