import os
import shutil
from loguru import logger
from swarm import Swarm, Agent
from config import config
from openai import OpenAI
from utils import get_pdf_pages, compile_latex, adjust_bullet_point_lengths
from swarm.core import Result

client = Swarm()

class CVOptimizer:
    def __init__(self, output_dir, processed_job_info, personal_info, max_pages=1):
        self.output_dir = output_dir
        self.processed_job_info = processed_job_info
        self.personal_info = personal_info
        self.max_pages = max_pages
        self.sections = ['education', 'work_experience', 'projects', 'technical_skills']
        self.sections_to_reduce = ['technical_skills', 'projects', 'work_experience']

        self.optimizer_agent = Agent(
            model=config.OPENAI_MODEL,
            name="CV Optimizer",
            instructions="""You are an expert in optimizing CV content to match job requirements and fit within page limits.
            Your task is to refine and condense the CV content while maintaining its impact and relevance.
            Focus on highlighting the most important information and removing any redundant or less relevant details.
            Ensure that bullet points are between 75 and 95 characters long.""",
            functions=[self._optimize_section]
        )

        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

    def optimize_content(self):
        self._initial_optimization()
        self._reduce_content_if_needed()
        self._final_formatting_pass()

    def _initial_optimization(self):
        for section in self.sections:
            self._optimize_section(section)

    def _reduce_content_if_needed(self):
        pdf_path = os.path.join(self.output_dir, 'main.pdf')
        current_pages = get_pdf_pages(pdf_path)
        while current_pages and current_pages > self.max_pages:
            section_to_reduce = self._identify_section_to_reduce()
            if not section_to_reduce:
                logger.warning("Unable to identify a section to reduce. Stopping reduction process.")
                break
            if self._reduce_section(section_to_reduce):
                compile_latex(self.output_dir)
                new_pages = get_pdf_pages(pdf_path)
                if new_pages and new_pages < current_pages:
                    current_pages = new_pages
                    logger.info(f"Reduced {section_to_reduce}. Current page count: {current_pages}")
                    if current_pages <= self.max_pages:
                        break
                else:
                    logger.warning(f"Reducing {section_to_reduce} did not decrease page count.")

    def _optimize_section(self, section, reduce=False):
        content = self._get_section_content(section)
        
        optimization_context = {
            "section_content": content,
            "section_name": section,
            "processed_job_info": self.processed_job_info,
            "personal_info": self.personal_info,
            "reduce": reduce
        }
        
        response = client.run(
            agent=self.optimizer_agent,
            messages=[{
                "role": "user", 
                "content": f"""
                Optimize the {section} section of the CV. {'Reduce the content if possible.' if reduce else ''}
                Focus on:
                1. Relevance to the job description.
                2. Consistency with personal information.
                3. Keeping bullet points between 75 and 95 characters.
                4. Maintaining LaTeX formatting.
                
                Return only the optimized LaTeX content for the section.
                """
            }],
            context_variables=optimization_context
        )
        
        optimized_content = response.messages[-1]["content"]
        self._save_section_content(section, optimized_content)

    def _identify_section_to_reduce(self):
        section_scores = {section: self._calculate_relevance_score(section, self._get_section_content(section)) for section in self.sections_to_reduce}
        return min(section_scores, key=section_scores.get) if section_scores else None

    def _calculate_relevance_score(self, section, content):
        prompt = f"""
        On a scale of 1-10, rate the relevance of this CV section for the given job description.
        Consider the importance of the section type and the specific content.

        Job Description:
        {self.processed_job_info}

        CV Section ({section}):
        {content}

        Rate (1-10):
        """

        try:
            response = self.openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert in CV evaluation and job matching."},
                    {"role": "user", "content": prompt}
                ]
            )
            score = int(response.choices[0].message.content.strip())
            logger.info(f"Relevance score for {section}: {score}")
            return score
        except Exception as e:
            logger.error(f"Error calculating relevance score for {section}: {str(e)}")
            return 5  # Default to middle score if there's an error

    def _reduce_section(self, section):
        return self._optimize_section(section, reduce=True)

    def _final_formatting_pass(self):
        for section in self.sections:
            content = self._get_section_content(section)
            optimized_content = adjust_bullet_point_lengths(content)
            self._save_section_content(section, optimized_content)

    def _get_section_content(self, section):
        section_file = os.path.join(self.output_dir, f"{section}.tex")
        try:
            with open(section_file, 'r') as file:
                return file.read()
        except FileNotFoundError:
            logger.warning(f"Section file {section_file} not found.")
            return ""

    def _save_section_content(self, section, content):
        with open(os.path.join(self.output_dir, f"{section}.tex"), 'w') as file:
            file.write(content)
        logger.info(f"Saved optimized content for section: {section}")
