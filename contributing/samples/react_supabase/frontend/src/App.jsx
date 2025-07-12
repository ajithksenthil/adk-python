import { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000';
const SESSION = { app_name: 'coordinator', user_id: 'demo', session_id: '1' };

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  useEffect(() => {
    const es = new EventSource(`${API_URL}/run_sse`);
    es.onmessage = (e) => setMessages((m) => [...m, e.data]);
    return () => es.close();
  }, []);

  const send = async () => {
    await fetch(`${API_URL}/run_sse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...SESSION, new_message: input }),
    });
  };

  return (
    <div>
      <ul>
        {messages.map((m, i) => (
          <li key={i}>{m}</li>
        ))}
      </ul>
      <input value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={send}>Send</button>
    </div>
  );
}
