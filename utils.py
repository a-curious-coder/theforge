import yaml
import logging
import os
import re
import openai
import subprocess

def load_yaml(file_path):
    try:
        with open(file_path, 'r') as file:
            logging.debug(f"Loading YAML file from {file_path}.")
            content = file.read()
            return yaml.safe_load(content)
    except yaml.YAMLError as e:
        logging.error(f"Error loading YAML from {file_path}: {e}")
        return {}

def load_template(file_path):
    logging.debug(f"Loading template from {file_path}.")
    with open(file_path, 'r') as file:
        return file.read()

def generate_section_content(section_name, prompt):
    logging.debug(f"Generating section for {section_name}.")
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a LaTeX expert tasked with generating CV sections that exactly match given templates. Ensure all LaTeX syntax is correct and complete."},
            {"role": "user", "content": prompt}
        ]
    )

    generated_content = response.choices[0].message['content'].strip('`').strip('latex')
    
    # Validate LaTeX syntax
    if not validate_latex_syntax(generated_content):
        logging.warning(f"Invalid LaTeX syntax detected in {section_name} section. Attempting to fix...")
        generated_content = fix_latex_syntax(generated_content)
    
    # Check and adjust bullet point lengths
    if section_name in ["Work Experience", "Projects"]:
        generated_content = adjust_bullet_point_lengths(generated_content)
    
    logging.info(f"Section for {section_name} generated successfully.")
    generated_content = generated_content.replace('#', r'\#')
    return generated_content.replace(r'\\#', r'\#')

def validate_latex_syntax(content):
    try:
        # Check for balanced braces
        brace_count = 0
        for char in content:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            if brace_count < 0:
                return False
        if brace_count != 0:
            return False

        # Check for common LaTeX commands
        common_commands = [r'\\begin', r'\\end', r'\\section', r'\\subsection', r'\\textbf', r'\\textit', r'\\item']
        for command in common_commands:
            if command in content and not content.count(command + '{') == content.count(command + '}'):
                return False

        # Check for unclosed environments
        environments = re.findall(r'\\begin\{(\w+)\}', content)
        for env in environments:
            if content.count(r'\\begin{' + env + '}') != content.count(r'\\end{' + env + '}'):
                return False

        # Check for undefined environments (like multicols)
        undefined_environments = ['multicols']
        for env in undefined_environments:
            if r'\\begin{' + env + '}' in content or r'\\end{' + env + '}' in content:
                return False

        return True
    except Exception as e:
        logging.error(f"Error in validate_latex_syntax: {str(e)}")
        return False

def fix_latex_syntax(content):
    fixed_content = content

    # Balance braces
    brace_count = 0
    for char in fixed_content:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
    if brace_count > 0:
        fixed_content += '}' * brace_count
    elif brace_count < 0:
        fixed_content = '{' * abs(brace_count) + fixed_content

    # Fix common LaTeX commands
    common_commands = ['\\\\begin', '\\\\end', '\\\\section', '\\\\subsection', '\\\\textbf', '\\\\textit', '\\\\item']
    for command in common_commands:
        fixed_content = re.sub(rf'{command}\s*([^{{}}]+)', rf'{command}{{\1}}', fixed_content)

    # Close unclosed environments
    environments = re.findall(r'\\begin\{(\w+)\}', fixed_content)
    for env in environments:
        if fixed_content.count(r'\\begin{' + env + '}') > fixed_content.count(r'\\end{' + env + '}'):
            fixed_content += r'\\end{' + env + '}'

    # Remove undefined environments (like multicols)
    undefined_environments = ['multicols']
    for env in undefined_environments:
        fixed_content = re.sub(r'\\begin\{' + env + r'\}.*?\\end\{' + env + r'\}', '', fixed_content, flags=re.DOTALL)
        fixed_content = fixed_content.replace(r'\\begin{' + env + '}', '')
        fixed_content = fixed_content.replace(r'\\end{' + env + '}', '')

    return fixed_content

def adjust_bullet_point_lengths(content):
    lines = content.split('\n')
    adjusted_lines = []
    for line in lines:
        if line.strip().startswith(r'\item[$\bullet$] '):
            bullet_point = line.strip()[17:].strip()  # Remove '\item' and leading/trailing spaces
            bullet_point = bullet_point.lstrip('-').strip()  # Remove hyphen and leading whitespace
            if len(bullet_point) < 75 or len(bullet_point) > 95:
                adjusted_bullet = adjust_bullet_point(bullet_point).strip('[$\\bullet$]')
                if adjusted_bullet != "":
                    adjusted_lines.append(f"    \\item[$\\bullet$] {adjusted_bullet}")
            else:
                adjusted_lines.append(f"    \\item[$\\bullet$] {bullet_point}")
        else:
            adjusted_lines.append(line)
    return '\n'.join(adjusted_lines)

def adjust_bullet_point(bullet_point):
    max_attempts = 3
    for _ in range(max_attempts):
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in CV writing. Adjust the given bullet point to be between 75 and 95 characters while maintaining its key information and ensuring high quality."},
                {"role": "user", "content": f"Adjust this bullet point to be between 75 and 95 characters: {bullet_point}"}
            ]
        )
        adjusted_bullet = response.choices[0].message['content'].strip()
        adjusted_bullet = adjusted_bullet.lstrip('-').strip()  # Remove hyphen and leading whitespace
        if 75 <= len(adjusted_bullet) <= 95:
            return adjusted_bullet
    
    # If we can't adjust it after multiple attempts, generate a new bullet point
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert in CV writing. Generate a new, high-quality bullet point based on the theme of the given one, ensuring it's between 75 and 95 characters."},
            {"role": "user", "content": f"Generate a new bullet point based on this theme, but make it between 75 and 95 characters: {bullet_point}"}
        ]
    )
    new_bullet = response.choices[0].message['content'].strip()
    new_bullet = new_bullet.lstrip('-').strip()  # Remove hyphen and leading whitespace
    if 75 <= len(new_bullet) <= 95:
        return new_bullet
    else:
        # If all else fails, return the original bullet point
        return bullet_point.lstrip('-').strip()

def build_latex_project(output_dir):
    current_dir = os.getcwd()
    logging.info(f"Current working directory: {current_dir}")
    os.chdir(output_dir)
    logging.info(f"Building project in {output_dir}.")
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        # Run pdflatex command to compile the LaTeX document
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-output-directory=.', 'main.tex'],
            capture_output=True,
            text=True
        )
        
        # Log the command being executed
        logging.info("Executing pdflatex command: pdflatex -interaction=nonstopmode -output-directory=. main.tex")
        
        # Log the stdout and stderr of the pdflatex command
        logging.debug(f"pdflatex stdout: {result.stdout}")
        logging.debug(f"pdflatex stderr: {result.stderr}")
        
        # Check if the PDF file was created successfully
        if os.path.isfile('main.pdf'):
            logging.info(f"PDF file 'main.pdf' has been successfully created in {output_dir}.")
            os.chdir(current_dir)
            return True
        else:
            logging.error(f"Attempt {attempt} failed. Error building project:")
            logging.error(result.stderr)
            
            if attempt < max_attempts:
                user_input = input(f"Attempt {attempt} failed. Do you want to try again? (y/n): ")
                if user_input.lower() != 'y':
                    break
            else:
                logging.error("Maximum attempts reached. Failed to build project.")
    
    os.chdir(current_dir)
    return False

def load_job_description(file_path):
    try:
        with open(file_path, 'r') as file:
            logging.debug(f"Loading job description from {file_path}.")
            return file.read().strip()
    except FileNotFoundError:
        logging.error(f"Job description file not found: {file_path}")
        return ""
