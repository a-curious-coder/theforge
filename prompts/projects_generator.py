import yaml
from utils import generate_section_content

def generate_projects_section(info, job_description, template):
    prompt = f"""
    Generate only the LaTeX output for the projects section of a CV based on the following information and job description:

    Information:
    {yaml.dump(info)}

    Job Description:
    {job_description}

    Template:
    {template}

    Ensure the output:
    1. Matches the exact formatting and structure of the template.
    2. Includes only the most relevant projects to the job description.
    3. Highlights technologies and skills used that align with the job requirements.
    4. Uses bullet points to describe key features or implementation details.
    5. Omits projects that aren't relevant unless needed to fill whitespace.
    6. Contains correct and complete LaTeX syntax.
    7. Ensure bullet points are no shorter than 75 and no longer than 95 characters, including spaces.
    8. Avoid repetition of information across bullet points.
    """
    return generate_section_content("Projects", prompt)