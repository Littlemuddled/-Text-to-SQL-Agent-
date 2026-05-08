<template>
  <div class="app-shell">
    <aside class="side-panel">
      <div class="brand">
        <div class="brand-mark">DA</div>
        <div>
          <div class="brand-title">data-agent</div>
          <div class="brand-subtitle">数据仓库自然语言查询</div>
        </div>
      </div>

      <div class="system-panel">
        <div class="panel-label">会话状态</div>
        <div class="status-line">
          <span class="status-dot" :class="{ active: loading }"></span>
          <span>{{ loading ? "正在分析" : "就绪" }}</span>
        </div>
        <div class="mini-metrics">
          <div>
            <span>{{ messages.length }}</span>
            <small>消息数</small>
          </div>
          <div>
            <span>{{ loading ? "实时" : "空闲" }}</span>
            <small>响应流</small>
          </div>
        </div>
      </div>

      <div class="query-hints">
        <div class="panel-label">示例问题</div>
        <button
          v-for="item in examples"
          :key="item"
          class="hint"
          type="button"
          @click="question = item"
        >
          {{ item }}
        </button>
      </div>
    </aside>

    <main class="chat-page">
      <header v-if="messages.length === 0" class="top-bar">
        <div>
          <h1>数据分析工作台</h1>
          <p>自然语言驱动的数据查询智能体</p>
        </div>
        <div class="top-badge">
          <span></span>
          SQL 智能体
        </div>
      </header>

      <div
        ref="messagesEl"
        class="messages"
        :class="{ 'has-messages': messages.length > 0 }"
      >
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-kicker">智能取数</div>
          <div class="empty-title">今天想看什么数据？</div>
          <div class="empty-subtitle">销售表现、区域分布、商品结构，都可以直接问。</div>
          <div class="empty-preview">
            <span>销售额</span>
            <span>华东</span>
            <span>品类占比</span>
            <span>GMV</span>
          </div>
        </div>

        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message-row', msg.role]"
        >
          <div v-if="msg.role === 'assistant'" class="avatar assistant-avatar">AI</div>

          <div class="bubble">
            <div v-if="msg.type === 'text'" class="message-text">
              {{ msg.content }}
            </div>

            <div v-else-if="msg.type === 'steps'" class="steps">
              <div class="steps-title">执行链路</div>
              <div v-for="(step, sIdx) in msg.steps" :key="sIdx" class="step">
                <span class="dot" :class="step.status"></span>
                <span>{{ step.text }}</span>
              </div>
            </div>

            <div v-else-if="msg.type === 'table'" class="table-card">
              <div class="table-toolbar">
                <span>查询结果</span>
                <small>{{ msg.rows.length }} 行</small>
              </div>
              <div class="table-wrap">
                <table class="result-table">
                  <thead>
                    <tr>
                      <th v-for="col in msg.columns" :key="col">
                        {{ col }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rIdx) in msg.rows" :key="rIdx">
                      <td v-for="col in msg.columns" :key="col">
                        {{ row[col] }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-else-if="msg.type === 'error'" class="error-text">
              {{ msg.content }}
            </div>
          </div>

          <div v-if="msg.role === 'user'" class="avatar user-avatar">You</div>
        </div>
        <div class="messages-bottom-spacer"></div>
      </div>

      <div class="input-wrapper">
        <div class="input-box">
          <input
            v-model="question"
            @keyup.enter="sendQuestion"
            placeholder="输入销售额、地区、商品、会员等级等分析问题..."
          />
          <button
            class="send-button"
            type="button"
            @click="sendQuestion"
            :disabled="loading"
            :aria-label="loading ? '正在执行查询' : '发送查询'"
          >
            <span v-if="loading" class="spinner"></span>
            <svg
              v-else
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M5 12h14m0 0-6-6m6 6-6 6"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { nextTick, ref } from "vue";

const API_URL = "/api/query";

const examples = [
  "统计2025年1月份各品类的销售额",
  "统计华东地区各品类销售额占比",
  "统计不同会员等级的订单金额",
];

const question = ref("");
const loading = ref(false);
const messages = ref([]);
const messagesEl = ref(null);

function scrollToBottom() {
  const el = messagesEl.value;
  if (!el) return;
  el.scrollTop = el.scrollHeight;
}

async function sendQuestion() {
  if (!question.value || loading.value) return;

  const q = question.value;
  question.value = "";
  loading.value = true;

  messages.value.push({ role: "user", type: "text", content: q });

  const stepIndex =
    messages.value.push({
      role: "assistant",
      type: "steps",
      steps: [],
    }) - 1;

  await nextTick();
  scrollToBottom();

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });

    if (!response.body) throw new Error("服务器未返回流");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop();

      for (const evt of events) {
        const line = evt.trim();
        if (!line.startsWith("data:")) continue;

        let data;
        try {
          data = JSON.parse(line.replace(/^data:\s*/, ""));
        } catch {
          continue;
        }

        const steps = messages.value[stepIndex].steps;

        if (data.stage) {
          const last = steps.at(-1);
          if (last && last.status === "running") last.status = "success";
          steps.push({ text: data.stage, status: "running" });
        } else if (data.error) {
          const last = steps.at(-1);
          if (last) last.status = "error";
          messages.value.push({
            role: "assistant",
            type: "error",
            content: data.error,
          });
        } else if (Array.isArray(data.result)) {
          const last = steps.at(-1);
          if (last) last.status = "success";
          messages.value.push({
            role: "assistant",
            type: "table",
            columns: Object.keys(data.result[0] || {}),
            rows: data.result,
          });
        }

        await nextTick();
        scrollToBottom();
      }
    }
  } catch (e) {
    messages.value.push({
      role: "assistant",
      type: "error",
      content: e?.message || "请求失败",
    });
  } finally {
    loading.value = false;
    await nextTick();
    scrollToBottom();
  }
}
</script>

