import yaml
import os
import re
import subprocess
import pypdf
import shutil
import argparse
from loguru import logger
from dotenv import load_dotenv
from typing import Dict, List, Optional
from openai import OpenAI

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    logger.critical("OPENAI_API_KEY environment variable is not set")
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger.disable("openai")
logger.disable("openai.http_client")

def load_yaml(file_path: str) -> Dict:
    try:
        with open(file_path, 'r') as file:
            logger.debug(f"Loading YAML file from {file_path}")
            return yaml.safe_load(file)
    except (yaml.YAMLError, FileNotFoundError) as e:
        logger.error(f"Error loading YAML from {file_path}: {e}")
        return {}

def load_template(file_path: str) -> str:
    try:
        logger.debug(f"Loading template from {file_path}")
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"Template file not found: {file_path}")
        return ""

def validate_latex_syntax(content: str) -> bool:
    try:
        brace_count = sum(1 if char == '{' else -1 if char == '}' else 0 for char in content)
        if brace_count != 0:
            logger.warning("Mismatched braces detected")
            return False

        common_commands = [r'\\begin', r'\\end', r'\\section', r'\\subsection', r'\\textbf', r'\\textit', r'\\item']
        for command in common_commands:
            if content.count(command + '{') != content.count(command + '}'):
                logger.warning(f"Mismatched {command} commands detected")
                return False

        environments = re.findall(r'\\begin\{(\w+)\}', content)
        for env in environments:
            if content.count(r'\\begin{' + env + '}') != content.count(r'\\end{' + env + '}'):
                logger.warning(f"Mismatched {env} environment detected")
                return False

        undefined_environments = ['multicols']
        for env in undefined_environments:
            if r'\\begin{' + env + '}' in content or r'\\end{' + env + '}' in content:
                logger.warning(f"Undefined environment {env} detected")
                return False

        logger.success("LaTeX syntax validation passed")
        return True
    except Exception as e:
        logger.error(f"Error in validate_latex_syntax: {str(e)}")
        return False

def fix_latex_syntax(content: str) -> str:
    logger.info("Attempting to fix LaTeX syntax")
    fixed_content = content

    brace_count = sum(1 if char == '{' else -1 if char == '}' else 0 for char in fixed_content)
    fixed_content = '{' * max(0, -brace_count) + fixed_content + '}' * max(0, brace_count)

    common_commands = ['\\\\begin', '\\\\end', '\\\\section', '\\\\subsection', '\\\\textbf', '\\\\textit', '\\\\item']
    for command in common_commands:
        fixed_content = re.sub(rf'{command}\s*([^{{}}]+)', rf'{command}{{\1}}', fixed_content)

    environments = re.findall(r'\\begin\{(\w+)\}', fixed_content)
    for env in environments:
        if fixed_content.count(r'\\begin{' + env + '}') > fixed_content.count(r'\\end{' + env + '}'):
            fixed_content += r'\\end{' + env + '}'

    undefined_environments = ['multicols']
    for env in undefined_environments:
        fixed_content = re.sub(r'\\begin\{' + env + r'\}.*?\\end\{' + env + r'\}', '', fixed_content, flags=re.DOTALL)
        fixed_content = fixed_content.replace(r'\\begin{' + env + '}', '').replace(r'\\end{' + env + '}', '')

    logger.success("LaTeX syntax fixed")
    return fixed_content

def adjust_bullet_point_lengths(content: str) -> str:
    logger.info("Adjusting bullet point lengths")
    lines = content.split('\n')
    adjusted_lines = []
    for line in lines:
        if line.strip().startswith(r'\item[$\bullet$] '):
            bullet_point = line.strip()[17:].strip().lstrip('-').strip()
            if len(bullet_point) < 75 or len(bullet_point) > 95:
                adjusted_bullet = adjust_bullet_point(bullet_point).strip('[$\\bullet$]')
                if adjusted_bullet:
                    adjusted_lines.append(f"    \\item[$\\bullet$] {adjusted_bullet}")
            else:
                adjusted_lines.append(f"    \\item[$\\bullet$] {bullet_point}")
        else:
            adjusted_lines.append(line)
    logger.success("Bullet point lengths adjusted")
    return '\n'.join(adjusted_lines)

