import pytest
import os
import tempfile
import shutil
from dotenv import load_dotenv
from cv_reducer import CVReducer

# Load environment variables
load_dotenv()

@pytest.fixture
def cv_reducer():
    test_dir = os.path.join(tempfile.gettempdir(), "test_output")
    os.makedirs(test_dir, exist_ok=True)
    openai_api_key = os.getenv('OPENAI_API_KEY')
    job_role = 'Software Engineer'
    job_description = '''
    We are seeking a skilled Software Engineer to join our team. The ideal candidate should have:
    - Strong experience in Python and JavaScript
    - Familiarity with web frameworks like Django or Flask
    - Knowledge of database systems and SQL
    - Experience with version control systems, preferably Git
    - Good understanding of software design patterns and principles
    '''
    yield CVReducer(
        test_dir,
        job_description=job_description
    )
    shutil.rmtree(test_dir)

def create_test_section(cv_reducer, section_name, content):
    with open(os.path.join(cv_reducer.output_dir, f'{section_name}.tex'), 'w') as f:
        f.write(content)

def test_identify_section_to_reduce(cv_reducer):
    # Create test sections
    create_test_section(cv_reducer, 'technical_skills', r'''
    \section{Technical Skills}
    \begin{itemize}
        \item Python, JavaScript, C++
        \item Django, Flask, React
        \item PostgreSQL, MongoDB
        \item Docker, Kubernetes
        \item Machine Learning, TensorFlow
    \end{itemize}
    ''')
    create_test_section(cv_reducer, 'projects', r'''
    \section{Projects}
    \subsection{E-commerce Platform}
    \begin{itemize}
        \item Developed a full-stack e-commerce platform using Django and React
        \item Implemented secure payment processing with Stripe API
        \item Utilized Redis for caching to improve performance
    \end{itemize}
    \subsection{Data Analysis Tool}
    \begin{itemize}
        \item Created a data analysis tool using Python and Pandas
        \item Implemented data visualization features with Matplotlib
        \item Integrated machine learning models for predictive analytics
    \end{itemize}
    ''')
    create_test_section(cv_reducer, 'work_experience', r'''
    \section{Work Experience}
    \subsection{Senior Software Engineer, TechCorp (2018-2021)}
    \begin{itemize}
        \item Led a team of 5 developers in building a cloud-based SaaS solution
        \item Implemented CI/CD pipelines using Jenkins and Docker
        \item Reduced system downtime by 30% through optimizing database queries
    \end{itemize}
    \subsection{Software Developer, StartupX (2015-2018)}
    \begin{itemize}
        \item Developed and maintained multiple web applications using Django
        \item Implemented RESTful APIs for mobile app integration
        \item Collaborated with UX designers to improve user interface and experience
    \end{itemize}
    ''')

    # Mock the OpenAI API call to avoid hanging
    cv_reducer.openai_client.chat.completions.create = lambda **kwargs: type('obj', (object,), {'choices': [type('obj', (object,), {'message': {'content': 'technical_skills'}})()]})()

    section_to_reduce = cv_reducer.identify_section_to_reduce()
    assert section_to_reduce in ['technical_skills', 'projects', 'work_experience']

def test_reduce_section_content(cv_reducer):
    original_content = r'''
    \section{Technical Skills}
    \begin{itemize}
        \item Python, JavaScript, C++
        \item Django, Flask, React
        \item PostgreSQL, MongoDB
        \item Docker, Kubernetes
        \item Machine Learning, TensorFlow
    \end{itemize}
    '''
    create_test_section(cv_reducer, 'technical_skills', original_content)

    # Mock the OpenAI API call to avoid hanging
    cv_reducer.openai_client.chat.completions.create = lambda **kwargs: type('obj', (object,), {'choices': [type('obj', (object,), {'message': {'content': '\section{Technical Skills}\n\\begin{itemize}\n\\item Python, JavaScript\n\\item Django, React\n\\item PostgreSQL\n\\item Docker\n\\end{itemize}'}})()]})()

    cv_reducer.reduce_section('technical_skills')

    with open(os.path.join(cv_reducer.output_dir, 'technical_skills.tex'), 'r') as f:
        reduced_content = f.read()

    assert reduced_content != original_content
    assert len(reduced_content) < len(original_content)

def test_reduce_content(cv_reducer, monkeypatch):
    # Mock the get_pdf_pages method to simulate a 2-page CV
    monkeypatch.setattr(cv_reducer, "get_pdf_pages", lambda: 2)

    # Create test sections
    create_test_section(cv_reducer, 'technical_skills', r'''
    \section{Technical Skills}
    \begin{itemize}
        \item Python, JavaScript, C++
        \item Django, Flask, React
        \item PostgreSQL, MongoDB
        \item Docker, Kubernetes
        \item Machine Learning, TensorFlow
    \end{itemize}
    ''')
    create_test_section(cv_reducer, 'projects', r'''
    \section{Projects}
    \subsection{E-commerce Platform}
    \begin{itemize}
        \item Developed a full-stack e-commerce platform using Django and React
        \item Implemented secure payment processing with Stripe API
        \item Utilized Redis for caching to improve performance
    \end{itemize}
    \subsection{Data Analysis Tool}
    \begin{itemize}
        \item Created a data analysis tool using Python and Pandas
        \item Implemented data visualization features with Matplotlib
        \item Integrated machine learning models for predictive analytics
    \end{itemize}
    ''')
    create_test_section(cv_reducer, 'work_experience', r'''
    \section{Work Experience}
    \subsection{Senior Software Engineer, TechCorp (2018-2021)}
    \begin{itemize}
        \item Led a team of 5 developers in building a cloud-based SaaS solution
        \item Implemented CI/CD pipelines using Jenkins and Docker
        \item Reduced system downtime by 30% through optimizing database queries
    \end{itemize}
    \subsection{Software Developer, StartupX (2015-2018)}
    \begin{itemize}
        \item Developed and maintained multiple web applications using Django
        \item Implemented RESTful APIs for mobile app integration
        \item Collaborated with UX designers to improve user interface and experience
    \end{itemize}
    ''')

    # Mock the compile_pdf method
    monkeypatch.setattr(cv_reducer, "compile_pdf", lambda: None)

    # Mock the OpenAI API call to avoid hanging
    cv_reducer.openai_client.chat.completions.create = lambda **kwargs: type('obj', (object,), {'choices': [type('obj', (object,), {'message': {'content': 'technical_skills'}})()]})()

    # Run the reduce_content method
    cv_reducer.reduce_content()

    # Check if any section has been reduced
    reduced_sections = 0
    for section in ['technical_skills', 'projects', 'work_experience']:
        with open(os.path.join(cv_reducer.output_dir, f'{section}.tex'), 'r') as f:
            content = f.read()
        if len(content) < len(cv_reducer.get_section_content(section)):
            reduced_sections += 1

    assert reduced_sections > 0