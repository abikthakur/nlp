/**
 * SportsBot — Frontend Logic
 * Handles chat, quiz mode, sidebar, markdown rendering, typing indicator.
 */

// ── Simple markdown renderer (no external deps) ───────────────────────────────
function renderMarkdown(text) {
  return text
    // Code blocks (must come before inline code)
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/_(.+?)_/g, '<em>$1</em>')
    // Tables (simple)
    .replace(/\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)*)/g, (_, header, rows) => {
      const ths = header.split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
      const trs = rows.trim().split('\n').map(row => {
        const tds = row.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('');
        return `<tr>${tds}</tr>`;
      }).join('');
      return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
    })
    // H3
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    // H2
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    // H1
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Unordered list items
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    // Wrap li runs in ul
    .replace(/(<li>[\s\S]+?<\/li>)(?=\s*(?!<li>))/g, '<ul>$1</ul>')
    // Ordered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Paragraphs (double newlines)
    .replace(/\n{2,}/g, '</p><p>')
    // Single line breaks
    .replace(/\n/g, '<br/>')
    // Wrap in paragraph
    .replace(/^(.+)$/, '<p>$1</p>');
}

// ── State ──────────────────────────────────────────────────────────────────────
const state = {
  history: [],          // [{role, content}]
  isLoading: false,
  quiz: {
    active: false,
    sessionId: null,
    score: 0,
    total: 5,
    current: 0,
  },
};

// ── DOM refs ───────────────────────────────────────────────────────────────────
const messagesContainer = document.getElementById('messagesContainer');
const messageInput       = document.getElementById('messageInput');
const sendBtn            = document.getElementById('sendBtn');
const clearBtn           = document.getElementById('clearBtn');
const quizPanel          = document.getElementById('quizPanel');
const quizTitle          = document.getElementById('quizTitle');
const quizProgress       = document.getElementById('quizProgress');
const quizScoreLive      = document.getElementById('quizScoreLive');
const quizQuestion       = document.getElementById('quizQuestion');
const quizOptions        = document.getElementById('quizOptions');
const sidebar            = document.getElementById('sidebar');
const mobileMenuBtn      = document.getElementById('mobileMenuBtn');

// ── Init ───────────────────────────────────────────────────────────────────────
renderWelcome();

// ── Event listeners ────────────────────────────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
// Auto-resize textarea
messageInput.addEventListener('input', () => {
  messageInput.style.height = 'auto';
  messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
});

clearBtn.addEventListener('click', () => {
  if (confirm('Clear the conversation?')) {
    state.history = [];
    messagesContainer.innerHTML = '';
    renderWelcome();
    endQuiz();
  }
});

mobileMenuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
document.addEventListener('click', (e) => {
  if (!sidebar.contains(e.target) && e.target !== mobileMenuBtn) {
    sidebar.classList.remove('open');
  }
});

// Sidebar quick-action buttons
document.getElementById('btnLiveScores').addEventListener('click', () => quickSend('Show me live scores right now.'));
document.getElementById('btnFixtures').addEventListener('click', () => quickSend('What are the upcoming Premier League fixtures?'));
document.getElementById('btnStandings').addEventListener('click', () => quickSend('Show me the current Premier League standings table.'));
document.getElementById('btnRules').addEventListener('click', () => quickSend('Explain the offside rule in simple terms.'));
document.getElementById('btnQuizFootball').addEventListener('click', () => startQuiz('football'));
document.getElementById('btnQuizCricket').addEventListener('click', () => startQuiz('cricket'));

// ── Welcome screen ─────────────────────────────────────────────────────────────
function renderWelcome() {
  const suggestions = [
    '⚽ What is offside?',
    '🏏 Explain LBW in cricket',
    '📊 Premier League table',
    '🔴 Live scores',
    '🆚 India vs Australia last match',
    '🧠 Cricket trivia',
  ];
  const chips = suggestions
    .map(s => `<button class="chip" onclick="quickSend('${s.replace(/'/g, "\\'")}')">
                 ${s}
               </button>`)
    .join('');

  const card = document.createElement('div');
  card.className = 'welcome-card';
  card.innerHTML = `
    <span class="welcome-emoji">🏟️</span>
    <h2>Welcome to SportsBot</h2>
    <p>Your AI-powered sports companion. Ask me anything about cricket & football —
       scores, rules, players, history, or take a quiz!</p>
    <div class="suggestion-chips">${chips}</div>
  `;
  messagesContainer.appendChild(card);
}

// ── Send a quick preset message ────────────────────────────────────────────────
function quickSend(text) {
  messageInput.value = text;
  sendMessage();
  sidebar.classList.remove('open');
}

// ── Main send flow ─────────────────────────────────────────────────────────────
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || state.isLoading) return;

  // Remove welcome card on first message
  const welcome = messagesContainer.querySelector('.welcome-card');
  if (welcome) welcome.remove();

  appendMessage('user', text);
  state.history.push({ role: 'user', content: text });

  messageInput.value = '';
  messageInput.style.height = 'auto';
  setLoading(true);

  const typingRow = appendTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: state.history.slice(-20) }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    typingRow.remove();
    appendMessage('bot', data.reply, data.blocked);
    state.history.push({ role: 'model', content: data.reply });

  } catch (err) {
    typingRow.remove();
    appendMessage('bot', `⚠️ **Error:** ${err.message}. Please check the server logs.`, false, true);
  } finally {
    setLoading(false);
  }
}

