import os
import shutil
import openai
import yaml
import traceback
from utils import get_pdf_pages, compile_latex  # Add get_pdf_pages import
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

class CVReducer:
    def __init__(self, output_dir, job_description, max_pages=1):
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.sections_to_reduce = ['technical_skills', 'projects', 'work_experience']
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.job_description = job_description

    def reduce_content(self):
        pdf_path = os.path.join(self.output_dir, 'main.pdf')
        current_pages = get_pdf_pages(pdf_path)
        while current_pages and current_pages > self.max_pages:
            section_to_reduce = self.identify_section_to_reduce()
            if not section_to_reduce:
                logger.warning("Unable to identify a section to reduce. Stopping reduction process.")
                break
            if self.reduce_section(section_to_reduce):
                compile_latex(self.output_dir)
                new_pages = get_pdf_pages(pdf_path)
                if new_pages and new_pages < current_pages:
                    current_pages = new_pages
                    logger.info(f"Reduced {section_to_reduce}. Current page count: {current_pages}")
                    if current_pages <= self.max_pages:
                        break
                else:
                    logger.warning(f"Reducing {section_to_reduce} did not decrease page count.")

    def identify_section_to_reduce(self):
        section_scores = {section: self.calculate_relevance_score(section, self.get_section_content(section))
                          for section in self.sections_to_reduce}
        return min(section_scores, key=section_scores.get) if section_scores else None

    def get_section_content(self, section):
        section_file = os.path.join(self.output_dir, f"{section}.tex")
        try:
            with open(section_file, 'r') as file:
                return file.read()
        except FileNotFoundError:
            logger.warning(f"Section file {section_file} not found.")
            return ""

    def calculate_relevance_score(self, section, content):
        prompt = f"""
        On a scale of 1-10, rate the relevance of this CV section for the given job description.
        Consider the importance of the section type and the specific content.

        Job Description:
        {self.job_description}

        CV Section ({section}):
        {content}

        Rate (1-10):
        """

        try:
            response = openai.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL"),
                messages=[
                    {"role": "system", "content": "You are an expert in CV evaluation and job matching."},
                    {"role": "user", "content": prompt}
                ]
            )
            score = int(response.choices[0].message['content'].strip())
            logger.info(f"Relevance score for {section}: {score}")
            return score
        except Exception as e:
            logger.error(f"Error calculating relevance score for {section}: {str(e)}")
            return 5  # Default to middle score if there's an error

    def reduce_section(self, section):
        content = self.get_section_content(section)
        prompt = f"""
        Reduce the content of this CV section while maintaining the most relevant information for the job description.
        Remove the least important items or details.

        Job Description:
        {self.job_description}

        Current CV Section ({section}):
        {content}

        Reduced CV Section:
        """

        try:
            response = openai.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL"),
                messages=[
                    {"role": "system", "content": "You are an expert in CV optimization and job matching."},
                    {"role": "user", "content": prompt}
                ]
            )
            reduced_content = response.choices[0].message['content'].strip()
            
            with open(os.path.join(self.output_dir, f"{section}.tex"), 'w') as file:
                file.write(reduced_content)
            
            logger.info(f"Reduced content for section: {section}")
            return True
        except Exception as e:
            logger.error(f"Error reducing content for {section}: {str(e)}")
            return False

def main():
    logger.add("cv_reducer.log", rotation="500 MB")

    with open('info.yml', 'r') as file:
        info = yaml.safe_load(file)
        openai_api_key = info.get('openai_api_key')
        job_role = info.get('job_role')

    temp_dir = 'cv_template'

    try:
        shutil.copytree('cv_template', temp_dir, dirs_exist_ok=True)
        os.chdir(temp_dir)

        reducer = CVReducer('.', job_description="")
        reducer.compile_pdf()

        initial_pages = reducer.get_pdf_pages()
        logger.info(f"Initial CV has {initial_pages} pages")

        reducer.reduce_content()

        final_pages = reducer.get_pdf_pages()
        logger.info(f"Final CV has {final_pages} pages")

        if final_pages > reducer.max_pages:
            logger.warning(f"Could not reduce CV to {reducer.max_pages} page(s). Final page count: {final_pages}")
        else:
            logger.info(f"Successfully reduced CV to {final_pages} page(s)")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        logger.debug(traceback.format_exc())
    finally:
        os.chdir('..')
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()