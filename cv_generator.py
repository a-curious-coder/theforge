import os
import logging
import subprocess
import shutil
import re
import PyPDF2

from prompts.education_generator import generate_education_section
from prompts.work_experience_generator import generate_work_experience_section
from prompts.projects_generator import generate_projects_section
from prompts.technical_skills_generator import generate_technical_skills_section
from prompts.name_generator import generate_cv_name
from utils import load_template
from cv_reducer import CVReducer  # Import the new CVReducer class

class CVGenerator:
    def __init__(self, info, job_description, output_dir, max_pages=1):
        self.info = info
        self.job_description = job_description
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.sections = {
            'education': ('cv_template/sections/education.tex', generate_education_section),
            'work_experience': ('cv_template/sections/work_experience.tex', generate_work_experience_section),
            'projects': ('cv_template/sections/projects/example_project.tex', generate_projects_section),
            'technical_skills': ('cv_template/sections/technical_skills.tex', generate_technical_skills_section)
        }
        self.cv_reducer = CVReducer(output_dir, max_pages)  # Create an instance of CVReducer

    def generate_cv_name(self):
        return generate_cv_name(self.job_description)

    def check_existing_cv(self, cv_name):
        cv_dir = 'CVs'
        existing_cvs = [f for f in os.listdir(cv_dir) if f.startswith(cv_name) and f.endswith('.pdf')]
        
        if existing_cvs:
            print(f"A CV with the name {cv_name} already exists.")
            user_input = input("Do you want to regenerate this CV? (y/n): ").lower()
            
            if user_input == 'y':
                # Find the highest number suffix
                max_suffix = 0
                for cv in existing_cvs:
                    match = re.search(r'_(\d+)\.pdf$', cv)
                    if match:
                        suffix = int(match.group(1))
                        max_suffix = max(max_suffix, suffix)
                
                new_cv_name = f"{cv_name[:-4]}_{max_suffix + 1}"
                return new_cv_name
            else:
                return None
        
        return cv_name

    def generate_cv(self):
        cv_name = self.generate_cv_name()
        cv_name = self.check_existing_cv(cv_name)
        
        if cv_name is None:
            print("CV generation cancelled.")
            return

        for filename in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, filename)
            os.remove(file_path)

        self.generate_sections()
        self.generate_main_tex()
        self.generate_resume_cls()
        self.compile_and_check_pages()

        # Move the generated PDF to the CVs directory with the new name
        cv_dir = 'CVs'
        os.makedirs(cv_dir, exist_ok=True)
        pdf_file = next((f for f in os.listdir(self.output_dir) if f.endswith('.pdf')), None)
        if pdf_file:
            new_pdf_name = f"{cv_name}.pdf"
            shutil.move(os.path.join(self.output_dir, pdf_file), os.path.join(cv_dir, new_pdf_name))
            logging.info(f"CV generated and saved as {new_pdf_name} in the CVs directory.")
        else:
            logging.error("PDF file not found, unable to move.")

    def generate_sections(self):
        for section, (template_path, generate_function) in self.sections.items():
            template = load_template(template_path)
            latex_content = generate_function(self.info.get(f"{section}_details", self.info), self.job_description, template)
            latex_content = "\n".join(line for line in latex_content.splitlines() if line.strip())  # Remove empty lines
            
            with open(f'{self.output_dir}/{section}.tex', 'w') as file:
                file.write(latex_content)
                logging.info(f"Content for {section} written to {self.output_dir}/{section}.tex")

    def generate_main_tex(self):
        main_tex = r"""\documentclass{resume} % Use the custom resume.cls style
\usepackage{amssymb}
\usepackage{enumitem}
\usepackage{multicol} % Added multicols package
\usepackage{hyperref} % Allows me to make clickable links
\usepackage[left=0.75in,top=0.35in,right=0.75in,bottom=0.35in]{geometry} % Document margins
\newcommand{\tab}[1]{\hspace{.2667\textwidth}\rlap{#1}}
\newcommand{\itab}[1]{\hspace{0em}\rlap{#1}}

% Personal Information
\name{""" + f"{self.info['personal_information']['name']} {self.info['personal_information']['surname']}" + r"""}
\address{%
    {\href{mailto:""" + f"{self.info['personal_information']['email']}" + r"""}{""" + f"{self.info['personal_information']['email']}" + r"""}} \\
    {\href{""" + f"{self.info['personal_information']['linkedin']}" + r"""}{""" + f"{self.info['personal_information']['linkedin'].split('/')[-1]}" + r"""}} \\
    {\href{""" + f"{self.info['personal_information']['github']}" + r"""}{""" + f"{self.info['personal_information']['github'].split('/')[-1]}" + r"""}}%
}

\begin{document}
\vspace{0.12cm}

\input{work_experience}
\input{projects}
\input{education}
\input{technical_skills}

\end{document}
"""
        with open(f'{self.output_dir}/main.tex', 'w') as file:
            file.write(main_tex)
            logging.info(f"Main LaTeX file written to {self.output_dir}/main.tex")

    def generate_resume_cls(self):
        # Define the source and destination paths
        source_path = 'cv_template/resume.cls'
        destination_path = os.path.join(self.output_dir, 'resume.cls')

        # Verify the source file exists before attempting to copy
        if not os.path.isfile(source_path):
            logging.error(f"Source file {source_path} does not exist.")
            return

        # Use subprocess to copy the file
        try:
            subprocess.run(['cp', source_path, destination_path], check=True)
            logging.info(f"Copied resume.cls from {source_path} to {destination_path}")

            # Verify the file has been copied across
            if os.path.isfile(destination_path):
                logging.info(f"Successfully verified that {destination_path} exists.")
            else:
                logging.error(f"File copy failed; {destination_path} does not exist after copy attempt.")
        except subprocess.CalledProcessError:
            logging.error(f"Failed to copy {source_path} to {destination_path}.")

    def compile_and_check_pages(self):
        # Change to the output directory before running pdflatex
        current_dir = os.getcwd()
        os.chdir(self.output_dir)
        
        try:
            subprocess.run(['pdflatex', 'main.tex'], check=True)
            
            # Use PyPDF2 to get the number of pages
            with open('main.pdf', 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                pages = len(pdf_reader.pages)
            
            if pages > self.max_pages:
                logging.warning(f"CV exceeds {self.max_pages} pages. Attempting to reduce content.")
                self.cv_reducer.reduce_content(pages)
        finally:
            # Change back to the original directory
            os.chdir(current_dir)