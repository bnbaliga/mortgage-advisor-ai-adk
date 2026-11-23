// HomeFirst AI Mortgage Advisor - Voice Client
// Professional enterprise UI with real-time voice interaction

const $ = (id) => document.getElementById(id);

// UI Elements
const startCallButton = $("start-call-button");
const endCallButton = $("end-call-button");
const liveIndicator = $("live-indicator");
const sessionEmpty = $("session-empty");
const sessionActive = $("session-active");
const sessionIcon = $("session-icon");
const sessionStatusText = $("session-status-text");
const sessionCount = $("session-count");
const statusBadge = $("status-badge");
const agentBadge = $("agent-badge");
const verificationBadge = $("verification-badge");
const sessionDuration = $("session-duration");
const transcriptPanel = $("transcript-panel");
const transcriptBody = $("transcript-body");
const statusIndicator = $("status-indicator");
const statusDot = $("status-dot");
const statusMessage = $("status-message");
const orb = $("orb");
const usagePanel = $("usage-panel");
const usageInput = $("usage-input");
const usageOutput = $("usage-output");
const usageTotal = $("usage-total");
const usageTotalBig = $("usage-total-big");
const usageCost = $("usage-cost");
const usageInAudio = $("usage-in-audio");
const usageInText = $("usage-in-text");
const usageOutAudio = $("usage-out-audio");
const usageOutText = $("usage-out-text");
const usageTurns = $("usage-turns");
const usageContext = $("usage-context");
const usageContextLimit = $("usage-context-limit");
const usageContextBar = $("usage-context-bar");

// State
const BARGE_RMS = 0.02;
let ws, audioCtx, workletNode, micStream;
let nextStart = 0;
let activeSources = [];
let speaking = false;
let callStartTime = null;
let durationInterval = null;
let isConnected = false;
let currentAgent = "triage";
let verificationLevel = "none";

// --- UI Updates ---

function setOrbState(state) {
  orb.className = "orb " + state;

  // Update status badge
  statusBadge.className = "status-badge " + state;
  const stateLabels = {
    idle: "Idle",
    listening: "Listening",
    thinking: "Processing",
    speaking: "Speaking"
  };
  statusBadge.textContent = stateLabels[state] || state;

  // Update status dot
  statusDot.className = "status-dot " + state;
}

function setStatus(text) {
  sessionStatusText.textContent = text;
  statusMessage.textContent = text;
}

function showSession(active) {
  sessionEmpty.style.display = active ? "none" : "block";
  sessionActive.style.display = active ? "flex" : "none";
  transcriptPanel.style.display = active ? "block" : "none";
  usagePanel.style.display = active ? "block" : "none";
  statusIndicator.style.display = active ? "flex" : "none";
  liveIndicator.style.display = active ? "inline-flex" : "none";
  sessionCount.textContent = active ? "(1)" : "(0)";

  // Toggle buttons - show Start when not active, show End when active
  startCallButton.style.display = active ? "none" : "inline-flex";
  endCallButton.style.display = active ? "inline-flex" : "none";

  if (active) {
    sessionIcon.classList.add("active");
  } else {
    sessionIcon.classList.remove("active");
    // Reset usage display
    usageInput.textContent = "0";
    usageOutput.textContent = "0";
    usageTotal.textContent = "(0)";
    usageTotalBig.textContent = "0";
    usageCost.textContent = "$0.0000";
    usageCost.style.background = "#dcfce7";
    usageCost.style.color = "#059669";
    usageInAudio.textContent = "0";
    usageInText.textContent = "0";
    usageOutAudio.textContent = "0";
    usageOutText.textContent = "0";
    usageTurns.textContent = "0";
    usageContext.textContent = "0";
    usageContextBar.style.width = "0%";
  }
}

