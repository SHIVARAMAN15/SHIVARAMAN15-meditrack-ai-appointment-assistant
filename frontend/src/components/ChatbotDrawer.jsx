import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, Trash2, ChevronDown } from 'lucide-react';
import { sendChatMessage } from '../api/client';

const SUGGESTIONS = [
  "Show tomorrow's appointments",
  "Which appointments have a high no-show risk?",
  "Show reminder recommendations",
  "Summarize appointment statistics",
  "What is the attendance probability for APT-1001?",
];

const INITIAL_MESSAGES = [
  {
    id: 1,
    sender: 'assistant',
    text: "Hello! I am your MediTrack Clinic Assistant. I can help you look up appointments, check no-show risks, check reminder recommendations, or reschedule visits. What would you like to check?",
    intent: 'GREETING',
    timestamp: '10:00 AM',
  },
];

let messageIdCounter = 100;
const getNextId = () => ++messageIdCounter;
const getFormattedTime = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export default function ChatbotDrawer({ onActionTriggered }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSendMessage = async (textToSend = input) => {
    const trimmed = textToSend.trim();
    if (!trimmed || loading) return;

    const userMsg = {
      id: getNextId(),
      sender: 'user',
      text: trimmed,
      timestamp: getFormattedTime(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const data = await sendChatMessage(trimmed);

      const botMsg = {
        id: getNextId(),
        sender: 'assistant',
        text: data.message || 'I processed your query.',
        intent: data.intent || 'PROCESSED',
        timestamp: getFormattedTime(),
        data: data.data,
      };

      setMessages((prev) => [...prev, botMsg]);

      // If the intent modified state (e.g. reschedule, cancel), notify parent to refresh
      if (['RESCHEDULE', 'CANCEL', 'SEND_REMINDER'].includes(data.intent) && onActionTriggered) {
        onActionTriggered(data.intent);
      }
    } catch (err) {
      const errorMsg = {
        id: getNextId(),
        sender: 'assistant',
        text: `Sorry, I encountered an issue: ${err.message}`,
        intent: 'ERROR',
        timestamp: getFormattedTime(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: getNextId(),
        sender: 'assistant',
        text: "Conversation cleared. How can I assist your clinic workflow?",
        intent: 'READY',
        timestamp: getFormattedTime(),
      },
    ]);
  };

  // Render markdown-like bold text and newlines cleanly
  const renderMessageText = (text) => {
    if (!text) return null;
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      // Basic replace **word** with strong
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return (
        <React.Fragment key={idx}>
          {parts.map((part, pIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
            }
            return part;
          })}
          {idx < lines.length - 1 && <br />}
        </React.Fragment>
      );
    });
  };

  return (
    <>
      {/* Floating Launcher Button */}
      <button
        type="button"
        className="chat-floating-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Open MediTrack Clinic Assistant"
      >
        <Bot size={22} />
        <span>Staff Assistant</span>
      </button>

      {/* Slide-in / Pop-up Drawer */}
      {isOpen && (
        <div className="chat-drawer" role="dialog" aria-label="Staff Assistant Chat">
          {/* Header */}
          <div className="chat-header">
            <div className="chat-header-title">
              <Bot size={20} />
              <div>
                <span>MediTrack Staff Assistant</span>
                <div style={{ fontSize: '0.68rem', color: '#94a3b8', fontWeight: 400 }}>
                  Deterministic Intent Engine &bull; Zero External API Latency
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                type="button"
                className="modal-close-btn"
                style={{ color: '#cbd5e1' }}
                onClick={clearChat}
                title="Clear conversation"
              >
                <Trash2 size={16} />
              </button>
              <button
                type="button"
                className="modal-close-btn"
                style={{ color: '#cbd5e1' }}
                onClick={() => setIsOpen(false)}
                title="Minimize chat"
              >
                <ChevronDown size={18} />
              </button>
            </div>
          </div>

          {/* Messages Stream */}
          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`chat-bubble ${msg.sender}`}>
                {msg.intent && msg.sender === 'assistant' && (
                  <span className="chat-intent-tag">[{msg.intent}]</span>
                )}
                <div>{renderMessageText(msg.text)}</div>
                <span
                  style={{
                    fontSize: '0.65rem',
                    opacity: 0.7,
                    alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                    marginTop: '2px',
                  }}
                >
                  {msg.timestamp}
                </span>
              </div>
            ))}
            {loading && (
              <div className="chat-bubble assistant">
                <span className="chat-intent-tag">[PROCESSING]</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                  <span style={{ fontSize: '0.8rem', color: 'var(--neutral-500)' }}>
                    Checking clinic database &amp; ML models...
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestions Chips */}
          <div className="chat-suggestions">
            {SUGGESTIONS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                className="suggestion-chip"
                onClick={() => handleSendMessage(item)}
              >
                {item}
              </button>
            ))}
          </div>

          {/* Input Bar */}
          <form
            className="chat-input-bar"
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
          >
            <input
              type="text"
              className="chat-input"
              placeholder="Ask about appointments, risks, or reschedule..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              className="btn btn-primary btn-sm btn-icon-only"
              disabled={loading || !input.trim()}
              title="Send query"
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
