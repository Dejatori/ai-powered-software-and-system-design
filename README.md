# 📘 AI-Powered Software and System Design

Welcome to the **"AI-Powered Software and System Design"** repository! 🌟 This repository contains
my notes, exercises, and code examples from the course, designed to help developers understand 
and apply generative AI concepts in software development to enhance their skills and productivity. 💻

---

## 📑 Table of Contents

- [📘 Introduction to AI-Powered Software and System Design](#-ai-powered-software-and-system-design)
    - [📑 Table of Contents](#-table-of-contents)
    - [📥 Installation](#-installation)
    - [📖 Usage](#-usage)
    - [🤝 Contributing](#-contributing)
    - [📜 License](#-license)
    - [📞 Support/Contact](#-supportcontact)
    - [🙏 Acknowledgments](#-acknowledgments)

---

## 📥 Installation

To get started with this repository, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Dejatori/ai-powered-software-and-system-design
   cd ai-powered-software-and-system-design
   ```

2. **Set up a Python environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   # or use conda
   conda create -n generative-ai python=3.13.2
   conda activate generative-ai
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # or use conda
   conda install -c conda-forge -c anaconda --file requirements.txt
   ```

4. **Launch the Jupyter Notebook**:
   ```bash
   jupyter notebook
   ```

You're all set! 🎉

---

## 📖 Usage

Dejatori: Help me to create the content for the Usage section of my README.md

Workspace: Collecting workspace informationHere’s an example of how you can structure the **Usage** section for your README.md file based on the workspace structure you provided:

```markdown
## Usage

### Module 1: Image Generation
To generate images using the script in `module_1`:
1. Navigate to the `module_1` directory:
   ```sh
   cd module_1
   ```
2. Run the `gen_image.py` script:
   ```sh
   python gen_image.py
   ```
3. Generated images will be saved in the `images/` directory.

### Module 2: Database Operations

#### Running the Simple Database Script
1. Navigate to the `module_2` directory:
   ```sh
   cd module_2
   ```
2. Execute the `simple_database.py` script:
   ```sh
   python simple_database.py
   ```

#### Working with the E-commerce Schema
- Open the `ecommerce_schema.ipynb` notebook in Jupyter Notebook to explore the e-commerce database schema.
- Alternatively, run the `ecommerce_schema.py` script:
   ```sh
   python ecommerce_schema.py
   ```

#### CRUD Operations
- Use the `database_schema_crud.py` script to perform Create, Read, Update, and Delete operations on the database:
   ```sh
   python database_schema_crud.py
   ```

Here’s an updated **Usage** section for **Module 3** that reflects its focus on design patterns:

```markdown
### Module 3: Design Patterns for Software Development

This module demonstrates the implementation of various design patterns, including Singleton, Strategy, Factory, and Facade, applied to a financial analysis system.

#### Steps to Use Module 3

1. **Initialize the Database**:
   - Run the script to set up the database with synthetic data:
     ```sh
     python module_3/CompanyDataByDejatori.ipynb
     ```
   - This will create tables (`companies`, `TimeSeries`) and populate them with sample data.

2. **Demonstrate Design Patterns**:
   - Execute the script to see examples of the following design patterns in action:
     - **Singleton**: Ensures a single database connection instance.
     - **Strategy**: Allows switching between different financial analysis algorithms (e.g., Bollinger Bands, Simple Moving Average).
     - **Factory**: Dynamically creates company objects based on type (Domestic, Foreign, Cryptocurrency).
     - **Facade**: Simplifies complex operations like bulk analysis or retrieving companies by grade.

3. **Example Usage**:
   - The script includes examples of:
     - Creating companies using the Factory pattern.
     - Analyzing financial data using the Strategy pattern.
     - Assigning grades to companies based on analysis results.
     - Displaying results for Domestic, Foreign, and Cryptocurrency companies.

4. **Custom Analysis**:
   - Modify the script to perform custom analysis:
     - Change the strategy type (`bollinger` or `sma`).
     - Adjust parameters like `window_size` or `width` for Bollinger Bands.

This module is a practical demonstration of how design patterns can be applied to real-world software development scenarios.

---

## 🤝 Contributing

We welcome contributions to this repository! 🛠️ Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add an amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT). 📝  
![MIT License Badge](https://img.shields.io/badge/License-MIT-blue.svg)

---

## 🙏 Acknowledgments

A big thank you to:

- DeepLearning.AI, for this course of **"AI-Powered Software and System Design"**. 🎓
- The Instructor [Laurence Moroney](https://www.linkedin.com/in/laurence-moroney/) for their excellent teaching
and insights. 👨‍🏫
- Open-source libraries and tools like Python, Jupyter, and NLTK that made this project possible. 🛠️
- The amazing developer community for their support and inspiration. 🌟

---

Happy learning and coding! 🎉