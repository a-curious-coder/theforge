import yaml

def get_education_prompt(info, job_description, template):
    return f"""
    Generate only the LaTeX output for the education section of a CV based on the following information and job description:

    Information:
    {yaml.dump(info)}

    Job Description:
    {job_description}

    Template:
    {template}

    Ensure the output:
    1. Matches the exact formatting and structure of the template.
    2. Includes relevant coursework and achievements that align with the job description.
    3. Uses the exact date format shown in the template.
    4. Limits to the most relevant and recent educational experiences.
    5. Contains correct and complete LaTeX syntax.
    """
