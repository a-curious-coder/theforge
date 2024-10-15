import os
from loguru import logger
from utils import load_yaml, load_job_description, compile_latex, load_template, get_pdf_pages, move_cv_to_output
from job_description_processor import process_job_description
from prompts import (
    get_cv_name_prompt,
    get_projects_prompt,
    get_education_prompt,
    get_work_experience_prompt,
    get_technical_skills_prompt
)
from cv_reducer import CVReducer
from dotenv import load_dotenv
from swarm import Swarm, Agent
from swarm.core import Result
from tenacity import retry, stop_after_attempt, wait_random_exponential

load_dotenv()

client = Swarm()

class CVGenerator:
    def __init__(self, info, processed_job_info, output_dir, max_pages=1):
        self.info = info
        self.processed_job_info = processed_job_info
        self.output_dir = output_dir
        self.max_pages = max_pages
        
        self.section_agent = Agent(
            model=os.getenv("OPENAI_MODEL"),
            name="Section Generator",
            instructions="""You are an expert in generating CV sections based on personal information and job requirements.
            Your task is to create highly relevant and impactful content for each section of the CV.
            Ensure that the content is tailored to the specific job description and highlights the candidate's most relevant skills and experiences.""",
            functions=[
                self.generate_education,
                self.generate_work_experience,
                self.generate_projects,
                self.generate_technical_skills,
                self.generate_cv_name
            ]
        )
        
        self.optimizer_agent = Agent(
            model=os.getenv("OPENAI_MODEL"),
            name="CV Optimizer",
            instructions="""You are an expert in optimizing CV content to match job requirements and fit within page limits.
            Your task is to refine and condense the CV content while maintaining its impact and relevance.
            Focus on highlighting the most important information and removing any redundant or less relevant details.
            Ensure that bullet points are between 75 and 95 characters long.""",
            functions=[self.optimize_content]
        )
        
        self.reviewer_agent = Agent(
            model=os.getenv("OPENAI_MODEL"),
            name="CV Reviewer",
            instructions="""You are an expert in reviewing and providing feedback on CVs.
            Your task is to critically evaluate the CV for its overall quality, relevance to the job description, and adherence to best practices.
            Use the processed job information to ensure the CV is tailored to the specific job requirements.
            Provide specific suggestions for improvements and highlight any areas that may need further attention.
            Pay special attention to how well the CV matches the key requirements and preferences outlined in the job description.""",
            functions=[self.review_cv]
        )

        self.formatter_agent = Agent(
            model=os.getenv("OPENAI_MODEL"),
            name="LaTeX Formatter",
            instructions="""You are an expert in formatting CVs using LaTeX.
            Your task is to ensure that the CV is properly formatted, visually appealing, and adheres to LaTeX best practices.
            Pay attention to spacing, alignment, and overall layout to create a professional-looking document.""",
            functions=[self.format_latex]
        )

        self.cv_reducer = CVReducer(output_dir, processed_job_info, max_pages)

    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(min=1, max=60))
    def generate_cv(self):
        try:
            context_variables = {
                "info": self.info,
                "processed_job_info": self.processed_job_info,
                "output_dir": self.output_dir,
                "max_pages": self.max_pages
            }
            
            logger.info("Starting CV generation process")
            
            # Generate CV name
            cv_name_prompt = get_cv_name_prompt(self.processed_job_info)
            cv_name_response = client.run(
                agent=self.section_agent,
                messages=[{"role": "user", "content": cv_name_prompt}],
                context_variables=context_variables
            )
            cv_name = cv_name_response.context_variables.get('cv_name', 'default_cv_name')
            
            # Generate sections
            sections = ['education', 'work_experience', 'projects', 'technical_skills']
            for section in sections:
                logger.info(f"Generating {section} section")
                prompt = getattr(self, f'generate_{section}')(context_variables)
                response = client.run(
                    agent=self.section_agent,
                    messages=[{"role": "user", "content": prompt.context_variables[f'{section}_content']}],
                    context_variables=context_variables
                )
                self._save_section_content(section, response.context_variables.get(f'{section}_content', ''))
            
            # Optimize content
            logger.info("Optimizing CV content")
            response = client.run(
                agent=self.optimizer_agent,
                messages=[{"role": "user", "content": "Optimize and reduce CV content if needed."}],
                context_variables=context_variables
            )
            
            # Format LaTeX
            logger.info("Formatting CV in LaTeX")
            response = client.run(
                agent=self.formatter_agent,
                messages=[{"role": "user", "content": "Format the CV in LaTeX."}],
                context_variables=response.context_variables
            )
            
            self._save_main_tex(response.context_variables.get('formatted_content', ''))
            
            # Compile LaTeX
            num_pages = compile_latex(self.output_dir)
            if num_pages is not None:
                if num_pages > self.max_pages:
                    logger.warning(f"Generated CV has {num_pages} pages, which exceeds the maximum of {self.max_pages}.")
                    self.cv_reducer.reduce_content()
                    num_pages = compile_latex(self.output_dir)
            
            # Review CV
            logger.info("Reviewing final CV")
            response = client.run(
                agent=self.reviewer_agent,
                messages=[{"role": "user", "content": "Review the final CV using the processed job information."}],
                context_variables=response.context_variables
            )
            
            self._save_review_feedback(response.context_variables.get('review_feedback', ''))
            
            # Move CV to output directory
            move_cv_to_output(self.output_dir, cv_name)
            
            logger.success("CV generation process completed successfully")
            return response
        except Exception as e:
            logger.error(f"Error in CV generation process: {str(e)}")
            raise

    def generate_education(self, context_variables):
        prompt = get_education_prompt(self.info, self.processed_job_info, load_template('cv_template/sections/education.tex'))
        return Result(value="Education section generated", context_variables={"education_content": prompt})

    def generate_work_experience(self, context_variables):
        prompt = get_work_experience_prompt(self.info, self.processed_job_info, load_template('cv_template/sections/work_experience.tex'))
        return Result(value="Work experience section generated", context_variables={"work_experience_content": prompt})

    def generate_projects(self, context_variables):
        prompt = get_projects_prompt(self.info, self.processed_job_info, load_template('cv_template/sections/projects.tex'))
        return Result(value="Projects section generated", context_variables={"projects_content": prompt})

    def generate_technical_skills(self, context_variables):
        prompt = get_technical_skills_prompt(self.info, self.processed_job_info, load_template('cv_template/sections/technical_skills.tex'))
        return Result(value="Technical skills section generated", context_variables={"technical_skills_content": prompt})

    def generate_cv_name(self, context_variables):
        prompt = get_cv_name_prompt(self.processed_job_info)
        return Result(value="CV name generated", context_variables={"cv_name": prompt})

    def optimize_content(self, context_variables):
        return self.cv_reducer.optimize_content(context_variables)

    def review_cv(self, context_variables):
        with open(os.path.join(self.output_dir, 'main.tex'), 'r') as f:
            cv_content = f.read()
        # Perform review on cv_content
        review_feedback = "This is a simulated review of the CV..."  # Replace with actual review logic
        return Result(value="CV reviewed", context_variables={"review_feedback": review_feedback})

    def format_latex(self, context_variables):
        formatted_content = "\\documentclass{resume}\n\\begin{document}\n"
        for section in ['education', 'work_experience', 'projects', 'technical_skills']:
            with open(os.path.join(self.output_dir, f'{section}.tex'), 'r') as f:
                formatted_content += f.read() + "\n"
        formatted_content += "\\end{document}"
        return Result(value="CV formatted in LaTeX", context_variables={"formatted_content": formatted_content})

    def _save_section_content(self, section, content):
        with open(os.path.join(self.output_dir, f'{section}.tex'), 'w') as f:
            f.write(content)
        logger.info(f"Saved {section} section content")

    def _save_main_tex(self, content):
        with open(os.path.join(self.output_dir, 'main.tex'), 'w') as f:
            f.write(content)
        logger.info("Saved main.tex content")

    def _save_review_feedback(self, feedback):
        with open(os.path.join(self.output_dir, 'review_feedback.txt'), 'w') as f:
            f.write(feedback)
        logger.info("Saved review feedback")

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

    cv_generator = CVGenerator(info, processed_job_info, output_dir, max_pages)
    cv_generator.generate_cv()

    logger.info("CV generation process completed.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate a CV")
    parser.add_argument("--info", default="info.yml", help="Path to the YAML file containing personal information")
    parser.add_argument("--job", default="job_description.txt", help="Path to the job description file")
    parser.add_argument("--output", default="output", help="Output directory for generated files")
    parser.add_argument("--pages", type=int, default=1, choices=[1, 2], help="Maximum number of pages for the CV")
    
    args = parser.parse_args()
    
    generate_cv(args.info, args.job, args.output, args.pages)
