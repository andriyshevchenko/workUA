"""
Скрипт для конвертації інструкції з Markdown в PDF
"""
import markdown
from pathlib import Path
from utils import separator_line

def markdown_to_html(md_file: str, html_file: str):
    """Конвертує Markdown в HTML з гарним стилем"""
    
    # Читаємо markdown файл
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Конвертуємо в HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc']
    )
    
    # Додаємо CSS стилі для красивого вигляду
    full_html = f"""
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Work.UA Bot - Інструкція для користувача</title>
    <style>
        @page {{
            margin: 2cm;
            size: A4;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 40px;
        }}
        
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 5px;
            margin-top: 30px;
        }}
        
        h3 {{
            color: #2980b9;
            margin-top: 20px;
        }}
        
        h4 {{
            color: #7f8c8d;
            margin-top: 15px;
        }}
        
        code {{
            background: #f4f4f4;
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 2px 5px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
        }}
        
        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
            page-break-inside: avoid;
        }}
        
        pre code {{
            background: none;
            border: none;
            color: #ecf0f1;
            padding: 0;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 20px;
            margin-left: 0;
            color: #7f8c8d;
            background: #ecf0f1;
            padding: 10px 20px;
            border-radius: 0 5px 5px 0;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            page-break-inside: avoid;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        
        th {{
            background-color: #3498db;
            color: white;
        }}
        
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        ul, ol {{
            margin: 10px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 5px 0;
        }}
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px 15px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }}
        
        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 10px 15px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }}
        
        .info {{
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            padding: 10px 15px;
            margin: 15px 0;
            border-radius: 0 5px 5px 0;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 30px 0;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            h1, h2, h3 {{
                page-break-after: avoid;
            }}
            
            pre, blockquote, table {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""
    
    # Зберігаємо HTML
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✅ HTML створено: {html_file}")
    return html_file

if __name__ == "__main__":
    md_file = "ІНСТРУКЦІЯ_ДЛЯ_КОРИСТУВАЧА.md"
    html_file = "ІНСТРУКЦІЯ_ДЛЯ_КОРИСТУВАЧА.html"
    
    print("🔄 Конвертую Markdown в HTML...")
    html_path = markdown_to_html(md_file, html_file)
    
    print("\n" + separator_line())
    print("✅ HTML файл створено!")
    print(separator_line())
    print(f"\n📄 Файл: {html_path}")
    print("\n💡 Як створити PDF:")
    print("   1. Відкрийте файл в браузері (Chrome або Edge)")
    print("   2. Натисніть Ctrl+P (Друк)")
    print("   3. Оберіть 'Зберегти як PDF'")
    print("   4. Налаштуйте поля та масштаб")
    print("   5. Збережіть файл")
    print("\n" + separator_line())