function updateUsage(data) {
  const fmt = (n) => (n || 0).toLocaleString();

  // Main totals
  usageInput.textContent = fmt(data.input);
  usageOutput.textContent = fmt(data.output);
  usageTotal.textContent = `(${fmt(data.total)})`;
  usageTotalBig.textContent = fmt(data.total);

  // Modality breakdown
  const by = data.by_modality || {};
  usageInAudio.textContent = fmt(by["in:AUDIO"]);
  usageInText.textContent = fmt(by["in:TEXT"]);
  usageOutAudio.textContent = fmt(by["out:AUDIO"]);
  usageOutText.textContent = fmt(by["out:TEXT"]);

  // Model turns
  usageTurns.textContent = fmt(data.reports);

  // Cost
  if (data.cost_usd !== undefined && data.cost_usd !== null) {
    usageCost.textContent = `$${data.cost_usd.toFixed(4)}`;
  } else {
    usageCost.textContent = "set prices in .env";
    usageCost.style.background = "#f3f4f6";
    usageCost.style.color = "#6b7280";
  }

  // Context memory bar
  const context = data.context || 0;
  const limit = data.context_limit || 100000;
  usageContext.textContent = fmt(context);
  usageContextLimit.textContent = fmt(limit);
  const pct = Math.min(100, (context / limit) * 100);
  usageContextBar.style.width = `${pct}%`;
  usageContextBar.style.background = pct > 80 ? "var(--danger)" : "var(--primary)";
}

function updateAgent(agent) {
  currentAgent = agent;
  agentBadge.className = "agent-badge " + agent;

  const agentNames = {
    triage: "Sam",
    origination: "Mac",
    servicing: "Ivy",
    collections: "Collections",
    welcome: "Welcome"
  };
  agentBadge.textContent = agentNames[agent] || agent;
}

function updateVerification(level) {
  verificationLevel = level;
  verificationBadge.className = "verification-badge " + level;

  const lockIcon = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
  </svg>`;

  const checkIcon = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
  </svg>`;

  const labels = {
    none: "Not Verified",
    basic: "Basic Verified",
    strong: "Strong Verified"
  };

  verificationBadge.innerHTML = (level === "strong" ? checkIcon : lockIcon) + " " + labels[level];
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function startDurationTimer() {
  callStartTime = Date.now();
  durationInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
    sessionDuration.textContent = formatDuration(elapsed);
  }, 1000);
}

function stopDurationTimer() {
  if (durationInterval) {
    clearInterval(durationInterval);
    durationInterval = null;
  }
  sessionDuration.textContent = "0:00";
}

function addTranscript(role, text, agent = null) {
  // Clear empty state if present
  const emptyEl = transcriptBody.querySelector(".transcript-empty");
  if (emptyEl) {
    emptyEl.remove();
  }

  const line = document.createElement("div");
  line.className = "transcript-line";

  const isUser = role === "user";
  const displayName = isUser ? "You" : (agent || getAgentDisplayName());
  const avatarInitial = isUser ? "Y" : displayName.charAt(0);

  line.innerHTML = `
    <div class="transcript-avatar ${isUser ? 'user' : 'agent'}">${avatarInitial}</div>
    <div class="transcript-content">
      <div class="transcript-name">${displayName}</div>
      <div class="transcript-text">${escapeHtml(text)}</div>
    </div>
  `;

  transcriptBody.appendChild(line);
  transcriptBody.scrollTop = transcriptBody.scrollHeight;
}

function getAgentDisplayName() {
  const names = {
    triage: "Sam (Customer Rep)",
    origination: "Mac (Origination)",
    servicing: "Ivy (Servicing)",
    collections: "Collections Agent",
    welcome: "Welcome Agent"
  };
  return names[currentAgent] || "AI Agent";
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function clearTranscript() {
  transcriptBody.innerHTML = '<div class="transcript-empty">Conversation will appear here...</div>';
}


// --- Voice Playback (24k PCM from server) ---

function playVoice(buf) {
  const int16 = new Int16Array(buf);
  const f32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    f32[i] = int16[i] / 0x8000;
  }

  const ab = audioCtx.createBuffer(1, f32.length, 24000);
  ab.getChannelData(0).set(f32);

  const src = audioCtx.createBufferSource();
  src.buffer = ab;
  src.connect(audioCtx.destination);

  const now = audioCtx.currentTime;
  if (nextStart < now) nextStart = now;
  src.start(nextStart);
  nextStart += ab.duration;

  activeSources.push(src);
  src.onended = () => {
    activeSources = activeSources.filter((s) => s !== src);
    if (!activeSources.length) {
      speaking = false;
      setOrbState("listening");
    }
  };

  speaking = true;
  setOrbState("speaking");
}