<style scoped>
:global(html),
:global(body) {
  height: 100%;
  margin: 0;
}

:global(body) {
  min-width: 320px;
  display: block !important;
  color: #17211d;
  background:
    radial-gradient(circle at 16% 8%, rgba(53, 173, 137, 0.24), transparent 31%),
    radial-gradient(circle at 82% 14%, rgba(239, 119, 84, 0.2), transparent 28%),
    linear-gradient(135deg, #eef7f0 0%, #f7f2ea 46%, #eef4f8 100%);
  place-items: unset !important;
}

:global(#app) {
  height: 100%;
  max-width: none !important;
  margin: 0 !important;
  padding: 0 !important;
}

* {
  box-sizing: border-box;
}

.app-shell {
  min-height: 100%;
  display: grid;
  grid-template-columns: 292px minmax(0, 1fr);
  color: #17211d;
}

.side-panel {
  min-height: 100vh;
  padding: 28px 22px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  background: rgba(13, 31, 27, 0.88);
  color: #f4fbf7;
  border-right: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 18px 0 50px rgba(22, 37, 34, 0.18);
}

.brand {
  display: flex;
  align-items: center;
  gap: 13px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(145deg, #69d5b1, #ff9b6a);
  color: #09231b;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
  box-shadow: 0 14px 34px rgba(105, 213, 177, 0.28);
}

.brand-title {
  font-size: 16px;
  font-weight: 760;
  letter-spacing: 0;
}

.brand-subtitle,
.panel-label,
.system-panel small,
.table-toolbar small,
.top-bar p {
  color: rgba(244, 251, 247, 0.62);
}

.brand-subtitle {
  margin-top: 2px;
  font-size: 12px;
}

.system-panel,
.query-hints {
  padding-top: 22px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.panel-label {
  margin-bottom: 12px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.status-line {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 650;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #65d59e;
  box-shadow: 0 0 0 5px rgba(101, 213, 158, 0.14);
}

.status-dot.active {
  background: #ffb15f;
  box-shadow: 0 0 0 5px rgba(255, 177, 95, 0.16);
}

.mini-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 18px;
}

.mini-metrics div {
  min-width: 0;
  padding: 13px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.mini-metrics span,
.mini-metrics small {
  display: block;
}

.mini-metrics span {
  overflow: hidden;
  font-size: 18px;
  font-weight: 760;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-metrics small {
  margin-top: 2px;
  font-size: 11px;
}

.query-hints {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.hint {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.07);
  color: rgba(244, 251, 247, 0.9);
  font: inherit;
  font-size: 13px;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background 160ms ease,
    border-color 160ms ease;
}

.hint:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(105, 213, 177, 0.42);
}

.chat-page {
  position: relative;
  min-width: 0;
  height: 100vh;
  overflow: hidden;
}

.top-bar {
  position: absolute;
  z-index: 3;
  top: 0;
  right: 0;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px clamp(24px, 5vw, 72px) 18px;
  background: linear-gradient(180deg, rgba(247, 246, 240, 0.9), rgba(247, 246, 240, 0));
  pointer-events: none;
}

.top-bar h1 {
  margin: 0;
  color: #17211d;
  font-size: clamp(22px, 2.2vw, 30px);
  line-height: 1.12;
  font-weight: 760;
  letter-spacing: 0;
}

.top-bar p {
  margin: 7px 0 0;
  color: rgba(23, 33, 29, 0.6);
  font-size: 13px;
}

.top-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid rgba(23, 33, 29, 0.09);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.68);
  color: #24352e;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 16px 40px rgba(47, 68, 62, 0.08);
}

.top-badge span {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #27ba78;
}

.messages {
  height: 100%;
  overflow-y: auto;
  padding: 132px clamp(18px, 6vw, 82px) 156px;
  scroll-behavior: smooth;
}

.messages.has-messages {
  padding-top: 34px;
}

.messages::-webkit-scrollbar,
.table-wrap::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.messages::-webkit-scrollbar-thumb,
.table-wrap::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(23, 33, 29, 0.18);
}

.empty-state {
  width: min(720px, 100%);
  margin: 11vh auto 0;
  padding: 34px 36px 32px;
  border: 1px solid rgba(23, 33, 29, 0.07);
  border-radius: 28px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.42), rgba(255, 255, 255, 0.16));
  box-shadow: 0 26px 90px rgba(44, 64, 57, 0.1);
  backdrop-filter: blur(12px);
}

