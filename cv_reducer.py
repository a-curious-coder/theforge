import os
import logging
import subprocess
import PyPDF2
import shutil
import openai
import yaml

class CVReducer:
    def __init__(self, output_dir, max_pages=1, openai_api_key=None):
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.sections_to_reduce = ['technical_skills', 'projects', 'work_experience', 'education']
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        openai.api_key = self.openai_api_key

    def reduce_content(self, current_pages):
        for section in self.sections_to_reduce:
            if current_pages <= self.max_pages:
                break
            
            logging.info(f"Reducing content in {section} section")
            self.reduce_section(section)
            self.compile_pdf()

            current_pages = self.get_pdf_pages()

        if current_pages > self.max_pages:
            logging.warning(f"Unable to reduce CV to {self.max_pages} pages. Final page count: {current_pages}")

    def reduce_section(self, section):
        with open(f'{section}.tex', 'r') as file:
            content = file.read()
        
        lines = content.split('\n')
        
        if section == 'technical_skills':
            lines = self.reduce_technical_skills(lines)
        elif section in ['projects', 'work_experience', 'education']:
            lines = self.reduce_section_with_ai(section, lines)
        
        with open(f'{section}.tex', 'w') as file:
            file.write('\n'.join(lines))

    def reduce_technical_skills(self, lines):
        # Remove the last skill (existing logic)
        skill_index = len(lines) - 1 - next(i for i, line in enumerate(reversed(lines)) if r'\item' in line)
        del lines[skill_index]
        return lines

    def reduce_section_with_ai(self, section, lines):
        # Extract items (bullet points or entire sections)
        items = self.extract_items(lines)
        
        # Use OpenAI to rank items by importance
        ranked_items = self.rank_items_with_ai(section, items)
        
        # Remove the least important item
        del ranked_items[-1]
        
        # Reconstruct the section with remaining items
        return self.reconstruct_section(lines, ranked_items)

    def extract_items(self, lines):
        items = []
        current_item = []
        for line in lines:
            if r'\section' in line or r'\subsection' in line:
                if current_item:
                    items.append('\n'.join(current_item))
                    current_item = []
                current_item.append(line)
            elif r'\item' in line:
                if current_item:
                    items.append('\n'.join(current_item))
                current_item = [line]
            else:
                current_item.append(line)
        if current_item:
            items.append('\n'.join(current_item))
        return items

    def rank_items_with_ai(self, section, items):
        prompt = f"Rank the following {section} items from most important to least important for a CV, considering relevance and impact:\n\n"
        for i, item in enumerate(items):
            prompt += f"{i+1}. {item}\n\n"
        prompt += "Return the ranked list of item numbers, separated by commas."

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that ranks CV items by importance."},
                {"role": "user", "content": prompt}
            ]
        )

        ranked_indices = [int(x.strip()) - 1 for x in response.choices[0].message['content'].split(',')]
        return [items[i] for i in ranked_indices]

    def reconstruct_section(self, original_lines, ranked_items):
        new_lines = []
        for line in original_lines:
            if r'\section' in line or r'\subsection' in line:
                if any(item.startswith(line) for item in ranked_items):
                    new_lines.append(line)
            elif r'\item' in line:
                if any(item.strip() == line.strip() for item in ranked_items):
                    new_lines.append(line)
            else:
                new_lines.append(line)
        return new_lines

    def compile_pdf(self):
        current_dir = os.getcwd()
        # os.chdir(self.output_dir)
        try:
            subprocess.run(['pdflatex', '-interaction=nonstopmode', '-output-directory=.', 'main.tex'], capture_output=True, text=True)
        finally:
            os.chdir(current_dir)

    def get_pdf_pages(self):
        pdf_path = os.path.join('main.pdf')
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return len(pdf_reader.pages)

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Load OpenAI API key from info.yml
    with open('info.yml', 'r') as file:
        info = yaml.safe_load(file)
        openai_api_key = info.get('openai_api_key')

    # Create a temporary directory for the demonstration
    temp_dir = 'cv_template'

    try:
        # Copy the cv_template contents to the temporary directory
        for item in os.listdir('cv_template'):
            s = os.path.join('cv_template', item)
            d = os.path.join(temp_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

        # Change to the temporary directory
        os.chdir(temp_dir)

        # Create an instance of CVReducer with OpenAI API key
        reducer = CVReducer('.', max_pages=1, openai_api_key=openai_api_key)

        # Compile the initial PDF
        reducer.compile_pdf()

        # Get the initial page count
        initial_pages = reducer.get_pdf_pages()
        logging.info(f"Initial CV has {initial_pages} pages")

        # Reduce content if necessary
        if initial_pages > reducer.max_pages:
            reducer.reduce_content(initial_pages)

        # Get the final page count
        final_pages = reducer.get_pdf_pages()
        logging.info(f"Final CV has {final_pages} pages")

    finally:
        # Change back to the original directory
        os.chdir('..')

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()