
// import {
//   Show,
//   SignInButton,
//   SignUpButton,
//   UserButton,
// } from '@clerk/react'
// import './App.css'

// function App() {
//   return (
//     <main className="app">
//       <header className="navbar">
//         <h2>YouTube RAG Bot</h2>

//         <div className="auth-actions">
//           <Show when="signed-out">
//             <SignInButton />
//             <SignUpButton />
//           </Show>

//           <Show when="signed-in">
//             <UserButton />
//           </Show>
//         </div>
//       </header>

//       <section className="hero">
//         <p className="eyebrow">YOUR PERSONAL VIDEO KNOWLEDGE BASE</p>
//         <h1>Chat with your YouTube videos.</h1>
//         <p>
//           Add a YouTube URL, ask questions about its content,
//           and return to your saved conversations whenever you need.
//         </p>

//         <Show when="signed-out">
//           <SignUpButton>
//             <button className="primary-button">
//               Get started
//             </button>
//           </SignUpButton>
//         </Show>

//         <Show when="signed-in">
//           <p className="success-message">
//             You're signed in! Your video workspace will be available here.
//           </p>
//         </Show>
//       </section>
//     </main>
//   )
// }

// export default App


import { useState } from "react";
import {
  SignedIn,
  SignedOut,
  SignInButton,
  UserButton,
  useAuth,
} from "@clerk/clerk-react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function ChatPersistenceTest() {
  const { getToken } = useAuth();
  const [chatId, setChatId] = useState("");
  const [chats, setChats] = useState([]);
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState("");
  const [copiedToken, setCopiedToken] = useState(false);

  async function copyTokenForSwagger() {
    try {
      const token = await getToken();
      if (!token) throw new Error("No Clerk session token. Sign in again.");
      await navigator.clipboard.writeText(token);
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 4000);
      setStatus("Clerk session token copied to clipboard! (Valid for 60s)");
    } catch (err) {
      setStatus(`Error copying token: ${err.message}`);
    }
  }

  async function request(path, options = {}) {
    const token = await getToken();

    if (!token) {
      throw new Error("No Clerk session token. Sign in again.");
    }

    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || JSON.stringify(data));
    }

    return data;
  }

  async function run(action) {
    try {
      setStatus("Working...");
      await action();
      setStatus("Success");
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    }
  }

  async function createChat() {
    const chat = await request("/api/v1/chats", {
      method: "POST",
      body: JSON.stringify({ title: "Persistence test" }),
    });

    setChatId(chat.id);
    await loadChats();
  }

  async function loadChats() {
    const data = await request("/api/v1/chats");
    setChats(data);
  }

  async function saveTestMessage() {
    if (!chatId) throw new Error("Create or select a chat first.");

    await request(`/api/v1/chats/${chatId}/messages`, {
      method: "POST",
      body: JSON.stringify({
        role: "user",
        content: "Persistence test message",
      }),
    });

    await reopenChat();
  }

  async function reopenChat() {
    if (!chatId) throw new Error("Select a chat first.");

    const chat = await request(`/api/v1/chats/${chatId}`);
    setMessages(chat.messages || []);
  }

  return (
    <main style={{ maxWidth: 760, margin: "40px auto", padding: 20 }}>
      <h1>Chat Persistence Test</h1>
      <UserButton />

      <p>
        <button onClick={() => run(createChat)}>1. Create chat</button>{" "}
        <button onClick={() => run(loadChats)}>2. List chats</button>{" "}
        <button onClick={copyTokenForSwagger} style={{ background: "#0f172a", color: "#38bdf8", border: "1px solid #38bdf8", padding: "6px 12px", borderRadius: 4, cursor: "pointer" }}>
          {copiedToken ? "✓ Copied! (Valid 60s)" : "📋 Copy Token for Swagger"}
        </button>
      </p>

      <label>
        Chat ID
        <input
          value={chatId}
          onChange={(event) => setChatId(event.target.value)}
          style={{ display: "block", width: "100%", margin: "8px 0" }}
          placeholder="Create a chat or paste its ID"
        />
      </label>

      <p>
        <button onClick={() => run(saveTestMessage)}>
          3. Save test message
        </button>{" "}
        <button onClick={() => run(reopenChat)}>
          4. Reopen chat
        </button>
      </p>

      <h2>Saved chats</h2>
      {chats.map((chat) => (
        <p key={chat.id}>
          <button
            onClick={() => {
              setChatId(chat.id);
              setMessages([]);
            }}
          >
            Select
          </button>{" "}
          {chat.title} — {chat.id}
        </p>
      ))}

      <h2>Messages</h2>
      {messages.map((message) => (
        <p key={message.id}>
          <strong>{message.role}:</strong> {message.content}
        </p>
      ))}

      <p>{status}</p>
    </main>
  );
}

export default function App() {
  return (
    <>
      <SignedOut>
        <p>Please sign in to test chat persistence.</p>
        <SignInButton />
      </SignedOut>
      <SignedIn>
        <ChatPersistenceTest />
      </SignedIn>
    </>
  );
}

