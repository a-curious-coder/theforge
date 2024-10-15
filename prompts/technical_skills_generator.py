import yaml

def get_technical_skills_prompt(info, job_description, template):
    return f"""
    Generate the technical skills section for a CV based on the following information and job description:

    Information:
    {yaml.dump(info)}

    Job Description:
    {job_description}

    Template:
    {template}

    Follow these guidelines:
    1. Match the exact formatting and structure of the template.
    2. Carefully analyze the job description and select ONLY the specific technical skills that directly align with it.
    3. Do not include skills that are not relevant to the specific job, even if they are in the provided information.
    4. List all skills in a single, unorganized list without categories.
    5. Order skills by their relevance to the job description.
    6. For each skill, include a brief indicator of proficiency level if appropriate and if the template allows.
    7. Ensure the LaTeX syntax is correct and complete.
    8. If the job description mentions specific versions or variations of technologies, list those exact versions.
    9. If certain skills are mentioned multiple times or emphasized in the job description, ensure they are prominently featured.
    10. Aim for a concise list of specific technical skills that demonstrates a strong match to the job requirements.
    11. Each listed skill must be a specific, individual technical skill (e.g., 'Python', 'Docker', 'TensorFlow'), not a broad category or description.
    """

# No changes needed for this file as it already only contains the get_technical_skills_prompt function
