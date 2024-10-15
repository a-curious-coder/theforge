import yaml
from utils import generate_section_content

def generate_work_experience_section(info, processed_job_info, template):
    prompt = f"""
    Generate the work experience section for a CV based on the following information and job requirements:

    Information:
    {yaml.dump(info)}

    Job Requirements:
    {yaml.dump(processed_job_info)}

    Template:
    {template}

    // ... rest of the prompt remains the same ...
    """
    return generate_section_content("Work Experience", prompt)