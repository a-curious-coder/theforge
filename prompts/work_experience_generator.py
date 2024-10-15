import yaml

def get_work_experience_prompt(info, processed_job_info, template):
    return f"""
    Generate the work experience section for a CV based on the following information and job requirements:

    Information:
    {yaml.dump(info)}

    Job Requirements:
    {yaml.dump(processed_job_info)}

    Template:
    {template}

    Ensure the output:
    1. Matches the exact formatting and structure of the template.
    2. Highlights experiences most relevant to the job requirements.
    3. Uses action verbs and quantifies achievements where possible.
    4. Tailors the content to emphasize skills and experiences that match the job description.
    5. Contains correct and complete LaTeX syntax.
    6. Limits each bullet point to between 75 and 95 characters for readability.
    """
