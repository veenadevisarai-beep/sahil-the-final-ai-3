from flask import Flask, request, jsonify, send_from_directory
from knowledge import answer, resolve
import ollama
import re

app = Flask(__name__)

OLLAMA_MODEL = "llama3.2:3b"

conversation = []
last_topic = ""


SYSTEM_PROMPT = """
You are SST AI, a Class 9 Social Science tutor.

Subjects:
History, Geography, Political Science, Economics.

IMPORTANT:

- Answer only Class 9 Social Science questions.
- Use simple language suitable for Class 9.
- Stay focused on the student's requested topic.
- Never change the topic unless the student asks you to.

FOLLOW-UP QUESTIONS:

If the student says:
"explain it"
"explain this"
"explain that"
"tell me more"
"more details"
"make it simple"
"in simple words"
"give examples"

use the previous topic supplied by the application.

QUESTION GENERATION:

If the student asks:
"make 10 questions"
"give 10 questions"
"create 10 questions"
"10 questions about it"

generate exactly 10 questions about the current topic.

If the student asks for 5 questions, generate exactly 5.
If they ask for 20, generate exactly 20.

For example:

Previous topic: Plate Tectonics
Student: make 10 questions about it

You MUST generate 10 questions about Plate Tectonics.

Do NOT generate questions about random Social Science chapters.

MCQs:
If the student asks for MCQs, give MCQs with four options.

If the student asks for answers, give the answers.

If the question is unrelated to Social Science, say:

"I am SST AI, so I only answer Class 9 Social Science questions."

Do not pretend information is from NCERT unless you are confident.
"""


def ask_ollama(question, topic=""):
    global conversation

    context = ""

    if topic:
        context = (
            "\nCURRENT TOPIC:\n"
            + topic
            + "\n\n"
            "The student's current question should be understood "
            "in relation to this topic unless they clearly change it."
        )

    conversation.append({
        "role": "user",
        "content": question
    })

    if len(conversation) > 16:
        conversation = conversation[-16:]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + context
        }
    ]

    messages.extend(conversation)

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages
    )

    result = response["message"]["content"].strip()

    conversation.append({
        "role": "assistant",
        "content": result
    })

    if len(conversation) > 16:
        conversation[:] = conversation[-16:]

    return result


def extract_topic(question):
    """
    Try to find the main topic from the student's question.
    """

    patterns = [
        r"(?:about|on)\s+(.+)",
        r"(?:explain|describe|define)\s+(.+)",
        r"(?:what\s+is|what\s+are)\s+(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)

        if match:
            topic = match.group(1).strip()
            topic = topic.rstrip("?.!")

            if topic:
                return topic

    return ""


def is_followup(question):
    q = question.lower().strip()

    followups = [
        "explain it",
        "explain this",
        "explain that",
        "explain it simply",
        "explain it in simple words",
        "explain this in simple words",
        "tell me more",
        "more details",
        "give more details",
        "make it simple",
        "make it easier",
        "in simple words",
        "simplify it",
        "give examples",
        "example",
        "more",
    ]

    return q in followups


def is_question_generation(question):
    q = question.lower().strip()

    return bool(
        re.search(
            r"\b(?:make|give|create|generate)\s+"
            r"(?:me\s+)?\d+\s+questions?\b",
            q
        )
        or re.search(
            r"\b\d+\s+questions?\b",
            q
        )
    )


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/ask", methods=["POST"])
def ask():
    global last_topic

    data = request.get_json(silent=True) or {}

    question = str(
        data.get("question", "")
    ).strip()

    if not question:
        return jsonify({
            "answer": "Please enter a question."
        })

    try:

        # -----------------------------------
        # FOLLOW-UP QUESTION
        # -----------------------------------

        if is_followup(question) and last_topic:

            prompt = (
                "The previous topic was: "
                + last_topic
                + "\n\n"
                + question
            )

            result = ask_ollama(
                prompt,
                last_topic
            )

            return jsonify({
                "answer": result
            })


        # -----------------------------------
        # QUESTION GENERATION
        # -----------------------------------

        if is_question_generation(question) and last_topic:

            prompt = (
                "The previous topic was: "
                + last_topic
                + "\n\n"
                "The student wants practice questions about "
                "that topic.\n\n"
                + question
                + "\n\n"
                "Generate exactly the requested number of questions. "
                "Every question must be about "
                + last_topic
                + "."
            )

            result = ask_ollama(
                prompt,
                last_topic
            )

            return jsonify({
                "answer": result
            })


        # -----------------------------------
        # NORMAL SST KNOWLEDGE BASE
        # -----------------------------------

        result = resolve(question)

        if result["kind"] != "fallback":

            ai_answer = answer(question)

            # Try to remember the topic
            topic = extract_topic(question)

            if topic:
                last_topic = topic

            conversation.append({
                "role": "user",
                "content": question
            })

            conversation.append({
                "role": "assistant",
                "content": ai_answer
            })

            if len(conversation) > 16:
                del conversation[:-16]

            return jsonify({
                "answer": ai_answer
            })


        # -----------------------------------
        # OLLAMA
        # -----------------------------------

        topic = extract_topic(question)

        if topic:
            last_topic = topic

        result = ask_ollama(
            question,
            last_topic
        )

        return jsonify({
            "answer": result
        })


    except Exception as e:

        return jsonify({
            "answer": "AI connection error: " + str(e)
        })


@app.route("/new-chat", methods=["POST"])
def new_chat():
    global conversation
    global last_topic

    conversation = []
    last_topic = ""

    return jsonify({
        "status": "ok"
    })


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )