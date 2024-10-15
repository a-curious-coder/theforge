import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # OpenAI settings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    # Output directories
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
    CV_OUTPUT_DIR = os.getenv('CV_OUTPUT_DIR', 'CVs')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')

    # Input files
    JOB_DESCRIPTION_FILE = os.getenv('JOB_DESCRIPTION_FILE', 'job_description.txt')
    JOB_DESCRIPTION_PROCESSED_FILE = os.getenv('JOB_DESCRIPTION_PROCESSED_FILE', '{job_description_file}_enhanced.json')
    INFO_FILE = os.getenv('INFO_FILE', 'info.yml')

    # CV generation settings
    DESIRED_PAGES = int(os.getenv('DESIRED_PAGES', 1))

    # Logging
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')

    @classmethod
    def get_job_description_processed_file(cls, job_description_file=None):
        if job_description_file is None:
            job_description_file = cls.JOB_DESCRIPTION_FILE
        return cls.JOB_DESCRIPTION_PROCESSED_FILE.format(job_description_file=os.path.splitext(job_description_file)[0])


config = Config()
