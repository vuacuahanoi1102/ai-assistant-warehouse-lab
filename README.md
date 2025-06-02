AI Assistant for Workflow & Warehouse AutomationAI Assistant using FastAPI and LLMs to manage sample workflow and plastic storage
This project is an AI assistant system designed to support real-world lab and warehouse workflows. It integrates LLMs with backend logic to manage tasks, and track plastic material inventory across pallets and layers.
.

🔧 Tech Stack
Python, FastAPI

SQLModel

Local LLMs via Ollama

💡 Features
Parse user input (e.g. “Add sample p640j lot 58”) and automatically generate related tasks.

Mark specific tasks as done,add task,delete task,delete sample via natural language.

Manage plastic bag positions (pallet → layer → bag).

Track movement of bags if lower layers need to be accessed.

📁 Project Structure

app/

├── main.py  

├── database.py

├── models.py

├── index.html

├── task_template.py

├── services/

│  ├── sample_services.py  

│  ├── chat_services.py   

│  ├── plastic_service.py   

|  └── llm_service.py     

Find the PowerPoint file for more details about its purpose and how it works.