.empty-kicker {
  color: #b96145;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.16em;
}

.empty-title {
  margin-top: 16px;
  color: #17211d;
  font-size: clamp(34px, 4.2vw, 54px);
  font-weight: 760;
  line-height: 1.08;
  letter-spacing: 0;
}

.empty-subtitle {
  max-width: 520px;
  margin-top: 14px;
  color: rgba(23, 33, 29, 0.58);
  font-size: 15px;
  line-height: 1.7;
}

.empty-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 28px;
}

.empty-preview span {
  padding: 9px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(23, 33, 29, 0.07);
  color: #31493f;
  font-size: 12px;
  font-weight: 720;
  box-shadow: 0 12px 30px rgba(47, 68, 62, 0.07);
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-row.user {
  justify-content: flex-end;
}

.avatar {
  flex: 0 0 auto;
  min-width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 780;
  letter-spacing: 0;
}

.assistant-avatar {
  background: #17211d;
  color: #dff8ec;
}

.user-avatar {
  background: #f97352;
  color: #fff7f3;
}

.bubble {
  max-width: min(900px, 78%);
  padding: 15px 16px;
  border: 1px solid rgba(23, 33, 29, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 18px 50px rgba(36, 54, 48, 0.1);
  backdrop-filter: blur(18px);
}

.message-row.user .bubble {
  border-color: rgba(249, 115, 82, 0.18);
  background: linear-gradient(135deg, #f97352, #f6a35c);
  color: #fffaf6;
  box-shadow: 0 18px 42px rgba(194, 91, 62, 0.24);
}

.message-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.steps {
  min-width: min(560px, 62vw);
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.steps-title {
  margin-bottom: 2px;
  color: #31493f;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.step {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 24px;
  color: #24352e;
  font-size: 14px;
}

.dot {
  flex: 0 0 auto;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot.running {
  background: #f4a83d;
  box-shadow: 0 0 0 5px rgba(244, 168, 61, 0.13);
}

.dot.success {
  background: #28b77a;
  box-shadow: 0 0 0 5px rgba(40, 183, 122, 0.13);
}

.dot.error {
  background: #e5484d;
  box-shadow: 0 0 0 5px rgba(229, 72, 77, 0.13);
}

.table-card {
  min-width: min(720px, 72vw);
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
  color: #24352e;
  font-size: 14px;
  font-weight: 760;
}

.table-toolbar small {
  color: rgba(36, 53, 46, 0.55);
  font-size: 12px;
  font-weight: 650;
}

.table-wrap {
  max-width: 100%;
  overflow: auto;
  border: 1px solid rgba(23, 33, 29, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.5);
}

.result-table {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: auto;
}

.result-table th,
.result-table td {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(23, 33, 29, 0.08);
  color: #23342d;
  font-size: 13px;
  text-align: left;
  white-space: nowrap;
}

.result-table th {
  position: sticky;
  z-index: 1;
  top: 0;
  background: #eef7f0;
  color: #416353;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.result-table tbody tr:last-child td {
  border-bottom: 0;
}

.result-table tbody tr:hover td {
  background: rgba(105, 213, 177, 0.1);
}

.error-text {
  color: #b4232a;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.input-wrapper {
  position: fixed;
  z-index: 5;
  right: 0;
  bottom: 24px;
  left: 292px;
  display: flex;
  justify-content: center;
  padding: 0 clamp(18px, 6vw, 82px);
  pointer-events: none;
}

.input-box {
  pointer-events: auto;
  width: min(820px, 100%);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 10px 10px 18px;
  border: 1px solid rgba(23, 33, 29, 0.12);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 22px 70px rgba(36, 54, 48, 0.18);
  backdrop-filter: blur(20px);
}

.input-box input {
  min-width: 0;
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: #17211d;
  font: inherit;
  font-size: 15px;
}

.input-box input::placeholder {
  color: rgba(23, 33, 29, 0.48);
}

.send-button {
  flex: 0 0 auto;
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 16px;
  background: #17211d;
  color: #f5fff9;
  cursor: pointer;
  transition:
    transform 160ms ease,
    opacity 160ms ease,
    background 160ms ease;
}

.send-button:hover:not(:disabled) {
  transform: translateY(-1px);
  background: #263b33;
}

.send-button:disabled {
  cursor: not-allowed;
  opacity: 0.72;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 999px;
  animation: spin 800ms linear infinite;
}

.messages-bottom-spacer {
  height: 150px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 900px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .side-panel {
    min-height: auto;
    padding: 16px;
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .system-panel,
  .query-hints {
    display: none;
  }

  .chat-page {
    height: calc(100vh - 74px);
  }

  .top-bar {
    padding: 20px 18px 12px;
  }

  .top-badge {
    display: none;
  }

  .messages {
    padding: 118px 16px 150px;
  }

  .messages.has-messages {
    padding-top: 18px;
  }

  .bubble {
    max-width: calc(100vw - 88px);
    border-radius: 16px;
  }

  .steps,
  .table-card {
    min-width: 0;
    width: 100%;
  }

  .input-wrapper {
    left: 0;
    bottom: 16px;
    padding: 0 14px;
  }

  .empty-title {
    font-size: 32px;
  }

  .empty-state {
    margin-top: 6vh;
    padding: 26px 22px 24px;
    border-radius: 22px;
  }

  .empty-subtitle {
    font-size: 14px;
  }
}
</style>
