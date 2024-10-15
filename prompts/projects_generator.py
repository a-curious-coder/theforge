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
    2. Carefully selects projects that are most aligned with the job description.
    3. Orders the selected projects from most relevant to least relevant.
    4. Includes an appropriate number of projects based on relevance, not to fill space.
    5. Highlights technologies and skills used that align with the job requirements.
    6. Uses bullet points to describe key features or implementation details.
    7. Contains correct and complete LaTeX syntax.
    8. Ensures bullet points are no shorter than 75 and no longer than 90 characters, including spaces.
    9. Avoids repetition of information across bullet points.
    10. Emphasizes the project's impact and your role in its development.
    """
    return generate_section_content("Projects", prompt)