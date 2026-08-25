import sqlite3, json
from openai import OpenAI

MODEL='gpt-5.4-mini'

# Tool for querying the Northwind database
def query_database(user_input):
    # Turn the natural-language query into a SQL query
    print(f'\033[93mCalling text2sql("{user_input}")\033[0m')
    sql = text2sql(user_input)
    print(f'\033[92m{sql}\033[0m')
    
    # Execute the SQL query and return the result
    print('\033[93mCalling execute_sql()\033[0m')
    result = execute_sql(sql)
    return json.dumps(result)

# Tool description
database_tool = {
    'type': 'function',
    'function': {
        'name': 'query_database',
        'description': '''
            Queries the Northwind database to answer a question or respond
            to a command. Northwind contains information about sales, products,
            orders, and employees of a company named Northwind Traders.
            ''',
        'parameters': {
            'type': 'object',
            'properties': {
                'user_input': {
                    'type': 'string',
                    'description': 'Natural-language description of the data to retrieve'
                },
            },
            'required': ['user_input']
        }
    }
}

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
            [ShipperID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            [CompanyName] TEXT NOT NULL,
            [Phone] TEXT
        )

        CREATE TABLE [Suppliers]
        (
            [SupplierID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
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
            [ProductID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
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
            [OrderID] INTEGER PRIMARY KEY AUTOINCREMENT,
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

    messages = [
        {
            'role': 'system',
            'content': 'You are a database expert who converts questions into SQL queries.'
        },
        {
            'role': 'user',
            'content': prompt
        }
    ]

    client = OpenAI()
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2
    )

    sql = response.choices[0].message.content
    return sql

# Helper function to execute SQL queries
def execute_sql(sql):
    connection = sqlite3.connect('static/northwind.db')
    cursor = connection.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    return rows

tools = [
    database_tool
]
