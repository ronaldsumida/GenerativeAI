import sqlite3, json, os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.calculator import CalculatorTools
from agno.tools.file_generation import FileGenerationTools
from agno.models.message import Message
from agno.tools import tool

MODEL='gpt-5.4-mini'

INSTRUCTIONS='''
    You are a helpful assistant named LISA who can answer questions from the
    Northwind database. Northwind contains information about sales, products,
    orders, and employees of a company named Northwind Traders. The database
    contains the following tables:

    Categories - Information about product categories
    Customers - Information about customers who purchase Northwind products
    Employees - Information about employees of Northwind Traders
    Shippers - Information about companies that ship Northwind products
    Suppliers - Information about suppliers of Northwind products
    Products - Information about the products that Northwind sells
    Orders - Information about orders placed by Northwind customers
    OrderDetails - Information about order details such as products and quantities

    Assume that monetary amounts are in dollars. Round such amounts to the nearest
    dollar in your output, and use commas as separators for amounts greater than $999.
    Show dollar amounts only. Do not include cents.

    You can also generate CSV, TXT, PDF, and JSON files. When generating a
    report in a PDF or a text file, include explanatory text when possible
    documenting the contents of the file.

    When you generate a file, include an HTML link in your output that can
    be used to download the file. Also let the user know that the download
    link is available. Don't use a sandbox URL. Link to the file that the
    file-generation tool created in the Web site's "static" directory.
    Use fully-qualified URLs -- for example,
    "http://localhost:5000/static/reports/report.pdf".

    If asked to generate a report, generate a PDF file unless directed to do
    otherwise. Do not use markdown in the files you generate unless specifically
    asked to.

    Return markdown in all your responses to the user. Use markdown tables
    when appropriate.
    '''

# Generate a path to the site's "static/reports" directory
root_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(root_dir, 'static', 'reports')
os.makedirs(output_path, exist_ok=True)

# Tool function for querying the database
def query_database(text: str) -> str:
    '''
    Queries the Northwind database to answer a question or respond
    to a command. Northwind contains information about sales, products,
    orders, and employees of a company named Northwind Traders.

    Args:
        text: Natural-language query describing the data to be retrieved.

    Returns:
        JSON string containing query results.
    '''

    # Convert a natural-language query into a SQL query
    sql = text2sql(text)
    print(f'\x1b[32m{sql}\x1b[0m')

    # Execute the SQL query
    with sqlite3.connect('static/northwind.db') as connection:
        rows = connection.execute(sql).fetchall()

    # Return the JSON-encoded results
    return json.dumps(rows)

# Demonstration tool for human-in-the-loop confirmation
@tool(requires_confirmation=True)
def delete_database() -> str:
    '''
    Deletes the Northwind database.

    Returns:
        Status message indicating that the database was deleted.
    '''

    # This code does not run until the user approves the tool call.
    # For the demo, it deliberately does NOT delete the database.
    print('\x1b[35mDELETE DATABASE approved (simulation only)\x1b[0m')
    return 'The Northwind database was deleted.'

