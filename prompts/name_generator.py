def get_cv_name_prompt(job_description):
    return f"""
    Based on the following job description, generate a concise and descriptive filename for a CV.
    The filename should follow this format: [MainTechnology/Role]_[OptionalSpecialization]_CV
    
    For example:
    - Python_DataScience_CV
    - CSharp_FullStack_CV
    - JavaScript_Frontend_CV
    - Java_Backend_CV
    
    Ensure the filename is concise, relevant, and doesn't exceed 30 characters.
    Do not include any explanation, just return the filename.
    
    Job Description:
    {job_description}
    """
