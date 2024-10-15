import os
import re
import argparse
from loguru import logger
from utils import load_yaml, load_job_description, compile_latex, validate_latex_syntax, fix_latex_syntax, move_cv_to_output
from job_description_processor import process_job_description
from prompts.education_generator import generate_education_section
from prompts.work_experience_generator import generate_work_experience_section
from prompts.projects_generator import generate_projects_section
from prompts.technical_skills_generator import generate_technical_skills_section
from prompts.name_generator import generate_cv_name
from utils import load_template, get_pdf_pages
from cv_reducer import CVReducer
import openai
import shutil
import subprocess
from dotenv import load_dotenv

load_dotenv()

class CVGenerator:
    def __init__(self, info, processed_job_info, output_dir, max_pages=1):
        self.info = info
        self.processed_job_info = processed_job_info
        self.job_description = str(processed_job_info)
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.sections = {
            'education': ('cv_template/sections/education.tex', generate_education_section),
            'work_experience': ('cv_template/sections/work_experience.tex', generate_work_experience_section),
            'projects': ('cv_template/sections/projects/example_project.tex', generate_projects_section),
            'technical_skills': ('cv_template/sections/technical_skills.tex', generate_technical_skills_section)
        }
        self.cv_reducer = CVReducer(
            output_dir, 
            processed_job_info.get('processed_description', self.job_description)
        )
        self.desired_pages = max_pages

    def generate_sections(self):
        for section, (template_path, generate_function) in self.sections.items():
            template = load_template(template_path)
            required_info = self.info.get(f"{section}_details", self.info)
            latex_content = generate_function(required_info, self.processed_job_info, template)
            latex_content = "\n".join(line for line in latex_content.splitlines() if line.strip())
            
            with open(f'{self.output_dir}/{section}.tex', 'w') as file:
                file.write(latex_content)
                logger.info(f"Content for {section} written to {self.output_dir}/{section}.tex")
                
    def generate_cv_name(self):
        return generate_cv_name(self.job_description)

    def check_existing_cv(self, cv_name):
        cv_dir = 'CVs'
        existing_cvs = [f for f in os.listdir(cv_dir) if f.startswith(cv_name) and f.endswith('.pdf')]
        
        if existing_cvs:
            print(f"A CV with the name {cv_name} already exists.")
            user_input = input("Do you want to regenerate this CV? (y/n): ").lower()
            
            if user_input == 'y':
                max_suffix = max([int(re.search(r'_(\d+)\.pdf$', cv).group(1)) for cv in existing_cvs if re.search(r'_(\d+)\.pdf$', cv)] or [0])
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
        
        num_pages = compile_latex(self.output_dir)
        if num_pages is not None:
            if num_pages > self.max_pages:
                logger.warning(f"Generated CV has {num_pages} pages, which exceeds the maximum of {self.max_pages}.")
                self.reduce_content()  # Call the reduce_content method
            
            # Add final review process
            self.final_review()
            
            # Rebuild the project after final review
            num_pages = compile_latex(self.output_dir)
            if num_pages is not None:
                logger.info(f"Final CV has {num_pages} page(s).")
                
                cv_dir = 'CVs'
                os.makedirs(cv_dir, exist_ok=True)
                pdf_file = next((f for f in os.listdir(self.output_dir) if f.endswith('.pdf')), None)
                if pdf_file:
                    new_pdf_name = f"{cv_name}.pdf"
                    shutil.move(os.path.join(self.output_dir, pdf_file), os.path.join(cv_dir, new_pdf_name))
                    logger.info(f"CV generated and saved as {new_pdf_name} in the CVs directory.")
                else:
                    logger.error("PDF file not found, unable to move.")
            else:
                logger.error("Failed to generate final CV after review.")
        else:
            logger.error("Failed to generate initial CV.")

    def generate_specific_sections(self, section_names):
        for section in section_names:
            if section in self.sections:
                template_path, generate_function = self.sections[section]
                template = load_template(template_path)
                required_info = self.info.get(f"{section}_details", self.info)
                latex_content = generate_function(required_info, self.processed_job_info, template)
                latex_content = "\n".join(line for line in latex_content.splitlines() if line.strip())
                
                with open(f'{self.output_dir}/{section}.tex', 'w') as file:
                    file.write(latex_content)
                    logger.info(f"Content for {section} written to {self.output_dir}/{section}.tex")
            else:
                logger.warning(f"Section '{section}' not found in available sections.")

    def compile_specific_sections(self, section_names):
        self.generate_resume_cls()
        self.generate_main_tex(section_names)
        self.compile_and_check_pages()

    def generate_main_tex(self, section_names=None):
        if section_names is None:
            section_names = self.sections.keys()

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

