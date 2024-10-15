from loguru import logger
from cv_generator import CVGenerator
from utils import load_yaml, load_job_description
from job_description_processor import JobDescriptionProcessor
from config import config
import os

def setup_logging():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_file = os.path.join(config.LOG_DIR, config.LOG_FILE)
    logger.add(log_file, rotation="500 MB", level="DEBUG")

def setup_directories():
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.CV_OUTPUT_DIR, exist_ok=True)

def main():
    try:
        # Setup
        setup_logging()
        setup_directories()

        # Load and process data
        info = load_yaml(config.INFO_FILE)
        job_description = load_job_description(config.JOB_DESCRIPTION_FILE)
        
        job_processor = JobDescriptionProcessor()
        processed_job_info = job_processor.process_job_description(job_description)
        
        cv_generator = CVGenerator(info, processed_job_info, config.OUTPUT_DIR, max_pages=config.DESIRED_PAGES)
        
        # Generate CV
        result = cv_generator.generate_cv()
        logger.info("CV generation process completed.")
        # If you need the review feedback, you can access it from the result
        review_feedback = result.context_variables.get('review_feedback', '')
        if review_feedback:
            logger.info("CV reviewed. Feedback available in the result.")
        
        # Move generated PDF
        pdf_file = next((f for f in os.listdir(config.OUTPUT_DIR) if f.endswith('.pdf')), None)
        if pdf_file:
            cv_name = cv_generator.generate_cv_name()
            new_pdf_name = f"{cv_name}.pdf"
            os.rename(os.path.join(config.OUTPUT_DIR, pdf_file), os.path.join(config.CV_OUTPUT_DIR, new_pdf_name))
            logger.success(f"CV generated and saved as {new_pdf_name} in the CVs directory.")
        else:
            logger.error("PDF file not found, unable to move.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting CV generation process...")
    main()
    logger.info("CV generation process completed.")
