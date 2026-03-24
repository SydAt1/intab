/* ═══════════════════════════════════════════════
   InTab — quiz.js
   All quiz state, API calls, fretboard canvas,
   and dashboard population logic.
═══════════════════════════════════════════════ */

/* ─── State ─────────────────────────────────── */
const quizState = {
  sessionId: null,
  score: 0,
  streak: 0,
  peakStreak: 0,
  difficulty: 'beginner',
  questionNumber: 0,
  totalAnswered: 0,
  totalCorrect: 0,
  currentChord: null,
  currentOptions: [],
  ended: false,
  personalBest: 0,
};

/* ─── Auth ───────────────────────────────────── */
function getToken() {
  return localStorage.getItem('access_token') || localStorage.getItem('token') || '';
}
function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` };
}

/* ─── Loading overlay ────────────────────────── */
function showLoading(msg = 'Loading…') {
  document.getElementById('loadingText').textContent = msg;
  document.getElementById('loading-overlay').classList.add('show');
}
function hideLoading() {
  document.getElementById('loading-overlay').classList.remove('show');
}

/* ─── View switching ─────────────────────────── */
function showView(id) {
  ['quiz-lobby', 'quiz-question', 'quiz-results'].forEach(v => {
    document.getElementById(v).style.display = (v === id) ? '' : 'none';
  });
}
function showLobby() {
  showView('quiz-lobby');
  loadDashboard();
}

/* ─── Dashboard ──────────────────────────────── */
async function loadDashboard() {
  try {
    const res = await fetch('/api/quiz/history', { headers: authHeaders() });
    if (!res.ok) return;
    const sessions = await res.json();
    if (!sessions.length) return;

    // Personal best
    const best = sessions.reduce((a, b) => b.final_score > a.final_score ? b : a, sessions[0]);
    quizState.personalBest = best.final_score;
    document.getElementById('personalBestScore').textContent = best.final_score;
    document.getElementById('personalBestDate').textContent =
      'Achieved ' + new Date(best.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    // Bar fill — treat 300pts as 100%
    const pct = Math.min((best.final_score / 300) * 100, 100);
    document.getElementById('pbBarFill').style.width = pct + '%';

    // Mini stats
    document.getElementById('statSessions').textContent = sessions.length;
    document.getElementById('statBestStreak').textContent =
      sessions.reduce((m, s) => Math.max(m, s.final_streak || 0), 0);
    const order = { beginner: 0, intermediate: 1, advanced: 2 };
    const highDiff = sessions.reduce((a, b) =>
      (order[b.difficulty_reached] || 0) > (order[a] || 0) ? b.difficulty_reached : a,
      sessions[0].difficulty_reached
    );
    const diffLabel = { beginner: 'Begn.', intermediate: 'Inter.', advanced: 'Adv.' };
    document.getElementById('statHighDiff').textContent = diffLabel[highDiff] || '—';

    // History rows
    const list = document.getElementById('historyList');
    list.innerHTML = '';
    sessions.slice(0, 7).forEach(s => {
      const row = document.createElement('div');
      row.className = 'history-row';
      const date = new Date(s.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const diff = s.difficulty_reached || 'beginner';
      const diffFull = { beginner: 'Beginner', intermediate: 'Inter.', advanced: 'Advanced' }[diff] || diff;
      row.innerHTML = `
        <span class="hr-date">${date}</span>
        <span class="hr-score">${s.final_score} pts</span>
        <span class="hr-streak">× ${s.final_streak || 0}</span>
        <span class="hr-badge hrb-${diff}">${diffFull}</span>
      `;
      list.appendChild(row);
    });
  } catch (e) {
    console.warn('Dashboard load error:', e);
  }
}

/* ─── Start quiz ─────────────────────────────── */
async function startQuiz() {
  showLoading('Starting…');
  try {
    const res = await fetch('/api/quiz/start', { method: 'POST', headers: authHeaders() });
    const data = await res.json();

    Object.assign(quizState, {
      sessionId: data.session_id,
      score: 0,
      streak: 0,
      peakStreak: 0,
      difficulty: data.difficulty || 'beginner',
      questionNumber: 0,
      totalAnswered: 0,
      totalCorrect: 0,
      currentChord: null,
      currentOptions: [],
      ended: false,
    });

    showView('quiz-question');
    await loadQuestion();
  } catch (e) {
    console.error(e);
    alert('Could not start quiz. Please log in and try again.');
  } finally {
    hideLoading();
  }
}

/* ─── Load question ─────────────────────────── */
async function loadQuestion() {
  quizState.questionNumber++;
  enableOptions();
  updateHUD();

  try {
    const params = new URLSearchParams({
      difficulty: quizState.difficulty,
      question_number: quizState.questionNumber,
    });
    const res = await fetch(`/api/quiz/question?${params}`, { headers: authHeaders() });
    const data = await res.json();

    quizState.currentChord = data.chord;
    quizState.currentOptions = data.options;

    data.options.forEach((label, i) => {
      const btn = document.getElementById(`opt-${i}`);
      btn.textContent = label;
      btn.className = 'opt';
    });

    drawFretboard(data.chord);
  } catch (e) {
    console.error('Question load error:', e);
  }
}

/* ─── Submit answer ─────────────────────────── */
async function submitAnswer(idx) {
  if (quizState.ended) return;
  disableOptions();

  const chosen = quizState.currentOptions[idx];
  const correct = quizState.currentChord.label;

  try {
    const res = await fetch('/api/quiz/answer', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        session_id: quizState.sessionId,
        question_number: quizState.questionNumber,
        chord_shown: correct,
        answer: chosen,
        difficulty: quizState.difficulty,
        current_score: quizState.score,
        current_streak: quizState.streak,
      }),
    });
    const data = await res.json();

    quizState.totalAnswered++;
    if (data.correct) quizState.totalCorrect++;
    quizState.score = data.new_score;
    quizState.streak = data.new_streak;
    quizState.peakStreak = Math.max(quizState.peakStreak, data.new_streak);
    quizState.difficulty = data.new_difficulty;

    // Flash chosen button
    document.getElementById(`opt-${idx}`).classList.add(data.correct ? 'correct' : 'wrong');

    // Reveal correct if wrong
    if (!data.correct) {
      quizState.currentOptions.forEach((opt, i) => {
        if (opt === correct)
          document.getElementById(`opt-${i}`).classList.add('reveal-correct');
      });
    }

    updateHUD();
    setTimeout(loadQuestion, 850);
  } catch (e) {
    console.error('Answer error:', e);
    enableOptions();
  }
}

/* ─── End session ────────────────────────────── */
async function endQuiz() {
  if (quizState.ended) return;
  quizState.ended = true;

  showLoading('Saving…');
  try {
    await fetch('/api/quiz/end', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        session_id: quizState.sessionId,
        final_score: quizState.score,
        final_streak: quizState.peakStreak,
        difficulty_reached: quizState.difficulty,
      }),
    });
  } catch (e) {
    console.warn('End session error:', e);
  } finally {
    hideLoading();
  }

  showResults();
}

/* ─── Show results ───────────────────────────── */
function showResults() {
  const headlines = ['Nice work.', 'Keep going.', 'Well played.', 'Solid session.'];
  document.getElementById('resultsHeadline').textContent =
    headlines[Math.floor(Math.random() * headlines.length)];

  document.getElementById('resScore').textContent = quizState.score;
  document.getElementById('resStreak').textContent = quizState.peakStreak;
  document.getElementById('resCorrect').textContent = `${quizState.totalCorrect}/${quizState.totalAnswered}`;
  document.getElementById('resDifficulty').textContent = quizState.difficulty;

  const isNewBest = quizState.score > quizState.personalBest && quizState.totalAnswered > 0;
  document.getElementById('pbBanner').style.display = isNewBest ? '' : 'none';

  showView('quiz-results');
  loadDashboard(); // refresh in background
}

/* ─── HUD update ─────────────────────────────── */
function updateHUD() {
  document.getElementById('qScore').textContent = quizState.score;
  document.getElementById('qStreak').textContent = quizState.streak;
  document.getElementById('qCounter').textContent =
    'Q ' + String(quizState.questionNumber).padStart(2, '0');

  const badge = document.getElementById('qDifficulty');
  const labels = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' };
  badge.textContent = labels[quizState.difficulty] || quizState.difficulty;
  badge.className = `diff-pill diff-${quizState.difficulty}`;

  // Progress: score / 200 capped at 100%
  const pct = Math.min((quizState.score / 200) * 100, 100);
  document.getElementById('progressFill').style.width = pct + '%';
}

/* ─── Options helpers ────────────────────────── */
function disableOptions() {
  for (let i = 0; i < 4; i++) document.getElementById(`opt-${i}`).disabled = true;
}
function enableOptions() {
  for (let i = 0; i < 4; i++) {
    const b = document.getElementById(`opt-${i}`);
    b.disabled = false;
    b.className = 'opt';
  }
}


/* ═══════════════════════════════════════════════
   FRETBOARD CANVAS RENDERER
   Draws a standard chord diagram.
   chord: { label, frets: int[6], baseFret: int, barres: [] }
   frets array index 0 = string 1 (high e) in chords-db.
   Display: left = low E (index 5), right = high e (index 0).
═══════════════════════════════════════════════ */
function drawFretboard(chord) {
  const canvas = document.getElementById('quiz-fretboard');
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;

  const STRINGS = 6;
  const FRETS_VIS = 5;
  const PAD_T = 32;
  const PAD_L = 22;
  const PAD_R = 14;
  const PAD_B = 16;
  const GW = W - PAD_L - PAD_R;
  const GH = H - PAD_T - PAD_B;
  const SG = GW / (STRINGS - 1);  // string gap
  const FG = GH / FRETS_VIS;      // fret gap
  const DR = SG * 0.3;            // dot radius

  // Palette — dark like the fretboard panel bg (#0c1009)
  const C_BG = '#0c1009';
  const C_FRET = 'rgba(255,255,255,0.09)';
  const C_NUT = '#1DB954';
  const C_DOT = '#1DB954';
  const C_MUTED = 'rgba(255,255,255,0.22)';
  const C_OPEN = '#1DB954';
  const C_FR_N = 'rgba(255,255,255,0.18)';

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = C_BG;
  ctx.fillRect(0, 0, W, H);

  const { frets, baseFret = 1, barres = [] } = chord;

  // ── Nut ──
  if (baseFret === 1) {
    ctx.fillStyle = C_NUT;
    ctx.fillRect(PAD_L - 2, PAD_T, GW + 4, 3);
  } else {
    // base fret number label
    ctx.fillStyle = C_FR_N;
    ctx.font = '500 10px "Space Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`${baseFret}fr`, 1, PAD_T + FG * 0.5 + 4);
  }

  // ── Fret lines ──
  for (let f = 0; f <= FRETS_VIS; f++) {
    const y = PAD_T + f * FG;
    ctx.strokeStyle = C_FRET;
    ctx.lineWidth = f === 0 && baseFret !== 1 ? 1 : 1;
    ctx.beginPath();
    ctx.moveTo(PAD_L, y);
    ctx.lineTo(PAD_L + GW, y);
    ctx.stroke();
  }

  // ── String lines ──
  for (let s = 0; s < STRINGS; s++) {
    const x = PAD_L + s * SG;
    // Thicker for lower strings (left side = low E)
    ctx.strokeStyle = `rgba(255,255,255,${0.06 + (STRINGS - 1 - s) * 0.015})`;
    ctx.lineWidth = 0.8 + (STRINGS - 1 - s) * 0.15;
    ctx.beginPath();
    ctx.moveTo(x, PAD_T);
    ctx.lineTo(x, PAD_T + GH);
    ctx.stroke();
  }

  // ── Barres ──
  if (barres && barres.length) {
    barres.forEach(b => {
      const barFret = typeof b === 'object' ? b.fret : b;
      const fromStr = typeof b === 'object' ? (b.firstString - 1) : 0;
      const toStr = typeof b === 'object' ? (b.lastString - 1) : STRINGS - 1;
      const fi = barFret - baseFret;
      if (fi < 0 || fi >= FRETS_VIS) return;
      const y = PAD_T + fi * FG + FG / 2;
      // Display is reversed: string display index = STRINGS-1 - chords-db index
      const dFrom = STRINGS - 1 - toStr;
      const dTo = STRINGS - 1 - fromStr;
      const x1 = PAD_L + dFrom * SG - DR;
      const x2 = PAD_L + dTo * SG + DR;
      ctx.fillStyle = C_DOT;
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(x1, y - DR, x2 - x1, DR * 2, DR);
      } else {
        ctx.rect(x1, y - DR, x2 - x1, DR * 2);
      }
      ctx.fill();
    });
  }

  // ── Per-string dots, X, O ──
  for (let s = 0; s < STRINGS; s++) {
    // Display left=low E: display string s → frets array index (5 - s)
    const fretVal = frets[5 - s];
    const x = PAD_L + s * SG;

    if (fretVal === -1) {
      // Muted X
      const ty = PAD_T - 16, ts = 5;
      ctx.strokeStyle = C_MUTED;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x - ts, ty - ts); ctx.lineTo(x + ts, ty + ts); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x + ts, ty - ts); ctx.lineTo(x - ts, ty + ts); ctx.stroke();
    } else if (fretVal === 0) {
      // Open circle
      ctx.strokeStyle = C_OPEN;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(x, PAD_T - 14, 4.5, 0, Math.PI * 2);
      ctx.stroke();
    } else {
      // Fretted dot
      const fi = fretVal - baseFret;
      if (fi < 0 || fi >= FRETS_VIS) continue;
      const y = PAD_T + fi * FG + FG / 2;
      // Glowing dot — matches .ndot in index.css
      ctx.shadowColor = C_DOT;
      ctx.shadowBlur = 10;
      ctx.fillStyle = C_DOT;
      ctx.beginPath();
      ctx.arc(x, y, DR, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }
}

/* ─── Init ───────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  showView('quiz-lobby');
  loadDashboard();
});