import yaml
from utils import generate_section_content

def generate_technical_skills_section(info, job_description, template):
    prompt = f"""
    Generate the technical skills section for a CV based on the following information and job description:

    Information:
    {yaml.dump(info)}

    Job Description:
    {job_description}

    Template:
    {template}

    Follow these guidelines:
    1. Match the exact formatting and structure of the template.
    2. Prioritize skills that are most relevant to the job description.
    3. Group skills by category if the template allows.
    4. List skills in order of proficiency or relevance to the job.
    5. Ensure the LaTeX syntax is correct and complete.
    """
    return generate_section_content("Technical Skills", prompt)