function stopVoice() {
  activeSources.forEach((s) => {
    try { s.stop(); } catch {}
  });
  activeSources = [];
  nextStart = 0;
  speaking = false;
  if (isConnected) {
    setOrbState("listening");
  }
}

// --- WebSocket Connection ---

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    isConnected = true;
    setStatus("Connected - listening...");
    setOrbState("listening");
    showSession(true);
    startDurationTimer();
  };

  ws.onclose = () => {
    isConnected = false;
    setStatus("Call ended");
    setOrbState("idle");
    showSession(false);
    stopDurationTimer();
    startCallButton.disabled = false;

    // Reset state
    updateAgent("triage");
    updateVerification("none");
    clearTranscript();
  };

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
    setStatus("Connection error");
  };

  ws.onmessage = (evt) => {
    // Binary data = voice audio
    if (typeof evt.data !== "string") {
      playVoice(evt.data);
      return;
    }

    // JSON messages
    const m = JSON.parse(evt.data);

    if (m.type === "transcript") {
      if (m.role === "user") {
        setOrbState("thinking");
      }
      addTranscript(m.role, m.text);
    } else if (m.type === "agent_change") {
      updateAgent(m.agent);
    } else if (m.type === "verification_change") {
      updateVerification(m.level);
    } else if (m.type === "interrupted") {
      stopVoice();
    } else if (m.type === "usage") {
      updateUsage(m);
    } else if (m.type === "error") {
      setStatus("Error: " + m.message);
      console.error(m.message);
    }
  };
}

// --- Microphone Setup ---

async function startMic() {
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  await audioCtx.audioWorklet.addModule("/pcm-processor.js");

  micStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    },
  });

  const source = audioCtx.createMediaStreamSource(micStream);
  workletNode = new AudioWorkletNode(audioCtx, "pcm-processor");

  workletNode.port.onmessage = (e) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(e.data.pcm);
    }
    // Client-side barge-in
    if (e.data.rms >= BARGE_RMS && speaking) {
      stopVoice();
    }
  };

  source.connect(workletNode);
  workletNode.connect(audioCtx.destination);
}

// --- Call Control ---

async function startCall() {
  console.log("Starting call...");
  startCallButton.disabled = true;
  setStatus("Connecting...");
  setOrbState("thinking");

  try {
    await startMic();
    connect();
  } catch (err) {
    console.error("Failed to start call:", err);
    setStatus("Failed to start: " + err.message);
    startCallButton.disabled = false;
  }
}

function endCall() {
  console.log("Ending call...");

  // Close WebSocket first
  if (ws) {
    ws.close();
    ws = null;
  }

  // Stop microphone
  if (micStream) {
    micStream.getTracks().forEach(track => track.stop());
    micStream = null;
  }

  // Close audio context
  if (audioCtx && audioCtx.state !== 'closed') {
    audioCtx.close().catch(() => {});
    audioCtx = null;
  }

  // Stop any playing voice
  stopVoice();

  // Reset UI state
  isConnected = false;
  setStatus("Call ended");
  setOrbState("idle");
  showSession(false);
  stopDurationTimer();
  startCallButton.disabled = false;
  updateAgent("triage");
  updateVerification("none");
  clearTranscript();
}

// --- Event Listeners ---

startCallButton.addEventListener("click", () => {
  console.log("Start button clicked");
  startCall();
});

endCallButton.addEventListener("click", () => {
  console.log("End button clicked");
  endCall();
});

// Initialize UI
updateAgent("triage");
updateVerification("none");
console.log("HomeFirst AI Mortgage Advisor initialized");
