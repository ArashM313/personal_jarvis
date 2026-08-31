const $ = (id) => document.getElementById(id);
const chat = $("chat"), feed = $("feedItems"), orb = $("orb"), status = $("status");

const STATUS_TEXT = {
  sleeping: 'SLEEPING — say "Jarvis wake up"',
  awake: "AWAKE — LISTENING", thinking: "THINKING…", speaking: "SPEAKING…",
};

let ws;
function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = (e) => handle(JSON.parse(e.data));
  ws.onclose = () => setTimeout(connect, 1500);
}
connect();

function handle(evt) {
  switch (evt.type) {
    case "state":
      orb.className = evt.value;
      status.textContent = STATUS_TEXT[evt.value] || evt.value;
      $("wakeBtn").textContent = evt.value === "sleeping" ? "Wake" : "Sleep";
      break;
    case "user_text": addMsg(evt.text, "user"); break;
    case "answer": addMsg(evt.text, "jarvis"); break;
    case "tool_call":
      addFeed(`🔧 <b>${evt.name}</b> ${JSON.stringify(evt.args).slice(0, 120)}`);
      break;
    case "tool_result":
      addFeed(`↳ ${evt.name}: ${String(evt.result).slice(0, 120)}`);
      break;
    case "error": addMsg("⚠️ " + evt.message, "system"); break;
  }
}

function addMsg(text, cls) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}
function addFeed(html) {
  const div = document.createElement("div");
  div.className = "feed-item";
  div.innerHTML = html;
  feed.prepend(div);
}

 $("sendBtn").onclick = send;
 $("input").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
function send() {
  const t = $("input").value.trim();
  if (!t) return;
  $("input").value = "";
  fetch("/api/message", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: t }) });
}

 $("wakeBtn").onclick = () => {
  const sleeping = orb.className === "sleeping";
  fetch("/api/wake", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ awake: sleeping }) });
};
 $("newBtn").onclick = () => { fetch("/api/new", { method: "POST" }); addMsg("— new session —", "system"); };

// ── browser mic: records 16kHz mono WAV, no external deps ──
let media = null, rec = null, chunks = [];
 $("micBtn").onclick = async () => {
  if (media) { stopRec(); return; }
  try {
    media = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
    const ctx = new AudioContext();
    const src = ctx.createMediaStreamSource(media);
    rec = ctx.createScriptProcessor(4096, 1, 1);
    chunks = [];
    rec.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    src.connect(rec); rec.connect(ctx.destination);
    $("micBtn").classList.add("recording");
  } catch (err) { alert("Microphone access denied: " + err.message); media = null; }
};

function stopRec() {
  media.getTracks().forEach((t) => t.stop());
  rec.disconnect(); media = null;
  $("micBtn").classList.remove("recording");
  const rate = rec.context.sampleRate, merged = merge(chunks);
  const pcm = downsample(merged, rate, 16000);
  const blob = encodeWav(pcm, 16000);
  fetch("/api/audio", { method: "POST", body: blob })
    .then((r) => r.json()).then((j) => { if (j.text) addMsg(j.text, "user"); });
}
function merge(arr) {
  const out = new Float32Array(arr.reduce((a, c) => a + c.length, 0));
  let o = 0; for (const c of arr) { out.set(c, o); o += c.length; } return out;
}
function downsample(buf, from, to) {
  const n = Math.floor(buf.length * (to / from));
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = buf[Math.floor(i * (from / to))];
  return out;
}
function encodeWav(s, rate) {
  const b = new ArrayBuffer(44 + s.length * 2), v = new DataView(b);
  const W = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  W(0, "RIFF"); v.setUint32(4, 36 + s.length * 2, true); W(8, "WAVE"); W(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true); W(36, "data");
  v.setUint32(40, s.length * 2, true);
  for (let i = 0; i < s.length; i++) {
    const x = Math.max(-1, Math.min(1, s[i]));
    v.setInt16(44 + i * 2, x < 0 ? x * 0x8000 : x * 0x7fff, true);
  }
  return new Blob([b], { type: "audio/wav" });
}