# Helper function to convert natural-language queries into SQL queries
def text2sql(text):
    prompt = f'''
        Generate a well-formed SQLite query from the prompt below. Return
        the SQL only. Do not use markdown formatting, and do not use SELECT *.

        PROMPT: {text}
    
        The database targeted by the query contains the following tables:

        CREATE TABLE [Categories]
        (
            [CategoryID] INTEGER PRIMARY KEY AUTOINCREMENT,
            [CategoryName] TEXT,
            [Description] TEXT
        )

        CREATE TABLE [Customers]
        (
            [CustomerID] TEXT,
            [CompanyName] TEXT,
            [ContactName] TEXT,
            [ContactTitle] TEXT,
            [Address] TEXT,
            [City] TEXT,
            [Region] TEXT,
            [PostalCode] TEXT,
            [Country] TEXT,
            [Phone] TEXT,
            [Fax] TEXT,
            PRIMARY KEY (`CustomerID`)
        )

        CREATE TABLE [Employees]
        (
            [EmployeeID] INTEGER PRIMARY KEY AUTOINCREMENT,
            [LastName] TEXT,
            [FirstName] TEXT,
            [Title] TEXT,
            [TitleOfCourtesy] TEXT,
            [BirthDate] DATE,
            [HireDate] DATE,
            [Address] TEXT,
            [City] TEXT,
            [Region] TEXT,
            [PostalCode] TEXT,
            [Country] TEXT,
            [HomePhone] TEXT,
            [Extension] TEXT,
            [Notes] TEXT,
            [ReportsTo] INTEGER,
            FOREIGN KEY ([ReportsTo]) REFERENCES [Employees] ([EmployeeID]) 
        )

        CREATE TABLE [Shippers]
        (
            [ShipperID] INTEGER NOT NULL PRIMARY KEY,
            [CompanyName] TEXT NOT NULL,
            [Phone] TEXT
        )

        CREATE TABLE [Suppliers]
        (
            [SupplierID] INTEGER NOT NULL PRIMARY KEY,
            [CompanyName] TEXT NOT NULL,
            [ContactName] TEXT,
            [ContactTitle] TEXT,
            [Address] TEXT,
            [City] TEXT,
            [Region] TEXT,
            [PostalCode] TEXT,
            [Country] TEXT,
            [Phone] TEXT,
            [Fax] TEXT,
            [HomePage] TEXT
        )

        CREATE TABLE [Products]
        (
            [ProductID] INTEGER NOT NULL PRIMARY KEY,
            [ProductName] TEXT NOT NULL,
            [SupplierID] INTEGER,
            [CategoryID] INTEGER,
            [QuantityPerUnit] TEXT,
            [UnitPrice] NUMERIC DEFAULT 0,
            [UnitsInStock] INTEGER DEFAULT 0,
            [UnitsOnOrder] INTEGER DEFAULT 0,
            [ReorderLevel] INTEGER DEFAULT 0,
            [Discontinued] TEXT NOT NULL DEFAULT '0',
            FOREIGN KEY ([CategoryID]) REFERENCES [Categories] ([CategoryID]),
            FOREIGN KEY ([SupplierID]) REFERENCES [Suppliers] ([SupplierID])
        )

        CREATE TABLE [Orders]
        (
            [OrderID] INTEGER PRIMARY KEY,
            [CustomerID] INTEGER,
            [EmployeeID] INTEGER,
            [OrderDate] DATETIME,
            [ShipperID] INTEGER,
            FOREIGN KEY (EmployeeID) REFERENCES Employees (EmployeeID),
            FOREIGN KEY (CustomerID) REFERENCES Customers (CustomerID),
            FOREIGN KEY (ShipperID) REFERENCES Shippers (ShipperID)
        );

        CREATE TABLE [Order Details]
        (
            [OrderID] INTEGER NOT NULL,
            [ProductID] INTEGER NOT NULL,
            [UnitPrice] NUMERIC NOT NULL DEFAULT 0,
            [Quantity] INTEGER NOT NULL DEFAULT 1,
            [Discount] REAL NOT NULL DEFAULT 0,
            PRIMARY KEY ("OrderID", "ProductID"),
            FOREIGN KEY ([OrderID]) REFERENCES [Orders] ([OrderID]),
            FOREIGN KEY ([ProductID]) REFERENCES [Products] ([ProductID]) 
        )
        '''

    model=OpenAIChat(id=MODEL, temperature=0.2)
    messages = [Message(role='user', content=prompt)]
    response = model.response(messages)
    return response.content

# Function to hook into tool calls
def function_hook(function_name, function_call, arguments):
    print(f'\x1b[33mCalling {function_name}\x1b[0m')
    return function_call(**arguments)

# Function to create an agent
def create_agent(session_id, memory):
    # Create an agent and connect it to a session
    agent = Agent(
        name='Northwind Agent',
        model=OpenAIChat(id=MODEL),
        tools=[
            query_database,
            delete_database,
            CalculatorTools(),
            FileGenerationTools(output_directory=output_path)
        ],
        tool_hooks=[function_hook], # Shows tool calls performed by the agent
        instructions=INSTRUCTIONS,
        add_history_to_context=True,
        num_history_runs=10,
        session_id=session_id,
        db=memory,
        markdown=True
    )

    return agent
