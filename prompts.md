# Prompts

## Module 1

### Prompt 1

```plaintext
You are an expert on software design paradigms. I am working on building a simple Python-based app that will make
calls to the DALL-E API and generate images for users.
The application will be deployed in many different contexts and configurations depending on the end users,
and I want my less technical colleagues to be able to do some customization without editing the code itself.
What high level software design paradigms should I consider for this project?
```

### Prompt 2

```plaintext
You are an expert Python develop who intimately understands the
language and its ecosystem. You are also an excellent explainer that
helps people understand whatever you tell them, whether they are a
novice or expert. Please answer this question: Explain what Pickle is,
and why it is useful in Python. Be very succinct.
```

### Prompt 3

```plaintext
You are a deep expert on the OpenAI ecosystem, including the client libraries, REST endpoints, and any other
way of accessing functionality of GPT, DALL-E, and other models.
Please create easy to read, easy to follow code that will call DALL-E to generate an image.
The code should be in Python, and all parameters should be in an external file that the Python code reads.
Please use the most up-to-date design pattern.
```

### Prompt 4

```plaintext
Can you create code that accesses the OpenAl endpoint at:
https://platform.openai.com/docs/api-reference/images/create
directly to create an image?
```

## Module 2

### Prompt 1

```plaintext
You are an expert data architect with deep experience in designing and implementing database schemas.
Design a database schema for an e-commerce application with tables for users, products, orders, and order items.
The schema should include the necessary fields and relationships between the tables. Provide a brief explanation
of each table and its purpose.
```

### Prompt 2

```plaintext
What are the things to consider when you implement the create operation for a database?
```

### Prompt 3

```plaintext
How can I implement proper session management to create users, products, orders, and order items while maintaining
the relationships between them?
You need to consider the following:
- Data Validation and Constraints.
- Use transactions to ensure atomicity.
- Security Concerns.
- Performance Considerations.
- Integrity and Relationships.
- Error Handling.
- Auditability.
```

### Prompt 4

```plaintext
What are some best practices to improve the performance of this database?
```

## Module 3

### Prompt 1

```plaintext
Give me a high-level overview of the Gang of Four design patterns.
```

### Prompt 2

```plaintext
You are an expert Python developer who builds readable code.
Together we will work on an application that has a database to store
information, code to retrieve data from the database, and analytics
that will run on the retrieved data.
First, let's create the database, which has a table for companies. The
table will have three columns, the first is an id, the second the ticker
for the company, the third is the name of the company. Create this,
and synthesize data for 10 companies, adding that to the database.
```

### Prompt 3

```plaintext
Now add another table called 'TimeSeries' that has four columns, an
id for the row, the id for one of the companies, a value, and a date.
Populate this with about 100 values per company, and have the dates
be successive.
```

### Prompt 4

```plaintext
Now create code that when given a company ticker or an ID that it
will extract the data for that company, and the time series data and
load it into an company object. This object should have fields for
high_bollinger which is the same data type as the time series,
low_bollinger which is the same, moving _ average which is the same,
and a grade field which is a string.
```

### Prompt 5

```plaintext
You are an expert in software design patterns, particularly those from
the Gang of Four, designed to make coding and maintenance more
efficient. Please analyze the following code and suggest some
changes that I could make based on good software engineering
practice with these design patterns.
```

### Prompt 6

```plaintext
Instead of making all the changes at once, please do them one at a
time, going in order from Singleton to Factory to template Method to
Strategy, and explain in detail why you made the changes and what
impact they may have.
```

### Prompt 7

```plaintext
Enhance the following code to use the gang-of-four patterns. Strictly
follow the common conventions for any patterns you choose.
Start by explaining the conventions for the Singleton pattern and then
describe how the code modifications you made strictly follow the
conventions.
```

### Prompt 8

```plaintext
Go back to the code that adds data to the database and
synthesize some foreign companies (which will have a unique ID,
but the ticker is always 'ZZZZ' ) and the data for them, both in the
companies table and in the time series table.
Then fully explain the Factory pattern by having multiple
company types -- a Domestic Company that is denoted by its
ticker, and a Foreign Company that is denoted by its ID.
Create code that shows how to use the Factory pattern to create these
two types of companies.
```