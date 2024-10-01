import yaml
from utils import generate_section_content

def generate_work_experience_section(info, job_description, template):
    prompt = f"""
    Generate the work experience section for a CV based on the following information and job description:

    Information:
    {yaml.dump(info)}

    Job Description:
    {job_description}

    Template:
    {template}

    Follow these guidelines:
    1. Match the exact formatting and structure of the template.
    2. Begin each bullet point with an action verb.
    3. Quantify achievements with specific metrics when possible.
    4. Tailor experiences to highlight skills relevant to the job description.
    5. Use the exact date format shown in the template.
    6. Limit to the most relevant and recent work experiences.
    7. Ensure the LaTeX syntax is correct and complete.
    8. Ensure bullet points are no shorter than 75 and no longer than 95 characters, including spaces.
    9. Avoid repetition of information across bullet points.
    """
    return generate_section_content("Work Experience", prompt)