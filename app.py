from flask import Flask, render_template, send_file, request, Response
import os
import time
from werkzeug.utils import secure_filename
from cv_generator import CVGenerator
from job_description_processor import process_job_description

app = Flask(__name__)

# Assuming you have a function to load info from info.yml
from utils import load_yaml

@app.route('/')
def index():
    sections = ['education', 'work_experience', 'projects', 'technical_skills']
    section_icons = {
        'education': 'graduation-cap',
        'work_experience': 'briefcase',
        'projects': 'code',
        'technical_skills': 'cogs'
    }
    return render_template('index.html', sections=sections, section_icons=section_icons, title="The Forge - CV Generator")

@app.route('/generate_cv', methods=['POST'])
def generate_cv():
    job_description = request.form['job_description']
    info = load_yaml('info.yml')
    processed_job_info = process_job_description(job_description)
    
    cv_generator = CVGenerator(info, processed_job_info, 'output', max_pages=1)
    
    def generate():
        stream = cv_generator.generate_cv(stream=True)
        for chunk in stream:
            if 'content' in chunk:
                yield f"data: {chunk['content']}\n\n"
            elif 'delim' in chunk:
                yield f"data: {chunk['delim']} {chunk.get('agent', '')}\n\n"
            elif 'response' in chunk:
                yield "data: complete\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/view_pdf')
def view_pdf():
    pdf_path = 'output/main.pdf'  # Adjust this path to your actual PDF location
    if not os.path.exists(pdf_path):
        pdf_path = 'static/example.pdf'  # Path to your example PDF
    return send_file(pdf_path, mimetype='application/pdf')

@app.route('/download_pdf')
def download_pdf():
    pdf_path = 'output/main.pdf'  # Adjust this path to your actual PDF location
    if not os.path.exists(pdf_path):
        pdf_path = 'static/example.pdf'  # Path to your example PDF
    return send_file(pdf_path, as_attachment=True, download_name='generated_cv.pdf')

if __name__ == '__main__':
    app.run(debug=True)
