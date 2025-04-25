import time
import yaml
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from julep import Julep

# Load environment variables from .env file
load_dotenv()

# Get Julep API key securely
api_key = os.getenv("eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTA1OTEyNTUsImlhdCI6MTc0NTQwNzI1NSwic3ViIjoiYmQwNDEyZDEtYmI1Yy01NDg4LWE3ZjItMzFjMDUzNDUyYjQ4In0.mg3NMbTqq9JYW0_1Rhnko9C5Wxbf2aSkKEltRHs18e6FGFA7gS5NF-E8tEvrq8LlIr_AjRXRdMkYQuuHAqF1lg")
if not api_key:
    raise ValueError("Missing JULEP_API_KEY in environment variables")

# Initialize Flask app
app = Flask(__name__)

# Step 1: Connect to Julep using the API key
client = Julep(api_key=api_key)

# Step 2: Create the agent once at startup
agent = client.agents.create(
    name="Research Assistant",
    model="claude-3.5-sonnet",
    about="A helpful research assistant that finds concise, structured information on topics."
)

# Step 3: Define the task (YAML format)
task_definition = yaml.safe_load("""
name: Research Task
description: Research a topic and present it in a specified format
main:
- prompt:
  - role: system
    content: |
      You are a helpful research assistant. Your goal is to find concise information on topics provided by the user.
      When given a topic and an output format (e.g., 'summary', 'bullet points', 'short report'), you must gather relevant information and structure it accordingly.
      Maintain a neutral, objective tone. Strictly follow the output format:
      - Summary: 3-4 sentences
      - Bullet Points: max 5 concise points
      - Short Report: under 150 words
      If reliable info cannot be found, state that clearly.
  - role: user
    content: |
      Topic: ${steps[0].input.topic}
      Format: ${steps[0].input.format}
""")

# Step 4: Create the task once
task = client.tasks.create(agent_id=agent.id, **task_definition)

@app.route('/')
def home():
    return "Welcome! Use POST /research with JSON body containing 'topic' and 'format'."

@app.route('/research', methods=['POST'])
def research():
    try:
        data = request.get_json()

        # Validate input
        topic = data.get("topic")
        format_ = data.get("format")
        if not topic or not format_:
            return jsonify({"error": "Missing 'topic' or 'format' in request body"}), 400

        # Trigger task execution
        execution = client.executions.create(
            task_id=task.id,
            input={"topic": topic, "format": format_}
        )

        # Wait for completion
        while (result := client.executions.get(execution.id)).status not in ['succeeded', 'failed']:
            time.sleep(1)

        # Return the result
        if result.status == "succeeded":
            return jsonify({"result": result.output})
        else:
            return jsonify({"error": "Julep execution failed", "details": result.error}), 500

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
