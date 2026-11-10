# Nova AI – Personal AI Assistant

Nova AI is a personal AI assistant built using Python, Streamlit, and Ollama. It provides conversational assistance, study support, coding help, PDF question answering, and voice interaction.

## Features

- General Chat
- Study Assistant
- Coding Assistant
- PDF Upload and Question Answering
- Voice Input (Speech-to-Text)
- Voice Output (Text-to-Speech)
- Chat History Management
- SQLite Database Integration

## Technologies Used

- Python
- Streamlit
- Ollama
- Qwen 2.5 (3B)
- SQLite
- PyPDF
- Streamlit Mic Recorder

## Requirements

- Python 3.10 or later
- Ollama
- Qwen 2.5:3B model

## Installation

1. Clone this repository.
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Install Ollama and download the model:

```bash
ollama pull qwen2.5:3b
```

4. Run Nova AI:

```bash
streamlit run app.py
```

## Developer

Built as a personal learning project to explore Python, local AI models, and application development.