def adjust_bullet_point(bullet_point: str) -> str:
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            logger.debug(f"Adjusting bullet point, attempt {attempt + 1}")
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL"),
                messages=[
                    {"role": "system", "content": "You are an expert in CV writing. Adjust the given bullet point to be between 75 and 95 characters while maintaining its key information and ensuring high quality."},
                    {"role": "user", "content": f"Adjust this bullet point to be between 75 and 95 characters: {bullet_point}"}
                ]
            )
            adjusted_bullet = response.choices[0].message.content.strip().lstrip('-').strip()
            if 75 <= len(adjusted_bullet) <= 95:
                logger.success("Bullet point adjusted successfully")
                return adjusted_bullet
        except Exception as e:
            logger.error(f"Error adjusting bullet point: {str(e)}")
    
    try:
        logger.warning("Failed to adjust bullet point, generating new one")
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL"),
            messages=[
                {"role": "system", "content": "You are an expert in CV writing. Generate a new, high-quality bullet point based on the theme of the given one, ensuring it's between 75 and 95 characters."},
                {"role": "user", "content": f"Generate a new bullet point based on this theme, but make it between 75 and 95 characters: {bullet_point}"}
            ]
        )
        new_bullet = response.choices[0].message.content.strip().lstrip('-').strip()
        if 75 <= len(new_bullet) <= 95:
            logger.success("New bullet point generated successfully")
            return new_bullet
        else:
            logger.warning("Generated bullet point out of range, returning original")
            return bullet_point.lstrip('-').strip()
    except Exception as e:
        logger.error(f"Error generating new bullet point: {str(e)}")
        return bullet_point.lstrip('-').strip()

def load_job_description(file_path: str) -> str:
    try:
        with open(file_path, 'r') as file:
            logger.debug(f"Loading job description from {file_path}")
            return file.read().strip()
    except FileNotFoundError:
        logger.error(f"Job description file not found: {file_path}")
        return ""

def get_pdf_pages(pdf_path: str) -> Optional[int]:
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = pypdf.PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)
            logger.info(f"PDF {pdf_path} has {page_count} pages")
            return page_count
    except Exception as e:
        logger.error(f"Error reading PDF file {pdf_path}: {str(e)}")
        return None

def compile_latex(output_dir: str) -> Optional[int]:
    try:
        logger.info(f"Compiling LaTeX in {output_dir}")
        result = subprocess.run(['pdflatex', 'main.tex'], check=True, cwd=output_dir, capture_output=True, text=True)
        
        pdf_path = os.path.join(output_dir, 'main.pdf')
        if os.path.exists(pdf_path):
            page_count = get_pdf_pages(pdf_path)
            if page_count:
                return page_count
            else:
                logger.error("Failed to get page count")
                return None
        else:
            logger.error("PDF file not found after compilation")
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"LaTeX compilation failed: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error during LaTeX compilation: {str(e)}")
        return None

def move_cv_to_output(output_dir: str, cv_name: str) -> None:
    cv_dir = 'CVs'
    os.makedirs(cv_dir, exist_ok=True)
    pdf_file = next((f for f in os.listdir(output_dir) if f.endswith('.pdf')), None)
    if pdf_file:
        new_pdf_name = f"{cv_name}.pdf"
        shutil.move(os.path.join(output_dir, pdf_file), os.path.join(cv_dir, new_pdf_name))
        logger.success(f"CV generated and saved as {new_pdf_name} in the CVs directory")
    else:
        logger.error("PDF file not found, unable to move")

def main():
    parser = argparse.ArgumentParser(description="Utility functions for CV generation")
    parser.add_argument("function", choices=[
        "load_yaml", "load_template", "generate_section_content", 
        "validate_latex_syntax", "fix_latex_syntax", "adjust_bullet_point_lengths",
        "load_job_description", "compile_latex", "move_cv_to_output"
    ], help="Function to execute")
    parser.add_argument("--file", help="Path to the file (for functions that require a file path)")
    parser.add_argument("--content", help="Content string (for functions that require content)")
    parser.add_argument("--section", help="Section name (for generate_section_content)")
    parser.add_argument("--output_dir", help="Output directory (for compile_latex, move_cv_to_output)")
    parser.add_argument("--cv_name", help="CV name (for move_cv_to_output)")
    
    args = parser.parse_args()

    function_map = {
        "load_yaml": lambda: load_yaml(args.file),
        "load_template": lambda: load_template(args.file),
        "generate_section_content": lambda: generate_section_content(args.section, args.content),
        "validate_latex_syntax": lambda: validate_latex_syntax(args.content),
        "fix_latex_syntax": lambda: fix_latex_syntax(args.content),
        "adjust_bullet_point_lengths": lambda: adjust_bullet_point_lengths(args.content),
        "load_job_description": lambda: load_job_description(args.file),
        "compile_latex": lambda: compile_latex(args.output_dir),
        "move_cv_to_output": lambda: move_cv_to_output(args.output_dir, args.cv_name)
    }

    if args.function in function_map:
        result = function_map[args.function]()
        if result is not None:
            logger.info(f"Result: {result}")
    else:
        logger.error(f"Unknown function {args.function}")

if __name__ == "__main__":
    main()
