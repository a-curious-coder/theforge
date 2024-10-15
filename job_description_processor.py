import hashlib
import re
import json
from typing import Dict, List
import openai
import sys
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

logger.add("job_description_processor.log", rotation="10 MB")

def preprocess_job_description(job_description: str) -> Dict[str, List[str]]:
    """
    Preprocess the job description to extract key information.
    
    Args:
    job_description (str): The raw job description text.
    
    Returns:
    Dict[str, List[str]]: A dictionary containing structured information from the job description.
    """
    logger.info("Starting job description preprocessing")
    # Use GPT-4 to extract and structure the information
    prompt = f"""
    Analyze the following job description and extract the following information:
    1. Essential Requirements
    2. Preferred Skills
    3. Key Responsibilities
    4. Company Mission
    5. Industry-Specific Terminology
    6. Additional Relevant Information

    For each category, provide a list of items. Keep each item concise and relevant.

    Job Description:
    {job_description}

    Please format your response as a JSON object with the following structure:
    {{
        "essential_requirements": ["item1", "item2", ...],
        "preferred_skills": ["item1", "item2", ...],
        "key_responsibilities": ["item1", "item2", ...],
        "company_mission": ["item1", "item2", ...],
        "additional_info": ["item1", "item2", ...]
    }}
    """

    logger.info("Sending request to OpenAI API")
    response = openai.ChatCompletion.create(
        model=os.getenv("OPENAI_MODEL"),
        messages=[
            {"role": "system", "content": "You are an expert in analyzing job descriptions and extracting key information."},
            {"role": "user", "content": prompt}
        ]
    )
    output = response.choices[0].message['content']
    # Extract JSON from the output string
    try:
        # Remove the "```json" prefix and "```" suffix if present
        json_str = re.sub(r'^```json\s*|\s*```$', '', output.strip(), flags=re.MULTILINE)
        extracted_info = json.loads(json_str)
        logger.info("Successfully parsed JSON from OpenAI API response")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI API response: {e}")
        # Attempt to extract JSON-like structure from the string
        match = re.search(r'\{.*\}', output, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                extracted_info = json.loads(json_str)
                logger.info("Successfully extracted and parsed JSON from API response")
            except json.JSONDecodeError:
                logger.error("Failed to parse extracted JSON-like structure")
                extracted_info = {}
        else:
            logger.error("No JSON-like structure found in the API response")
            extracted_info = {}

    logger.info("Job description preprocessing completed")
    return extracted_info

def get_job_title(job_description: str) -> str:
    """
    Extract the job title from the job description.
    
    Args:
    job_description (str): The raw job description text.
    
    Returns:
    str: The extracted job title.
    """
    logger.info("Starting job title extraction")
    # Look for common patterns in job titles
    patterns = [
        r"Job Title:\s*(.*)",
        r"Position:\s*(.*)",
        r"Role:\s*(.*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, job_description, re.IGNORECASE)
        if match:
            logger.info(f"Job title extracted using pattern: {pattern}")
            return match.group(1).strip()

    logger.info("No pattern match found, using OpenAI API for job title extraction")
    # If no pattern matches, use GPT-4 to extract the job title
    prompt = f"""
    Extract the job title from the following job description. Provide only the job title, nothing else. 
    If you cannot locate a job title, write a job title that best reflects the job description.

    Job Description:
    {job_description}
    """

    response = openai.ChatCompletion.create(
        model=os.getenv("OPENAI_MODEL"),
        messages=[
            {"role": "system", "content": "You are an expert in analyzing job descriptions and extracting key information."},
            {"role": "user", "content": prompt}
        ]
    )

    logger.info("Job title extraction completed")
    return response.choices[0].message['content'].strip()

def process_job_description(job_description: str) -> Dict[str, any]:
    """
    Process the job description to extract all relevant information.
    
    Args:
    job_description (str): The raw job description text.
    
    Returns:
    Dict[str, any]: A dictionary containing all processed information from the job description.
    """
    logger.info("Starting job description processing")
    
    # Create a hash of the job description
    job_hash = hashlib.md5(job_description.encode()).hexdigest()
    
    # Create the job_descriptions folder if it doesn't exist
    os.makedirs("job_descriptions", exist_ok=True)
    
    # Define the file path
    file_path = f"job_descriptions/{job_hash}.json"
    
    # Check if the file already exists
    if os.path.exists(file_path):
        logger.info(f"Processed job description found at {file_path}")
        with open(file_path, 'r') as file:
            return json.load(file)
    
    # If not, process the job description
    processed_info = preprocess_job_description(job_description)
    job_title = get_job_title(job_description)
    
    processed_info['job_title'] = job_title
    
    # Save the processed information
    with open(file_path, 'w') as file:
        json.dump(processed_info, file, indent=2)
    
    logger.info(f"Job description processing completed and saved to {file_path}")
    return processed_info

if __name__ == "__main__":
    logger.info("Starting job description processor")
    if len(sys.argv) != 2:
        logger.error("Usage: python job_description_processor.py <path_to_job_description_file>")
        sys.exit(1)

    job_description_file = sys.argv[1]
    
    try:
        with open(job_description_file, 'r') as file:
            job_description = file.read()
        logger.info(f"Job description read from {job_description_file}")
    except (FileNotFoundError, IOError) as e:
        logger.error(f"Error reading file {job_description_file}: {str(e)}")
        sys.exit(1)

    processed_info = process_job_description(job_description)
    print(json.dumps(processed_info, indent=2))

    # Export the enhanced description
    output_file = f"{os.path.splitext(job_description_file)[0]}_processed.json"
    try:
        with open(output_file, 'w') as file:
            json.dump(processed_info, file, indent=2)
        logger.info(f"Processed job description exported to {output_file}")
    except IOError as e:
        logger.error(f"Error writing to file {output_file}: {str(e)}")