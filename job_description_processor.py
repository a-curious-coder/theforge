import hashlib
import re
import json
from typing import Dict, List
import openai
import os
import sys
from loguru import logger
from config import config

class JobDescriptionProcessor:
    def __init__(self):
        self.logger = logger.bind(context="JobDescriptionProcessor")
        os.makedirs(config.LOG_DIR, exist_ok=True)
        log_file = os.path.join(config.LOG_DIR, "job_description_processor.log")
        self.logger.add(log_file, rotation="10 MB")
        self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)

    def _call_openai_api(self, prompt: str, system_content: str) -> str:
        response = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()

    def preprocess_job_description(self, job_description: str) -> Dict[str, List[str]]:
        self.logger.info("Starting job description preprocessing")
        prompt = f"""
        Analyze the following job description and extract key information to be used for CV generation:
        1. Essential Requirements (specific skills, qualifications, and experiences that are must-haves)
        2. Preferred Skills (specific additional skills or experiences that would be beneficial)
        3. Key Responsibilities (specific main duties and tasks of the role)
        4. Company Mission (specific goals, values, or vision of the company)
        5. Industry-Specific Terminology (specific important terms or jargon used in the field)
        6. Additional Relevant Information (any other specific details that could be useful for tailoring a CV)

        Provide concise, specific, and relevant items for each category, focusing on information that would be valuable for creating a targeted CV. Avoid vague or generic statements.

        Job Description:
        {job_description}

        Format response as JSON:
        {{
            "essential_requirements": ["specific_item1", "specific_item2", ...],
            "preferred_skills": ["specific_item1", "specific_item2", ...],
            "key_responsibilities": ["specific_item1", "specific_item2", ...],
            "company_mission": ["specific_item1", "specific_item2", ...],
            "industry_terminology": ["specific_term1", "specific_term2", ...],
            "additional_info": ["specific_item1", "specific_item2", ...]
        }}
        """
        self.logger.info("Sending request to OpenAI API for job description analysis")
        output = self._call_openai_api(prompt, "You are an expert in analyzing job descriptions and extracting specific, concise key information for CV tailoring.")
        return self._parse_json_response(output)

    def _parse_json_response(self, output: str) -> Dict[str, List[str]]:
        try:
            json_str = re.sub(r'^```json\s*|\s*```$', '', output.strip(), flags=re.MULTILINE)
            extracted_info = json.loads(json_str)
            self.logger.info("Successfully parsed JSON from OpenAI API response")
            return extracted_info
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from OpenAI API response: {e}")
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if match:
                try:
                    extracted_info = json.loads(match.group(0))
                    self.logger.info("Successfully extracted and parsed JSON from API response")
                    return extracted_info
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse extracted JSON-like structure")
            self.logger.error("No JSON-like structure found in the API response")
            return {}

    def get_job_title(self, job_description: str) -> str:
        self.logger.info("Starting job title extraction")
        patterns = [
            r"Job Title:\s*(.*)",
            r"Position:\s*(.*)",
            r"Role:\s*(.*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, job_description, re.IGNORECASE)
            if match:
                self.logger.info(f"Job title extracted using pattern: {pattern}")
                return match.group(1).strip()

        self.logger.info("No pattern match found, using OpenAI API for job title extraction")
        prompt = f"""
        Extract or generate a specific and appropriate job title from the following job description. 
        The title should be concise, precise, and reflective of the role described, suitable for use in a CV.

        Job Description:
        {job_description}

        Provide only the job title.
        """
        return self._call_openai_api(prompt, "You are an expert in analyzing job descriptions and extracting specific key information for CV creation.")

    def process_job_description(self, job_description: str) -> Dict[str, any]:
        self.logger.info("Starting job description processing for CV tailoring")
        
        job_hash = hashlib.md5(job_description.encode()).hexdigest()
        os.makedirs("job_descriptions", exist_ok=True)
        file_path = f"job_descriptions/{job_hash}.json"
        
        if os.path.exists(file_path):
            self.logger.info(f"Processed job description found at {file_path}")
            with open(file_path, 'r') as file:
                return json.load(file)
        
        processed_info = self.preprocess_job_description(job_description)
        processed_info['job_title'] = self.get_job_title(job_description)
        
        with open(file_path, 'w') as file:
            json.dump(processed_info, file, indent=2)
        
        self.logger.info(f"Job description processing completed and saved to {file_path}")
        return processed_info

def main():
    logger.info("Starting job description processor for CV tailoring")

    try:
        with open(config.JOB_DESCRIPTION_FILE, 'r') as file:
            job_description = file.read()
        logger.info(f"Job description read from {config.JOB_DESCRIPTION_FILE}")
    except (FileNotFoundError, IOError) as e:
        logger.error(f"Error reading file {config.JOB_DESCRIPTION_FILE}: {str(e)}")
        sys.exit(1)

    processor = JobDescriptionProcessor()
    processed_info = processor.process_job_description(job_description)

    output_file = config.get_job_description_processed_file()
    
    try:
        with open(output_file, 'w') as file:
            json.dump(processed_info, file, indent=2)
        logger.success(f"Processed job description exported to {output_file}")
    except IOError as e:
        logger.error(f"Error writing to file {output_file}: {str(e)}")

if __name__ == "__main__":
    main()
