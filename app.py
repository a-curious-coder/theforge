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
    info = load_yaml('info.yml')  # Load your info.yml file
    processed_job_info = process_job_description(job_description)
    
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    cv_generator = CVGenerator(info, processed_job_info, output_dir, max_pages=1)
    
    def generate():
        yield "data: Analyzing job description\n\n"
        time.sleep(1)  # Simulate processing time
        
        for section in ['education', 'work_experience', 'projects', 'technical_skills']:
            yield f"data: section:{section}\n\n"
            cv_generator.generate_single_section(section)
            cv_generator.compile_cv()  # Compile after each section
            time.sleep(1)  # Simulate processing time
        
        yield "data: Optimizing CV content\n\n"
        cv_generator.optimize_content()
        time.sleep(1)  # Simulate processing time
        
        yield "data: Compiling final LaTeX document\n\n"
        cv_generator.compile_cv()
        time.sleep(1)  # Simulate processing time
        
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