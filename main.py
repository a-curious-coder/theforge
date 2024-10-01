import os
import logging
import shutil
from dotenv import load_dotenv
import openai
from cv_generator import CVGenerator
from utils import load_yaml, build_latex_project, load_job_description
from prompts.projects_generator import generate_projects_section
from prompts.education_generator import generate_education_section
from prompts.technical_skills_generator import generate_technical_skills_section
from prompts.work_experience_generator import generate_work_experience_section

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()
logging.info("Environment variables loaded.")

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
logging.info("OpenAI API key set.")

def main():
    info = load_yaml('info.yml')
    job_description = load_job_description('job_description.txt')

    # Create output directories if they don't exist
    output_dir = 'new_cv'
    cv_output_dir = 'CVs'
    output_dirs = [output_dir, cv_output_dir]
    for dir in output_dirs:
        os.makedirs(dir, exist_ok=True)
        logging.info(f"Output directory '{dir}' created.")

    cv_generator = CVGenerator(info, job_description, output_dir)
    cv_generator.generate_cv()
    logging.info("Files generated successfully in the new_cv folder!")

    if build_latex_project(output_dir):
        # Move the generated PDF to the CVs directory
        pdf_file = next((f for f in os.listdir(output_dir) if f.endswith('.pdf')), None)
        if pdf_file:
            shutil.move(os.path.join(output_dir, pdf_file), os.path.join(cv_output_dir, pdf_file))
            logging.info(f"PDF moved to '{cv_output_dir}/{pdf_file}'.")
        else:
            logging.error("PDF file not found, unable to move.")

        logging.info("Project built successfully.")
    else:
        logging.error("Failed to build project.")

if __name__ == "__main__":
    main()