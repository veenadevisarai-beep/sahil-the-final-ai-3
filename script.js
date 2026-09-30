const questionBox = document.getElementById("question");
const chatArea = document.getElementById("chatArea");

let selectedSubject = "";


function selectSubject(subject) {
    selectedSubject = subject;

    questionBox.focus();

    questionBox.placeholder =
        "Ask a " + subject + " question...";
}


function newChat() {
    chatArea.innerHTML = `
        <div class="welcome">

            <div class="robot">🤖</div>

            <h2>Welcome to SST AI!</h2>

            <p>
                Ask me anything about your Class 9 Social Science subjects.
            </p>

            <div class="subject-cards">

                <button onclick="selectSubject('History')">
                    🏺
                    <strong>History</strong>
                    <small>Events & civilizations</small>
                </button>

                <button onclick="selectSubject('Geography')">
                    🌍
                    <strong>Geography</strong>
                    <small>Earth & environment</small>
                </button>

                <button onclick="selectSubject('Political Science')">
                    🏛️
                    <strong>Political Science</strong>
                    <small>Democracy & government</small>
                </button>

                <button onclick="selectSubject('Economics')">
                    💰
                    <strong>Economics</strong>
                    <small>People & economy</small>
                </button>

            </div>

        </div>
    `;

    selectedSubject = "";
    questionBox.placeholder = "Ask your SST question...";
}


function addMessage(text, type) {

    const message = document.createElement("div");

    message.className = "message " + type;

    message.textContent = text;

    chatArea.appendChild(message);

    chatArea.scrollTop = chatArea.scrollHeight;
}


async function askQuestion() {

    const question = questionBox.value.trim();

    if (!question) {
        return;
    }

    addMessage(question, "user-message");

    questionBox.value = "";

    addMessage("🤖 Thinking...", "ai-message");

    try {

        const response = await fetch("/ask", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: question
            })

        });

        const data = await response.json();

        const messages =
            document.querySelectorAll(".ai-message");

        const lastMessage =
            messages[messages.length - 1];

        lastMessage.textContent =
            "🤖 " + data.answer;

    } catch (error) {

        const messages =
            document.querySelectorAll(".ai-message");

        const lastMessage =
            messages[messages.length - 1];

        lastMessage.textContent =
            "🤖 Sorry, I couldn't connect to the SST AI server.";

    }
}


function handleEnter(event) {

    if (event.key === "Enter" && !event.shiftKey) {

        event.preventDefault();

        askQuestion();

    }
}