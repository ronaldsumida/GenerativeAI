import os, json
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.message import Message

MODEL='gpt-5.4-mini'

# Initialize the path to the data subdirectories
current_dir = os.path.dirname(os.path.abspath(__file__))
applicants_path = os.path.join(current_dir, 'applicants')
jobs_path = os.path.join(current_dir, 'jobs')

# Function for retrieving a list of job applicants
def list_job_applicants() -> list:
    '''
    Retrieves the names of all current job applicants.
    Returns:
        List of strings containing the names of job applicants.
    '''

    applicants = []
    
    for filename in os.listdir(applicants_path):
        if not filename.lower().endswith('.md'):
            continue

        name = os.path.splitext(filename)[0] # Strip the file-name extension
        applicants.append(name)

    return applicants

# Function for retrieving a job applicant's resume
def get_resume(name: str) -> dict:
    '''
    Retrieves the resume of the specified job applicant.
    Args:
        name: Job applicant's name.
    Returns:
        Dictionary containing the applicant's name and resume.
    '''

    filename = os.path.join(applicants_path, f'{name}.md')

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    return { 'name': name, 'resume': content }

# Function for retrieving a list of job titles
def list_job_titles() -> list:
    '''
    Retrieves all current job titles.
    Returns:
        List of strings containing job titles.
    '''

    jobs = []

    for filename in os.listdir(jobs_path):
        if not filename.lower().endswith('.md'):
            continue

        title = os.path.splitext(filename)[0] # Strip the file-name extension
        jobs.append(title)

    return jobs

# Function for retrieving a job description
def get_job_description(title: str) -> dict:
    '''
    Retrieves the job description for the specified job title.
    Args:
        title: Job title.
    Returns:
        Dictionary containing the job title and job description.
    '''

    filename = os.path.join(jobs_path, f'{title}.md')

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    return { 'title': title, 'description': content }

# Function for evaluating an applicant for a job
def evaluate_applicant(name: str, title: str) -> dict:
    '''
    Evaluates an applicant for a job and returns a score from 0.0 to 10.0
    along with an explanation of that score.
    Args:
        name: Applicant's name
        title: Job title
    Returns:
        Dictionary containing a score and an explanation of the score in
        the following format:   
        {
            "score": NUMERIC_SCORE,
            "explanation": "EXPLANATION_OF_SCORE"
        }
    '''

    resume = get_resume(name)['resume']
    description = get_job_description(title)['description']

    SYSTEM_PROMPT = '''
        You are a hiring expert who evaluates a job applicant's fitness for a
        job and returns a score from 0.0 to 10.0, where a higher score reflects
        higher fitness for the job. Be critical; make it difficult to earn a high
        score. Always provide a textual summary explaining the score. Return a
        JSON response using the following format:

        {
            "score": NUMERIC_SCORE,
            "explanation": "EXPLANATION_OF_SCORE"
        }
        '''

    USER_PROMPT = f'''
        {name} is applying for the position of {title}.
        Here is his or her resume:

        [START RESUME]
        {resume}
        [END RESUME]

        Here's the job description:

        [START JOB DESCRIPTION]
        {description}
        [END JOB DESCRIPTION]

        Evaluate the applicant for this position.
        '''

    messages = [
        Message(role='system', content=SYSTEM_PROMPT),
        Message(role='user', content=USER_PROMPT)
    ]

    model=OpenAIChat(id=MODEL, temperature=0.2)
    response = model.response(messages)

    try:
        return json.loads(response.content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f'Evaluation model returned invalid JSON: {response.content!r}'
        ) from e
    
# Hook to show function calls and member delegations
def tool_hook(function_name, function_call, arguments):
    if function_name == 'delegate_task_to_member':
        member_id = arguments.get('member_id')
        print(f'\x1b[33mDelegating to {member_id}\x1b[0m')
    else:
        print(f'\x1b[32mCalling {function_name}\x1b[0m')

    return function_call(**arguments)

# Function to create an agent for evaluating job applicants
def create_agent(session_id, memory):
    agent = Agent(
        name='Hiring Agent',
        tools=[
            list_job_applicants,
            list_job_titles,
            get_resume,
            get_job_description,
            evaluate_applicant
        ],
        tool_hooks=[tool_hook],
        instructions='''
            Your name is SOPHIA, and you are a hiring expert. You have the
            ability to retrieve resumes and job descriptions and answer questions
            from them. You also have the ability to evaluate applicants for jobs. Use
            all the tools at your disposal to help the user with their hiring needs.
            Never use a tool unless absolutely necessary.
        
            Only evaluate applicants for whom resumes are available from the
            Resume Agent. Only evaluate applicants for jobs that are currently
            available from the Job Description Agent.

            If asked about a person whose name doesn't appear in the list returned
            by the list_job_applicants tool, find the closest match and ask the user
            if that's who they meant. Similarly, if asked about a job that isn't in
            the list returned by the list_job_titles tool, find the closest match
            and ask for clarification if necessary.

            If asked who's the best fit for a job, pass applicable names and the
            job title to evaluate_applicant one by one. Then include a table in
            your response with columns for the applicant name, the score (0.0 to
            10.0), and a brief explanation of the score. Use the table to show each
            applicant's fit for the job. Also provide a textual summary explaining
            why the highest-scoring applicant is the best fit. Sort the table by
            scores in descending order.            

            Make your output succint. Conversational responses are preferred to
            ones containing bulleted and numbered lists.
            ''',
        model=OpenAIChat(id=MODEL),
        add_history_to_context=True,
        num_history_runs=10,
        session_id=session_id,
        db=memory,
        markdown=True
    )

    return agent
