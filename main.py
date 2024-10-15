import os
import shutil
from dotenv import load_dotenv
import openai
from loguru import logger
from cv_generator import CVGenerator
from utils import load_yaml, load_job_description, get_pdf_pages
from job_description_processor import process_job_description

# Configure logger
logger.add("app.log", rotation="500 MB", level="DEBUG")

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded.")

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
logger.success("OpenAI API key set successfully.")

def generate_single_section(cv_generator, section_name):
    cv_generator.generate_single_section(section_name)
    pdf_pages = get_pdf_pages(cv_generator.output_dir)
    if pdf_pages is not None:
        logger.success(f"Section '{section_name}' generated successfully.")
        # Move the generated PDF to a test directory
        test_cv_dir = 'TestCVs'
        os.makedirs(test_cv_dir, exist_ok=True)
        pdf_file = next((f for f in os.listdir(cv_generator.output_dir) if f.endswith('.pdf')), None)
        if pdf_file:
            new_pdf_name = f"test_{section_name}.pdf"
            shutil.move(os.path.join(cv_generator.output_dir, pdf_file), os.path.join(test_cv_dir, new_pdf_name))
            logger.info(f"Section PDF saved as {new_pdf_name} in the TestCVs directory.")
        else:
            logger.error("PDF file not found, unable to move.")
    else:
        logger.critical(f"Failed to generate section '{section_name}'.")

def main():
    try:
        info = load_yaml('info.yml')
        job_description = load_job_description('job_description.txt')
        processed_job_info = process_job_description(job_description)

        desired_pages = 1
        
        output_dir = 'output'
        cv_output_dir = 'CVs'
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(cv_output_dir, exist_ok=True)
        
        cv_generator = CVGenerator(info, processed_job_info, output_dir, max_pages=desired_pages)
        cv_generator.generate_cv()
        
        pdf_file = next((f for f in os.listdir(output_dir) if f.endswith('.pdf')), None)
        if pdf_file:
            cv_name = cv_generator.generate_cv_name()
            new_pdf_name = f"{cv_name}.pdf"
            shutil.move(os.path.join(output_dir, pdf_file), os.path.join(cv_output_dir, new_pdf_name))
            logger.success(f"CV generated and saved as {new_pdf_name} in the CVs directory.")
        else:
            logger.error("PDF file not found, unable to move.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting CV generation process...")
    main()
    logger.info("CV generation process completed.")