"""
        for section in section_names:
            if section in self.sections:
                main_tex += f"\\input{{{section}}}\n"

        main_tex += r"\end{document}"

        with open(f'{self.output_dir}/main.tex', 'w') as file:
            file.write(main_tex)
            logger.info(f"Main LaTeX file written to {self.output_dir}/main.tex")

    def generate_resume_cls(self):
        source_path = 'cv_template/resume.cls'
        destination_path = os.path.join(self.output_dir, 'resume.cls')

        if not os.path.isfile(source_path):
            logger.error(f"Source file {source_path} does not exist.")
            return

        try:
            subprocess.run(['cp', source_path, destination_path], check=True)
            logger.info(f"Copied resume.cls from {source_path} to {destination_path}")

            if os.path.isfile(destination_path):
                logger.info(f"Successfully verified that {destination_path} exists.")
            else:
                logger.error(f"File copy failed; {destination_path} does not exist after copy attempt.")
        except subprocess.CalledProcessError:
            logger.error(f"Failed to copy {source_path} to {destination_path}.")

    def compile_and_check_pages(self):
        current_dir = os.getcwd()
        os.chdir(self.output_dir)
        
        try:
            pages = compile_latex(self.output_dir)
            
            if pages is None:
                logger.error("Failed to compile CV.")
                return
            
            if pages != self.desired_pages:
                logger.warning(f"CV has {pages} pages. Adjusting content to fit {self.desired_pages} page(s).")
                self.adjust_content()
        finally:
            os.chdir(current_dir)

    def generate_single_section(self, section):
        template_path, generate_function = self.sections[section]
        template = load_template(template_path)
        required_info = self.info.get(f"{section}_details", self.info)
        latex_content = generate_function(required_info, self.processed_job_info, template)
        latex_content = "\n".join(line for line in latex_content.splitlines() if line.strip())
        
        with open(f'{self.output_dir}/{section}.tex', 'w') as file:
            file.write(latex_content)
            logger.info(f"Content for {section} written to {self.output_dir}/{section}.tex")

    def adjust_content(self):
        current_pages = get_pdf_pages(os.path.join(self.output_dir, 'main.pdf'))
        
        if current_pages == self.desired_pages:
            logger.info(f"CV is already {self.desired_pages} page(s). No adjustment needed.")
            return

        if current_pages < self.desired_pages:
            self.expand_content()
        else:
            self.reduce_content()

    def expand_content(self):
        logger.info("Expanding CV content...")
        for section in self.sections:
            self.expand_section(section)
            if get_pdf_pages(os.path.join(self.output_dir, 'main.pdf')) == self.desired_pages:
                break

    def reduce_content(self):
        logger.info("Reducing CV content...")
        self.cv_reducer.reduce_content()

    def identify_least_relevant_section(self):
        return self.cv_reducer.identify_least_relevant_section(self.sections.keys())

    def rank_sections_relevance(self):
        return self.cv_reducer.rank_sections_relevance(self.sections.keys())

    def can_reduce_section(self, section):
        return self.cv_reducer.can_reduce_section(section)

    def reduce_section(self, section):
        if section in self.sections:
            file_path = f'{self.output_dir}/{section}.tex'
            with open(file_path, 'r') as file:
                content = file.read()
            
            reduced_content = self.cv_reducer.reduce_section_content(section, content)
            
            with open(file_path, 'w') as file:
                file.write(reduced_content)
            
            logger.info(f"Reduced content for {section}")
            
            self.generate_main_tex()
            self.compile_and_check_pages()

    def expand_section(self, section):
        if section in self.sections:
            template_path, generate_function = self.sections[section]
            template = load_template(template_path)
            required_info = self.info.get(f"{section}_details", self.info)
            
            # Generate additional content for the section
            additional_content = generate_function(required_info, self.processed_job_info, template, expand=True)
            
            # Append the additional content to the existing section file
            with open(f'{self.output_dir}/{section}.tex', 'a') as file:
                file.write(additional_content)
            
            logger.info(f"Expanded content for {section}")
            
            # Recompile the CV
            self.generate_main_tex()
            self.compile_and_check_pages()

    def final_review(self):
        logger.info("Starting final review process...")
        
        # Check LaTeX syntax
        self.check_latex_syntax()
        
        # Ensure one-page requirement
        current_pages = get_pdf_pages(os.path.join(self.output_dir, 'main.pdf'))
        if current_pages > self.max_pages:
            logger.warning(f"CV is still {current_pages} pages. Attempting final reduction...")
            self.reduce_content()
        
        # Check for completeness
        self.check_completeness()
        
        # Optimize content
        self.optimize_content()
        
        logger.info("Final review process completed.")

    def check_latex_syntax(self):
        for section in self.sections:
            file_path = f'{self.output_dir}/{section}.tex'
            with open(file_path, 'r') as file:
                content = file.read()
            if not validate_latex_syntax(content):
                logger.warning(f"LaTeX syntax issues detected in {section}. Attempting to fix...")
                fixed_content = fix_latex_syntax(content)
                with open(file_path, 'w') as file:
                    file.write(fixed_content)

    def check_completeness(self):
        required_sections = set(self.sections.keys())
        existing_sections = set()
        for section in self.sections:
            file_path = f'{self.output_dir}/{section}.tex'
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    content = file.read()
                if content.strip():
                    existing_sections.add(section)
        
        missing_sections = required_sections - existing_sections
        if missing_sections:
            logger.warning(f"Missing sections: {', '.join(missing_sections)}. Attempting to regenerate...")
            for section in missing_sections:
                self.generate_single_section(section)

    def optimize_content(self):
        prompt = f"""
        Review and optimize the following CV content. Ensure it's well-structured, concise, and highlights the most relevant information for this job description:

        Job Description:
        {self.job_description}

        CV Content:
        """
        
        for section in self.sections:
            file_path = f'{self.output_dir}/{section}.tex'
            with open(file_path, 'r') as file:
                prompt += f"\n\n{section.upper()}:\n{file.read()}"
        
        prompt += "\n\nProvide optimized content for each section, maintaining LaTeX format."

        response = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL"),
            messages=[
                {"role": "system", "content": "You are an expert in CV optimization and LaTeX."},
                {"role": "user", "content": prompt}
            ]
        )

        optimized_content = response.choices[0].message['content'].strip()
        
        # Parse and save optimized content
        current_section = None
        section_content = ""
        for line in optimized_content.split('\n'):
            if line.strip().upper() in [section.upper() for section in self.sections]:
                if current_section:
                    with open(f'{self.output_dir}/{current_section.lower()}.tex', 'w') as file:
                        file.write(section_content.strip())
                current_section = line.strip()
                section_content = ""
            else:
                section_content += line + "\n"
        
        if current_section:
            with open(f'{self.output_dir}/{current_section.lower()}.tex', 'w') as file:
                file.write(section_content.strip())

        logger.info("CV content optimized.")

    def compile_cv(self):
        logger.info("Compiling CV...")
        try:
            num_pages = compile_latex(self.output_dir)
            if num_pages is not None:
                logger.info(f"CV compiled successfully. Number of pages: {num_pages}")
            else:
                logger.error("Failed to compile CV.")
        except Exception as e:
            logger.error(f"Failed to compile CV: {str(e)}")

def generate_cv(info_path, job_description_path, output_dir, max_pages):
    logger.info("Starting CV generation process...")

    info = load_yaml(info_path)
    if not info:
        logger.error(f"Failed to load info from {info_path}")
        return

    job_description = load_job_description(job_description_path)
    if not job_description:
        logger.error(f"Failed to load job description from {job_description_path}")
        return

    processed_job_info = process_job_description(job_description)

    os.makedirs(output_dir, exist_ok=True)

    build_cv(info, processed_job_info, output_dir, max_pages)

    logger.info("CV generation process completed.")

def compile_cv(output_dir):
    logger.info("Compiling CV...")
    num_pages = compile_latex(output_dir)
    if num_pages is not None:
        logger.info(f"CV compiled successfully. Number of pages: {num_pages}")
    else:
        logger.error("Failed to compile CV.")

def move_cv(output_dir, cv_name):
    logger.info("Moving CV to output directory...")
    move_cv_to_output(output_dir, cv_name)

def main():
    parser = argparse.ArgumentParser(description="CV Generator and Compiler")
    parser.add_argument("action", choices=["generate", "compile", "move"], help="Action to perform")
    parser.add_argument("--info", default="info.yml", help="Path to the YAML file containing personal information")
    parser.add_argument("--job", default="job_description.txt", help="Path to the job description file")
    parser.add_argument("--output", default="output", help="Output directory for generated files")
    parser.add_argument("--pages", type=int, default=1, choices=[1, 2], help="Maximum number of pages for the CV")
    parser.add_argument("--cv-name", help="Name of the CV file (required for 'move' action)")
    
    args = parser.parse_args()

    if args.action == "generate":
        generate_cv(args.info, args.job, args.output, args.pages)
    elif args.action == "compile":
        compile_cv(args.output)
    elif args.action == "move":
        if not args.cv_name:
            logger.error("CV name is required for 'move' action. Use --cv-name to specify.")
            return
        move_cv(args.output, args.cv_name)

if __name__ == "__main__":
    main()