// ── Append a chat message bubble ───────────────────────────────────────────────
function appendMessage(role, content, blocked = false, isError = false) {
  const row = document.createElement('div');
  row.className = `message-row ${role}`;

  const avatarEl = document.createElement('div');
  avatarEl.className = `avatar ${role}`;
  avatarEl.textContent = role === 'bot' ? '⚽' : '👤';
  avatarEl.setAttribute('aria-hidden', 'true');

  const bubbleEl = document.createElement('div');
  bubbleEl.className = `bubble ${role}${blocked ? ' blocked' : ''}${isError ? ' blocked' : ''}`;
  bubbleEl.innerHTML = renderMarkdown(content);

  const timeEl = document.createElement('div');
  timeEl.className = 'msg-time';
  timeEl.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const msgWrap = document.createElement('div');
  msgWrap.style.display = 'flex';
  msgWrap.style.flexDirection = 'column';
  msgWrap.style.maxWidth = 'min(680px, 78%)';
  msgWrap.appendChild(bubbleEl);
  msgWrap.appendChild(timeEl);

  row.appendChild(avatarEl);
  row.appendChild(msgWrap);
  messagesContainer.appendChild(row);
  scrollToBottom();
}

// ── Typing indicator ───────────────────────────────────────────────────────────
function appendTyping() {
  const row = document.createElement('div');
  row.className = 'message-row bot';

  const avatarEl = document.createElement('div');
  avatarEl.className = 'avatar bot';
  avatarEl.textContent = '⚽';
  avatarEl.setAttribute('aria-hidden', 'true');

  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.setAttribute('aria-label', 'SportsBot is thinking…');
  indicator.innerHTML = `
    <span class="typing-dot"></span>
    <span class="typing-dot"></span>
    <span class="typing-dot"></span>
  `;

  row.appendChild(avatarEl);
  row.appendChild(indicator);
  messagesContainer.appendChild(row);
  scrollToBottom();
  return row;
}

// ── Quiz mode ──────────────────────────────────────────────────────────────────
async function startQuiz(sport) {
  // Remove welcome card if present
  const welcome = messagesContainer.querySelector('.welcome-card');
  if (welcome) welcome.remove();

  appendMessage('bot', `🎯 Starting a **${sport.charAt(0).toUpperCase() + sport.slice(1)} Quiz**! Loading questions…`);
  setLoading(true);

  try {
    const res = await fetch('/api/quiz/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sport }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    state.quiz = {
      active: true,
      sessionId: data.session_id,
      score: 0,
      total: data.total,
      current: 1,
    };

    displayQuizQuestion(data, sport);
  } catch (err) {
    appendMessage('bot', `⚠️ Could not start quiz: ${err.message}`);
  } finally {
    setLoading(false);
  }
  sidebar.classList.remove('open');
}

function displayQuizQuestion(data, sport) {
  const sportLabel = sport || 'Sports';
  quizTitle.textContent = `${sportLabel.charAt(0).toUpperCase() + sportLabel.slice(1)} Quiz`;
  quizProgress.textContent = `Q ${data.question_number} / ${state.quiz.total}`;
  quizScoreLive.textContent = `Score: ${state.quiz.score}`;
  quizQuestion.textContent = data.question;

  quizOptions.innerHTML = '';
  data.options.forEach((opt, idx) => {
    const btn = document.createElement('button');
    btn.className = 'quiz-option-btn';
    btn.textContent = opt;
    btn.setAttribute('role', 'listitem');
    btn.id = `quiz-opt-${idx}`;
    btn.addEventListener('click', () => submitAnswer(idx));
    quizOptions.appendChild(btn);
  });

  quizPanel.classList.remove('hidden');
  scrollToBottom();
}

async function submitAnswer(idx) {
  // Disable all buttons
  const btns = quizOptions.querySelectorAll('.quiz-option-btn');
  btns.forEach(b => { b.disabled = true; });

  try {
    const res = await fetch('/api/quiz/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.quiz.sessionId, answer_index: idx }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Highlight correct/wrong
    btns[idx].classList.add(data.correct ? 'correct' : 'wrong');
    if (!data.correct) {
      // Find the correct button
      data.options && data.options.forEach((opt, i) => {
        if (opt === data.correct_option) btns[i].classList.add('correct');
      });
      // Fallback: find by text
      btns.forEach(b => {
        if (b.textContent === data.correct_option) b.classList.add('correct');
      });
    }

    if (data.correct) state.quiz.score++;
    state.quiz.current++;

    await delay(900);

    if (data.done) {
      endQuiz();
      appendMessage('bot',
        `🏁 **Quiz Complete!**\n\n` +
        `You scored **${data.score} / ${data.total}**\n\n${data.message}`
      );
    } else {
      displayQuizQuestion(data, quizTitle.textContent.replace(' Quiz', '').toLowerCase());
    }
  } catch (err) {
    appendMessage('bot', `⚠️ Quiz error: ${err.message}`);
    endQuiz();
  }
}

function endQuiz() {
  state.quiz.active = false;
  state.quiz.sessionId = null;
  quizPanel.classList.add('hidden');
}

// ── Utilities ──────────────────────────────────────────────────────────────────
function setLoading(val) {
  state.isLoading = val;
  sendBtn.disabled = val;
  messageInput.disabled = val;
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  });
}

function delay(ms) {
  return new Promise(res => setTimeout(res, ms));
}
