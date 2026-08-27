const API_BASE = "http://127.0.0.1:8000";

const els = {
  messages: document.getElementById("messages"),
  welcome: document.getElementById("welcome"),
  messageInput: document.getElementById("messageInput"),
  sendBtn: document.getElementById("sendBtn"),
  fileInput: document.getElementById("fileInput"),
  attachmentPreview: document.getElementById("attachmentPreview"),
  fileName: document.getElementById("fileName"),
  fileSize: document.getElementById("fileSize"),
  removeFileBtn: document.getElementById("removeFileBtn"),
  historyList: document.getElementById("historyList"),
  newChatBtn: document.getElementById("newChatBtn"),
  clearHistoryBtn: document.getElementById("clearHistoryBtn"),

  modeBtns: [
    ...document.querySelectorAll(".mode-btn")
  ],

  quickBtns: [
    ...document.querySelectorAll(".quick")
  ],

  modalBackdrop:
    document.getElementById("modalBackdrop"),

  modalCloseBtn:
    document.getElementById("modalCloseBtn"),

  modalBody:
    document.getElementById("modalBody"),

  modalTitle:
    document.getElementById("modalTitle"),

  modalEyebrow:
    document.getElementById("modalEyebrow"),

  sidebar:
    document.getElementById("sidebar"),

  mobileMenuBtn:
    document.getElementById("mobileMenuBtn")
};


/* ========================================
   STATE
======================================== */

let selectedFile = null;

let currentMode = "citizen";

let isSending = false;

let conversations = JSON.parse(
  localStorage.getItem("biltek_conversations") || "[]"
);

let currentConversationId = null;


/* ========================================
   HELPERS
======================================== */

function uid() {

  if (crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random()}`;
}


function saveHistory() {

  localStorage.setItem(
    "biltek_conversations",
    JSON.stringify(conversations)
  );

  renderHistory();
}


function currentConversation() {

  return conversations.find(
    conversation =>
      conversation.id === currentConversationId
  );
}


function ensureConversation(
  firstText = "Yeni Sohbet"
) {

  if (
    currentConversationId &&
    currentConversation()
  ) {
    return currentConversation();
  }

  const conversation = {

    id: uid(),

    title:
      (firstText || "Yeni Sohbet")
        .slice(0, 44),

    createdAt: Date.now(),

    updatedAt: Date.now(),

    mode: currentMode,

    messages: []
  };

  conversations.unshift(conversation);

  currentConversationId =
    conversation.id;

  saveHistory();

  return conversation;
}


/* ========================================
   HISTORY
======================================== */
function renderHistory() {

  els.historyList.innerHTML = "";

  const sorted =
    [...conversations]
      .sort(
        (a, b) =>
          b.updatedAt - a.updatedAt
      );


  sorted.forEach(
    conversation => {

      const row =
        document.createElement("div");

      row.className =
        "history-row";


      const button =
        document.createElement("button");

      button.className =
        "history-item" +
        (
          conversation.id ===
          currentConversationId
            ? " active"
            : ""
        );

      button.textContent =
        conversation.title ||
        "Sohbet";


      button.onclick = () => {

        loadConversation(
          conversation.id
        );
      };


      const deleteButton =
        document.createElement("button");

      deleteButton.className =
        "history-delete-btn";

      deleteButton.innerHTML =
        "×";

      deleteButton.title =
        "Sohbeti sil";


      deleteButton.onclick =
        event => {

          event.stopPropagation();

          deleteConversation(
            conversation.id
          );
        };


      row.appendChild(
        button
      );

      row.appendChild(
        deleteButton
      );

      els.historyList.appendChild(
        row
      );
    }
  );
}
function deleteConversation(
  id
) {

  const isCurrent =
    currentConversationId === id;


  conversations =
    conversations.filter(
      conversation =>
        conversation.id !== id
    );


  if (isCurrent) {

    currentConversationId =
      null;

    selectedFile =
      null;

    els.fileInput.value =
      "";

    updateAttachment();

    els.messages.innerHTML =
      "";

    els.welcome
      .classList
      .remove(
        "hidden"
      );
  }


  saveHistory();
}

function loadConversation(id) {

  currentConversationId = id;

  const conversation =
    currentConversation();

  if (!conversation) {
    return;
  }

  currentMode =
    conversation.mode ||
    "citizen";

  updateModeUI();

  renderConversation(
    conversation
  );

  renderHistory();

  els.sidebar.classList.remove(
    "open"
  );
}


function renderConversation(
  conversation
) {

  els.messages.innerHTML = "";

  els.welcome.classList.toggle(
    "hidden",
    conversation.messages.length > 0
  );

  conversation.messages.forEach(
    message => {

      if (message.role === "user") {

        renderUserMessage(
          message
        );

      } else {

        renderAssistantMessage(
          message
        );
      }
    }
  );

  scrollToBottom();
}


function newConversation() {

  currentConversationId = null;

  selectedFile = null;

  els.fileInput.value = "";

  updateAttachment();

  els.messages.innerHTML = "";

  els.welcome.classList.remove(
    "hidden"
  );

  renderHistory();

  els.messageInput.focus();
}


/* ========================================
   MODE
======================================== */

function updateModeUI() {

  els.modeBtns.forEach(
    button => {

      button.classList.toggle(
        "active",
        button.dataset.mode ===
        currentMode
      );
    }
  );
}


els.modeBtns.forEach(
  button => {

    button.addEventListener(
      "click",
      () => {

        const nextMode =
          button.dataset.mode;

        // Aynı mod seçildiyse hiçbir şey yapma
        if (nextMode === currentMode) {
          return;
        }

        currentMode = nextMode;

        updateModeUI();

        // Seçilen moda ait son konuşmayı bul
        const modeConversation =
          conversations
            .filter(
              conversation =>
                (conversation.mode || "citizen") ===
                currentMode
            )
            .sort(
              (a, b) =>
                (b.updatedAt || 0) -
                (a.updatedAt || 0)
            )[0];

        // Daha önce bu modda konuşma varsa aç
        if (modeConversation) {

          loadConversation(
            modeConversation.id
          );

        } else {

          // Bu mod için henüz konuşma yoksa
          // boş yeni sohbet göster
          newConversation();
        }
      }
    );
  }
);

/* ========================================
   QUICK QUESTIONS
======================================== */

els.quickBtns.forEach(
  button => {

    button.onclick = () => {

      els.messageInput.value =
        button.dataset.prompt || "";

      autoResize();

      els.messageInput.focus();
    };
  }
);


/* ========================================
   SIDEBAR BUTTONS
======================================== */

els.newChatBtn.onclick =
  newConversation;


els.clearHistoryBtn.onclick =
  () => {

    conversations = [];

    currentConversationId = null;

    saveHistory();

    newConversation();
  };


els.mobileMenuBtn.onclick =
  () => {

    els.sidebar.classList.toggle(
      "open"
    );
  };


/* ========================================
   FILE UPLOAD
======================================== */

els.fileInput.addEventListener(
  "change",
  event => {

    selectedFile =
      event.target.files?.[0] ||
      null;

    updateAttachment();
  }
);


els.removeFileBtn.onclick =
  () => {

    selectedFile = null;

    els.fileInput.value = "";

    updateAttachment();
  };


function updateAttachment() {

  if (!selectedFile) {

    els.attachmentPreview
      .classList
      .add("hidden");

    return;
  }

  els.fileName.textContent =
    selectedFile.name;

  els.fileSize.textContent =
    `${(
      selectedFile.size / 1024
    ).toFixed(1)} KB`;

  els.attachmentPreview
    .classList
    .remove("hidden");
}


/* ========================================
   TEXTAREA
======================================== */

function autoResize() {

  els.messageInput.style.height =
    "auto";

  els.messageInput.style.height =
    Math.min(
      els.messageInput.scrollHeight,
      150
    ) + "px";
}


els.messageInput.addEventListener(
  "input",
  autoResize
);


els.messageInput.addEventListener(
  "keydown",
  event => {

    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {

      event.preventDefault();

      sendMessage();
    }
  }
);


els.sendBtn.onclick =
  sendMessage;


/* ========================================
   USER MESSAGE
======================================== */

function renderUserMessage(
  message
) {

  els.welcome.classList.add(
    "hidden"
  );

  const row =
    document.createElement("div");

  row.className =
    "message-row user";

  row.innerHTML = `
    <div class="bubble"></div>
  `;

  row
    .querySelector(".bubble")
    .textContent =

      message.text ||

      (
        message.fileName
          ? `📎 ${message.fileName}`
          : "Belge gönderildi"
      );

  els.messages.appendChild(
    row
  );
}


/* ========================================
   ASSISTANT MESSAGE
======================================== */

function renderAssistantMessage(
  message,
  live = false
) {

  els.welcome.classList.add(
    "hidden"
  );

  const row =
    document.createElement("div");

  row.className =
    `message-row assistant ${
      message.mode === "expert"
        ? "expert"
        : ""
    }`;

  row.dataset.messageId =
    message.id || "";

  const title =
    message.mode === "expert"
      ? "UZMAN DEĞERLENDİRMESİ"
      : "BİLTEK YANITI";

  const technicalButton =
    message.mode === "expert"
      ? `
        <button
          class="action-btn details-btn"
        >
          Teknik Detaylar
        </button>
      `
      : "";

  row.innerHTML = `

    <div class="avatar">
      BT
    </div>

    <div class="bubble">

      <div class="answer-card">

        <div class="answer-title">
          ${title}
        </div>

        <div class="answer-text"></div>

        <div class="answer-actions">

          <button
            class="action-btn sources-btn"
          >
            Kaynakları Gör
          </button>

          <button
            class="action-btn primary official-btn"
          >
            Resmi Yazı Oluştur
          </button>

          ${technicalButton}

        </div>

      </div>

    </div>
  `;

  row
    .querySelector(".answer-text")
    .textContent =
      message.text || "";


  row
    .querySelector(".sources-btn")
    .onclick =
      () => {

        openSources(
          message.sources || []
        );
      };


  row
    .querySelector(".official-btn")
    .onclick =
      () => {

        openOfficialWriting(
          message
        );
      };


  const detailsButton =
    row.querySelector(
      ".details-btn"
    );


  if (detailsButton) {

    detailsButton.onclick =
      () => {

        openDetails(
          message.raw || {}
        );
      };
  }


  els.messages.appendChild(
    row
  );


  if (!live) {
    scrollToBottom();
  }


  return row;
}


/* ========================================
   THINKING ANIMATION
======================================== */

function renderThinking() {

  const row =
    document.createElement("div");

  row.className =
    "message-row assistant";

  row.id =
    "thinkingRow";

  row.innerHTML = `

    <div class="avatar">
      BT
    </div>

    <div class="thinking">

      BİLTEK düşünüyor

      <span class="dots">
        <i></i>
        <i></i>
        <i></i>
      </span>

    </div>
  `;

  els.messages.appendChild(
    row
  );

  scrollToBottom();
}


function removeThinking() {

  document
    .getElementById(
      "thinkingRow"
    )
    ?.remove();
}


/* ========================================
   SCROLL
======================================== */

function scrollToBottom() {

  const stage =
    document.querySelector(
      ".chat-stage"
    );

  requestAnimationFrame(
    () => {

      stage.scrollTo({

        top:
          stage.scrollHeight,

        behavior:
          "smooth"

      });
    }
  );
}
/* ========================================
   EXTRACT DATA FROM BACKEND
======================================== */

function extractAnswer(data) {

  if (!data) {
    return "Yanıt alınamadı.";
  }

  // Question → RAG
  if (
    data.route === "question" &&
    data.rag?.answer
  ) {
    return data.rag.answer;
  }

  // Expert mode
  if (currentMode === "expert") {

    const analysis =
      data.evrak_analysis || {};

    const rag =
      data.rag || {};

    const routing =
      data.routing || {};

    const parts = [];


    if (analysis.summary) {

      parts.push(
        `BELGE DEĞERLENDİRMESİ\n${analysis.summary}`
      );
    }


    if (analysis.topic) {

      const topic =
        typeof analysis.topic === "object"
          ? analysis.topic.value ||
            analysis.topic.label ||
            JSON.stringify(analysis.topic)
          : analysis.topic;

      parts.push(
        `KONU\n${topic}`
      );
    }


    if (analysis.purpose) {

      const purpose =
        typeof analysis.purpose === "object"
          ? analysis.purpose.value ||
            analysis.purpose.label ||
            JSON.stringify(analysis.purpose)
          : analysis.purpose;

      parts.push(
        `AMAÇ\n${purpose}`
      );
    }


    if (rag.answer) {

      parts.push(
        `MEVZUAT ANALİZİ\n${rag.answer}`
      );
    }


    if (
      routing.selected_department
    ) {

      let departmentText =
        `İLGİLİ BİRİM\n${routing.selected_department}`;

      if (routing.reason) {

        departmentText +=
          `\n${routing.reason}`;
      }

      parts.push(
        departmentText
      );
    }


    if (parts.length > 0) {

      return parts.join(
        "\n\n"
      );
    }


    return "Analiz tamamlandı.";
  }


  // Citizen mode
  const analysis =
    data.evrak_analysis || {};


  if (analysis.summary) {

    return analysis.summary;
  }


  if (data.rag?.answer) {

    return data.rag.answer;
  }


  if (
    data.official_writing?.body
  ) {

    return data.official_writing.body;
  }


  return "Belge analizi tamamlandı.";
}


/* ========================================
   SOURCES
======================================== */

function extractSources(data) {

  if (!data) {
    return [];
  }

  if (
    Array.isArray(
      data.rag?.sources
    )
  ) {

    return data.rag.sources;
  }

  return [];
}


/* ========================================
   SIMPLE CITIZEN VIEW
======================================== */

function simpleCitizenText(text) {

  if (!text) {
    return text;
  }

  return String(text)

    .replace(
      /\*\*/g,
      ""
    )

    .replace(
      /^#{1,6}\s*/gm,
      ""
    )

    .trim();
}


/* ========================================
   SEND MESSAGE
======================================== */

async function sendMessage() {

  if (isSending) {
    return;
  }


  const text =
    els.messageInput
      .value
      .trim();


  if (
    !text &&
    !selectedFile
  ) {

    return;
  }


  isSending = true;

  els.sendBtn.disabled =
    true;


  const conversation =
    ensureConversation(

      text ||

      selectedFile?.name ||

      "Belge Analizi"
    );


  conversation.mode =
    currentMode;

  conversation.updatedAt =
    Date.now();


  const userMessage = {

    id: uid(),

    role: "user",

    text: text,

    fileName:
      selectedFile?.name ||
      null,

    createdAt:
      Date.now()
  };


  conversation.messages.push(
    userMessage
  );


  renderUserMessage(
    userMessage
  );


  saveHistory();


  els.messageInput.value =
    "";

  autoResize();


  renderThinking();


  const fileForRequest =
    selectedFile;


  selectedFile =
    null;


  els.fileInput.value =
    "";


  updateAttachment();


  try {

    /* ========================================
       QUESTION ONLY
       TRY STREAMING FIRST
    ======================================== */

    if (
      !fileForRequest &&
      text
    ) {

      const streamed =
        await tryStreamingQuestion(
          text,
          conversation
        );


      if (streamed) {

        return;
      }
    }


    /* ========================================
       NORMAL /PROCESS
    ======================================== */

    const form =
  new FormData();

form.append(
  "mode",
  currentMode
);

if (text) {
  form.append(
    "question",
    text
  );
}


    if (fileForRequest) {

      form.append(
        "file",
        fileForRequest
      );
    }


    const response =
      await fetch(
        `${API_BASE}/process`,
        {
          method: "POST",
          body: form
        }
      );


    if (!response.ok) {

      const detail =
        await response.text();


      throw new Error(

        detail ||

        `HTTP ${response.status}`
      );
    }


    const data =
      await response.json();


    removeThinking();


    let answer =
      extractAnswer(data);


    if (
      currentMode ===
      "citizen"
    ) {

      answer =
        simpleCitizenText(
          answer
        );
    }


    const assistantMessage = {

      id: uid(),

      role:
        "assistant",

      text:
        answer,

      mode:
        currentMode,

      sources:
        extractSources(data),

      raw:
        data,

      officialWriting:
        data.official_writing ||
        null,

      createdAt:
        Date.now()
    };


    conversation.messages.push(
      assistantMessage
    );


    conversation.updatedAt =
      Date.now();


    renderAssistantMessage(
      assistantMessage
    );


    saveHistory();

  }

  catch (error) {

    removeThinking();


    const errorMessage = {

      id: uid(),

      role:
        "assistant",

      mode:
        currentMode,

      text:
        `İşlem sırasında bir hata oluştu.\n${error.message}`,

      sources: [],

      raw: {},

      createdAt:
        Date.now()
    };


    conversation.messages.push(
      errorMessage
    );


    renderAssistantMessage(
      errorMessage
    );


    saveHistory();

  }

  finally {

    isSending =
      false;


    els.sendBtn.disabled =
      false;


    scrollToBottom();
  }
}


/* ========================================
   STREAMING
======================================== */

/*
Backend'te:

POST /chat/stream

varsa bu fonksiyon cevabı
parça parça gösterecek.

Endpoint henüz yoksa otomatik olarak
/process endpoint'ine geri döner.
*/

async function tryStreamingQuestion(
  text,
  conversation
) {

  let response;


  try {

    response =
      await fetch(
        `${API_BASE}/chat/stream`,
        {

          method:
            "POST",

          headers: {

            "Content-Type":
              "application/json"
          },

          body:
            JSON.stringify({

              text:
                text,

              mode:
                currentMode
            })
        }
      );

  }

  catch (error) {

    return false;
  }


  if (
    !response.ok ||
    !response.body
  ) {

    return false;
  }


  removeThinking();


  const assistantMessage = {

    id: uid(),

    role:
      "assistant",

    text:
      "",

    mode:
      currentMode,

    sources:
      [],

    raw:
      {},

    createdAt:
      Date.now()
  };


  const row =
    renderAssistantMessage(
      assistantMessage,
      true
    );


  const answerElement =
    row.querySelector(
      ".answer-text"
    );


  const reader =
    response.body
      .getReader();


  const decoder =
    new TextDecoder();


  let completeText =
    "";


  let carry =
    "";


  while (true) {

    const {
      value,
      done
    } =
      await reader.read();


    if (done) {
      break;
    }


    const chunk =
      decoder.decode(
        value,
        {
          stream: true
        }
      );


    carry += chunk;


    /* ========================================
       SSE FORMAT
       data: ...
    ======================================== */

    if (
      carry.includes(
        "data:"
      )
    ) {

      const lines =
        carry.split("\n");


      carry =
        lines.pop() || "";


      for (
        const line
        of lines
      ) {

        if (
          !line.startsWith(
            "data:"
          )
        ) {

          continue;
        }


        const payload =
          line
            .slice(5)
            .trim();


        if (
          !payload ||
          payload === "[DONE]"
        ) {

          continue;
        }


        try {

          const parsed =
            JSON.parse(
              payload
            );


          const token =

            parsed.token ??

            parsed.content ??

            parsed.text ??

            "";


          completeText +=
            token;


          if (
            parsed.sources
          ) {

            assistantMessage.sources =
              parsed.sources;
          }

        }

        catch {

          completeText +=
            payload;
        }
      }
    }

    else {

      completeText +=
        carry;


      carry =
        "";
    }


    assistantMessage.text =
      completeText;


    if (
      currentMode ===
      "citizen"
    ) {

      answerElement.textContent =
        simpleCitizenText(
          completeText
        );

    }

    else {

      answerElement.textContent =
        completeText;
    }


    scrollToBottom();
  }


  assistantMessage.text =

    currentMode ===
    "citizen"

      ? simpleCitizenText(
          completeText
        )

      : completeText;


  conversation.messages.push(
    assistantMessage
  );


  conversation.updatedAt =
    Date.now();


  saveHistory();


  return true;
}


/* ========================================
   MODAL
======================================== */

function openModal(
  title,
  eyebrow,
  html
) {

  els.modalTitle.textContent =
    title;


  els.modalEyebrow.textContent =
    eyebrow;


  els.modalBody.innerHTML =
    html;


  els.modalBackdrop
    .classList
    .remove(
      "hidden"
    );
}


function closeModal() {

  els.modalBackdrop
    .classList
    .add(
      "hidden"
    );
}


els.modalCloseBtn.onclick =
  closeModal;


els.modalBackdrop
  .addEventListener(
    "click",
    event => {

      if (
        event.target ===
        els.modalBackdrop
      ) {

        closeModal();
      }
    }
  );


/* ========================================
   HTML ESCAPE
======================================== */

function escapeHtml(
  value = ""
) {

  return String(value)

    .replaceAll(
      "&",
      "&amp;"
    )

    .replaceAll(
      "<",
      "&lt;"
    )

    .replaceAll(
      ">",
      "&gt;"
    )

    .replaceAll(
      '"',
      "&quot;"
    );
}


/* ========================================
   SOURCES POPUP
======================================== */

/* ========================================
   SOURCES POPUP
======================================== */

function openSources(
  sources
) {

  if (
    !sources ||
    !sources.length
  ) {

    openModal(
      "Kullanılan Kaynaklar",
      "KAYNAKLAR",
      `
        <p>
          Bu yanıt için görüntülenecek
          kaynak bulunamadı.
        </p>
      `
    );

    return;
  }


  const html =
    sources
      .map(
        (source, index) => {

          const title =
            source.title ||
            source.law_title ||
            source.law_number ||
            "Mevzuat Kaynağı";


          const info = [

            source.law_number,

            source.article,

            source.article_number

          ]
            .filter(Boolean)
            .join(" • ");


          /*
            Backend'ten gelen gerçek
            mevzuat / madde metni.
          */

          const content =
            source.content ||
            source.text ||
            source.page_content ||
            "";


          return `

            <div
              class="source-item"
              style="
                display:block;
                padding:18px 0;
              "
            >

              <!-- KAYNAK BAŞLIĞI -->

              <button
                type="button"

                class="source-toggle"

                data-source-index="${index}"

                style="
                  width:100%;

                  border:none;

                  background:none;

                  padding:0;

                  color:inherit;

                  cursor:pointer;

                  text-align:left;

                  display:flex;

                  align-items:center;

                  justify-content:
                    space-between;

                  gap:16px;
                "
              >


                <div
                  style="
                    flex:1;
                    min-width:0;
                  "
                >

                  <strong
                    style="
                      display:block;

                      margin-bottom:8px;

                      font-size:15px;
                    "
                  >

                    ${index + 1}.

                    ${escapeHtml(
                      title
                    )}

                  </strong>


                  <span
                    style="
                      color:#8fa9c2;

                      font-size:12px;
                    "
                  >

                    ${escapeHtml(
                      info
                    )}

                  </span>

                </div>


                <!-- OK -->

                <span
                  class="source-arrow"

                  style="
                    font-size:18px;

                    color:#6cbcff;

                    flex:
                      0 0 auto;
                  "
                >

                  ▼

                </span>

              </button>


              <!-- GERÇEK KAYNAK METNİ -->

              <div
                class="source-content"

                data-source-content="${index}"

                style="
                  display:none;

                  margin-top:18px;

                  padding:
                    18px
                    20px;

                  border-radius:10px;

                  background:
                    rgba(
                      255,
                      255,
                      255,
                      0.04
                    );

                  border:
                    1px solid
                    rgba(
                      255,
                      255,
                      255,
                      0.08
                    );

                  white-space:
                    pre-wrap;

                  line-height:1.75;

                  color:#c8d8e7;

                  font-size:13px;
                "
              >

                ${
                  content

                    ? escapeHtml(
                        content
                      )

                    : `
                      Kaynak metni
                      bulunamadı.
                    `
                }

              </div>

            </div>

          `;
        }
      )

      .join("");


  /* ========================================
     MODAL AÇ
  ======================================== */

  openModal(
    "Kullanılan Kaynaklar",
    "KAYNAKLAR",
    html
  );


  /* ========================================
     KAYNAĞA TIKLAMA
  ======================================== */

  document
    .querySelectorAll(
      ".source-toggle"
    )
    .forEach(
      button => {

        button.onclick =
          () => {

            const index =
              button
                .dataset
                .sourceIndex;


            const content =
              document.querySelector(

                `[data-source-content="${index}"]`

              );


            const arrow =
              button.querySelector(
                ".source-arrow"
              );


            if (!content) {

              return;
            }


            const isOpen =

              content.style.display ===
              "block";


            /* ========================================
               AÇ / KAPAT
            ======================================== */

            content.style.display =

              isOpen
                ? "none"
                : "block";


            /* ========================================
               OK İŞARETİ
            ======================================== */

            if (arrow) {

              arrow.textContent =

                isOpen
                  ? "▼"
                  : "▲";
            }

          };
      }
    );
}
/* ========================================
   ON-DEMAND RESMI YAZI
======================================== */

function openOfficialWriting(message) {

  const raw = message.raw || {};
  const analysis = raw.evrak_analysis || {};
  const entities = analysis.entities || {};

  const ocrMetadata =
    raw.ocr?.input?.metadata ||
    raw.ocr?.parsed_metadata ||
    {};

  /* ========================================
     BELGE ANALIZI KONTROL
  ======================================== */

  if (
    !raw.evrak_analysis ||
    Object.keys(raw.evrak_analysis).length === 0
  ) {

    openModal(
      "Resmi Yazı",
      "RESMİ YAZI",
      `
        <p>
          Resmi yazı oluşturmak için
          önce bir belge analizi yapılmalıdır.
        </p>
      `
    );

    return;
  }


  /* ========================================
     HELPER
  ======================================== */

  function textValue(value) {

    if (!value) {
      return "";
    }

    if (typeof value === "string") {
      return value.trim();
    }

    if (typeof value === "object") {

      return (
        value.value ||
        value.label ||
        value.text ||
        ""
      )
        .toString()
        .trim();
    }

    return String(value).trim();
  }


  /* ========================================
     DEFAULT MUHATAP
  ======================================== */

  const defaultRecipient =
    textValue(
      ocrMetadata.muhatap ||
      entities.muhatap
    );


  /* ========================================
     ÖNERİLEN YAZI TÜRÜ
  ======================================== */

  const suggestedType =
    message.officialWriting?.type ||
    raw.official_writing?.type ||
    "";


  /* ========================================
     FORM MODAL
  ======================================== */

  openModal(
    "Resmi Yazı Oluştur",
    "RESMİ YAZI",
    `
      <div
        style="
          max-width:620px;
          margin:auto;
        "
      >

        <div
          style="
            margin-bottom:24px;
            line-height:1.6;
            color:#bcd0e3;
          "
        >
          Oluşturmak istediğiniz resmi yazının
          türünü ve muhatabını belirleyebilirsiniz.
        </div>


        <!-- YAZI TÜRÜ -->

        <div
          style="
            margin-bottom:20px;
          "
        >

          <label
            for="officialWritingType"
            style="
              display:block;
              margin-bottom:8px;
              font-weight:700;
            "
          >
            Yazı Türü
          </label>


          <select
            id="officialWritingType"
            style="
              width:100%;
              box-sizing:border-box;
              padding:12px 14px;
              border-radius:9px;
              border:1px solid rgba(255,255,255,.15);
              background:#10283d;
              color:#ffffff;
              font-size:14px;
              outline:none;
            "
          >

            <option value="">
              Otomatik Belirle
            </option>

            <option
              value="talep_yazisi"
              ${
                suggestedType === "talep_yazisi"
                  ? "selected"
                  : ""
              }
            >
              Talep Yazısı
            </option>

            <option
              value="cevap_yazisi"
              ${
                suggestedType === "cevap_yazisi"
                  ? "selected"
                  : ""
              }
            >
              Cevap Yazısı
            </option>

            <option
              value="bilgilendirme_yazisi"
              ${
                suggestedType === "bilgilendirme_yazisi"
                  ? "selected"
                  : ""
              }
            >
              Bilgilendirme Yazısı
            </option>

            <option
              value="basvuru_cevabi"
              ${
                suggestedType === "basvuru_cevabi"
                  ? "selected"
                  : ""
              }
            >
              Başvuru Cevabı
            </option>

          </select>

        </div>


        <!-- MUHATAP -->

        <div
          style="
            margin-bottom:24px;
          "
        >

          <label
            for="officialWritingRecipient"
            style="
              display:block;
              margin-bottom:8px;
              font-weight:700;
            "
          >
            Muhatap
          </label>


          <input
            id="officialWritingRecipient"
            type="text"
            value="${escapeHtml(defaultRecipient)}"
            placeholder="Örn: İstanbul Büyükşehir Belediyesi"
            style="
              width:100%;
              box-sizing:border-box;
              padding:12px 14px;
              border-radius:9px;
              border:1px solid rgba(255,255,255,.15);
              background:#10283d;
              color:#ffffff;
              font-size:14px;
              outline:none;
            "
          >


          <div
            style="
              margin-top:7px;
              color:#7896b0;
              font-size:11px;
            "
          >
            Boş bırakırsanız belgede bulunan
            muhatap bilgisi kullanılır.
          </div>

        </div>


        <!-- OLUŞTUR BUTTON -->

        <div
          style="
            display:flex;
            justify-content:flex-end;
          "
        >

          <button
            id="createOfficialWritingBtn"
            type="button"
            class="action-btn primary"
            style="
              min-width:170px;
              padding:11px 18px;
            "
          >
            Resmi Yazı Oluştur
          </button>

        </div>


        <!-- STATUS -->

        <div
          id="officialWritingStatus"
          style="
            display:none;
            margin-top:18px;
            padding:12px;
            border-radius:8px;
            background:rgba(255,255,255,.04);
            color:#bcd0e3;
            font-size:13px;
          "
        >
        </div>

      </div>
    `
  );


  /* ========================================
     ELEMENTLER
  ======================================== */

  const createButton =
    document.getElementById(
      "createOfficialWritingBtn"
    );

  const typeSelect =
    document.getElementById(
      "officialWritingType"
    );

  const recipientInput =
    document.getElementById(
      "officialWritingRecipient"
    );

  const statusElement =
    document.getElementById(
      "officialWritingStatus"
    );


  if (!createButton) {
    return;
  }


  /* ========================================
     CREATE
  ======================================== */

  createButton.onclick =
    async () => {

      const writingType =
        typeSelect?.value ||
        null;

      const recipient =
        recipientInput?.value
          ?.trim() ||
        null;


      createButton.disabled = true;

      createButton.textContent =
        "Oluşturuluyor...";


      if (statusElement) {

        statusElement.style.display =
          "block";

        statusElement.textContent =
          "Resmi yazı hazırlanıyor...";
      }


      try {

        /* ========================================
           BACKEND
        ======================================== */

        const response =
          await fetch(
            `${API_BASE}/official-writing`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body:
                JSON.stringify({

                  evrak_analysis:
                    raw.evrak_analysis,

                  ocr_result:
                    raw.ocr || null,

                  rag_result:
                    raw.rag || null,

                  routing_result:
                    raw.routing || null,

                  writing_type:
                    writingType,

                  recipient:
                    recipient

                })
            }
          );


        if (!response.ok) {

          const errorText =
            await response.text();

          throw new Error(
            errorText ||
            `HTTP ${response.status}`
          );
        }


        const data =
          await response.json();


        const generated =
          data.official_writing;


        if (
          !generated ||
          !generated.body
        ) {

          throw new Error(
            "Resmi yazı metni oluşturulamadı."
          );
        }


        /* ========================================
           MESSAGE'E KAYDET
        ======================================== */

        message.officialWriting =
          generated;

        message.officialRecipient =
          recipient ||
          defaultRecipient ||
          "";


        if (!message.raw) {
          message.raw = {};
        }


        message.raw.official_writing =
          generated;


        saveHistory();


        /* ========================================
           PREVIEW
        ======================================== */

        showOfficialWritingPreview(
          message,
          message.officialRecipient
        );

      }

      catch (error) {

        console.error(
          "Official writing error:",
          error
        );


        createButton.disabled =
          false;

        createButton.textContent =
          "Resmi Yazı Oluştur";


        if (statusElement) {

          statusElement.style.display =
            "block";

          statusElement.textContent =
            `Hata: ${error.message}`;
        }
      }
    };
}


/* ========================================
   RESMI YAZI PREVIEW
======================================== */

function showOfficialWritingPreview(
  message,
  recipientOverride = ""
) {

  const officialWriting =
    message.officialWriting ||
    message.raw?.official_writing;


  if (!officialWriting?.body) {
    return;
  }


  const raw =
    message.raw || {};

  const analysis =
    raw.evrak_analysis || {};

  const entities =
    analysis.entities || {};

  const routing =
    raw.routing || {};

  const ocrMetadata =
    raw.ocr?.input?.metadata ||
    raw.ocr?.parsed_metadata ||
    {};


  /* ========================================
     HELPER
  ======================================== */

  function textValue(value) {

    if (!value) {
      return "";
    }

    if (typeof value === "string") {
      return value.trim();
    }

    if (typeof value === "object") {

      return (
        value.value ||
        value.label ||
        value.text ||
        ""
      )
        .toString()
        .trim();
    }

    return String(value).trim();
  }


  /* ========================================
     SUBJECT
  ======================================== */

  const subject =
    textValue(
      officialWriting.subject
    ) ||
    textValue(
      analysis.topic
    ) ||
    "Konu belirtilmedi";


  /* ========================================
     SAYI
  ======================================== */

  const rawSayi =
    textValue(
      ocrMetadata.sayi ||
      entities.sayi
    );


  const sayi =
    /\d/.test(rawSayi)
      ? rawSayi
      : "";


  /* ========================================
     TARİH
  ======================================== */

  const tarih =
    textValue(
      ocrMetadata.tarih ||
      entities.tarih
    );


  /* ========================================
     MUHATAP
  ======================================== */

  let recipient =
    textValue(
      recipientOverride ||
      message.officialRecipient ||
      ocrMetadata.muhatap ||
      entities.muhatap
    );


  /* ========================================
     BODY
  ======================================== */

  let body =
    textValue(
      officialWriting.body
    );


  /*
    Eğer muhatap body içinde
    "dikkatine" olarak geldiyse ayır.
  */

  if (
    !recipient &&
    body
  ) {

    const paragraphs =
      body
        .split(/\n\s*\n/)
        .map(
          item =>
            item.trim()
        )
        .filter(Boolean);


    if (
      paragraphs.length > 0 &&
      /\bdikkatine[;:.]?\s*$/i.test(
        paragraphs[0]
      )
    ) {

      recipient =
        paragraphs[0]
          .replace(
            /[;:.]\s*$/,
            ""
          )
          .trim();


      body =
        paragraphs
          .slice(1)
          .join("\n\n")
          .trim();
    }
  }


  /* ========================================
     ROUTING
  ======================================== */

  const selectedDepartment =
    textValue(
      routing.selected_department ||
      routing.recommended_unit
    );


  /* ========================================
     TYPE
  ======================================== */

  const typeLabels = {

    cevap_yazisi:
      "Cevap Yazısı",

    talep_yazisi:
      "Talep Yazısı",

    bilgilendirme_yazisi:
      "Bilgilendirme Yazısı",

    basvuru_cevabi:
      "Başvuru Cevabı"

  };


  const typeText =
    typeLabels[
      officialWriting.type
    ] ||
    officialWriting.type ||
    "Belirtilmedi";


  /* ========================================
     CONFIDENCE
  ======================================== */

  const confidence =
    officialWriting.confidence != null

      ? `%${Math.round(
          officialWriting.confidence *
          100
        )}`

      : "-";


  /* ========================================
     PREVIEW
  ======================================== */

  openModal(
    subject,
    "RESMİ YAZI",
    `
      <div
        style="
          max-width:760px;
          margin:auto;
        "
      >

        <!-- BAŞLIK -->

        <div
          style="
            text-align:center;
            font-weight:700;
            font-size:16px;
            margin-bottom:30px;
          "
        >
          RESMÎ YAZI TASLAĞI
        </div>


        <!-- SAYI -->

        ${
          sayi
            ? `
              <div
                style="
                  margin-bottom:10px;
                "
              >
                <strong>Sayı:</strong>
                ${escapeHtml(sayi)}
              </div>
            `
            : ""
        }


        <!-- TARİH -->

        ${
          tarih
            ? `
              <div
                style="
                  margin-bottom:10px;
                "
              >
                <strong>Tarih:</strong>
                ${escapeHtml(tarih)}
              </div>
            `
            : ""
        }


        <!-- KONU -->

        <div
          style="
            margin-bottom:10px;
          "
        >
          <strong>Konu:</strong>

          ${escapeHtml(subject)}
        </div>


        <!-- MUHATAP -->

        ${
          recipient
            ? `
              <div
                style="
                  margin-top:34px;
                  margin-bottom:30px;
                  text-align:center;
                "
              >

                <div
                  style="
                    font-size:12px;
                    color:#8fa9c2;
                    margin-bottom:7px;
                    font-weight:700;
                  "
                >
                  MUHATAP
                </div>


                <div
                  style="
                    font-weight:700;
                    font-size:15px;
                    line-height:1.5;
                  "
                >
                  ${escapeHtml(recipient)}
                </div>

              </div>
            `
            : ""
        }


        <!-- BODY -->

        <div
          style="
            white-space:pre-wrap;
            line-height:1.85;
            margin-top:30px;
          "
        >
          ${escapeHtml(body)}
        </div>


        <!-- META -->

        <div
          style="
            border-top:
              1px solid rgba(
                255,
                255,
                255,
                .12
              );

            margin-top:38px;

            padding-top:18px;

            color:#8fa9c2;

            font-size:12px;
          "
        >

          <div>

            <strong>
              Yazı Türü:
            </strong>

            ${escapeHtml(typeText)}

          </div>


          ${
            selectedDepartment
              ? `
                <div
                  style="
                    margin-top:6px;
                  "
                >

                  <strong>
                    Yönlendirilen Birim:
                  </strong>

                  ${escapeHtml(
                    selectedDepartment
                  )}

                </div>
              `
              : ""
          }


          <div
            style="
              margin-top:6px;
            "
          >

            <strong>
              Güven:
            </strong>

            ${escapeHtml(confidence)}

          </div>

        </div>


        <!-- BUTTONS -->

        <div
          style="
            margin-top:26px;
            display:flex;
            gap:10px;
            justify-content:flex-end;
            flex-wrap:wrap;
          "
        >


          <button
            id="editOfficialWritingBtn"
            class="action-btn"
            type="button"
          >
            Yeniden Oluştur
          </button>


          <button
            id="downloadOfficialPdfBtn"
            class="action-btn primary"
            type="button"
          >
            PDF Olarak İndir
          </button>


        </div>

      </div>
    `
  );


  /* ========================================
     PDF
  ======================================== */

  const pdfButton =
    document.getElementById(
      "downloadOfficialPdfBtn"
    );


  if (pdfButton) {

    pdfButton.onclick =
      () => {

        downloadOfficialWritingPdf({

          subject:
            subject,

          sayi:
            sayi,

          tarih:
            tarih,

          recipient:
            recipient,

          body:
            body,

          typeText:
            typeText

        });

      };
  }


  /* ========================================
     YENIDEN OLUŞTUR
  ======================================== */

  const editButton =
    document.getElementById(
      "editOfficialWritingBtn"
    );


  if (editButton) {

    editButton.onclick =
      () => {

        openOfficialWriting(
          message
        );

      };
  }
}

/* ========================================
   DOWNLOAD RESMI YAZI PDF
======================================== */
function downloadOfficialWritingPdf(
  data
) {

  const {
    subject,
    sayi,
    tarih,
    recipient,
    body,
    typeText
  } = data;


  if (
    typeof html2pdf ===
    "undefined"
  ) {

    alert(
      "PDF kütüphanesi yüklenemedi."
    );

    return;
  }


  const pdfContent =
    document.createElement(
      "div"
    );


  pdfContent.innerHTML = `

    <div
      style="
        box-sizing:border-box;
        width:190mm;
        padding:
          14mm
          16mm
          16mm
          16mm;

        background:#ffffff;
        color:#111111;

        font-family:
          Arial,
          Helvetica,
          sans-serif;

        font-size:11pt;
        line-height:1.7;
      "
    >


      <!-- BAŞLIK -->

      <div
        style="
          text-align:center;
          font-size:14pt;
          font-weight:700;
          margin-bottom:28px;
        "
      >
        RESMÎ YAZI TASLAĞI
      </div>


      <!-- SAYI + TARİH -->

      ${
        sayi || tarih
          ? `
            <div
              style="
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                margin-bottom:12px;
              "
            >

              <div>
                ${
                  sayi
                    ? `
                      <strong>Sayı:</strong>
                      ${escapeHtml(sayi)}
                    `
                    : ""
                }
              </div>


              <div
                style="
                  text-align:right;
                "
              >
                ${
                  tarih
                    ? escapeHtml(tarih)
                    : ""
                }
              </div>

            </div>
          `
          : ""
      }


      <!-- KONU -->

      <div
        style="
          margin-top:8px;
          margin-bottom:28px;
        "
      >

        <strong>
          Konu:
        </strong>

        ${escapeHtml(
          subject
        )}

      </div>


      <!-- MUHATAP -->

      ${
        recipient
          ? `
            <div
              style="
                text-align:center;
                font-weight:700;
                font-size:11.5pt;
                line-height:1.5;

                margin:
                  34px
                  20px
                  32px
                  20px;
              "
            >

              ${escapeHtml(
                recipient
              )}

            </div>
          `
          : ""
      }


      <!-- METİN -->

      <div
        style="
          white-space:pre-wrap;
          text-align:justify;
          line-height:1.8;
          margin-top:20px;
        "
      >

        ${escapeHtml(
          body
        )}

      </div>


      <!-- ALT BİLGİ -->

      <div
        style="
          margin-top:46px;
          padding-top:10px;

          border-top:
            1px solid #dddddd;

          font-size:8.5pt;
          color:#666666;
        "
      >

        Bu belge BİLTEK tarafından
        oluşturulmuş bir resmî yazı
        taslağıdır.

        ${
          typeText
            ? `
              <span>
                • Yazı Türü:
                ${escapeHtml(
                  typeText
                )}
              </span>
            `
            : ""
        }

      </div>


    </div>
  `;


  const safeName =
    (
      subject ||
      "resmi-yazi"
    )

      .replace(
        /[\\/:*?"<>|]/g,
        ""
      )

      .trim()

      .slice(
        0,
        60
      );


  const options = {

    margin:
      10,

    filename:
      `${safeName || "resmi-yazi"}.pdf`,

    image: {

      type:
        "jpeg",

      quality:
        0.98

    },

    html2canvas: {

      scale:
        2,

      useCORS:
        true,

      backgroundColor:
        "#ffffff"

    },

    jsPDF: {

      unit:
        "mm",

      format:
        "a4",

      orientation:
        "portrait"

    }

  };


  html2pdf()

    .set(
      options
    )

    .from(
      pdfContent
    )

    .save();
}
/* ========================================
   EXPERT TECHNICAL DETAILS
======================================== */

function openDetails(
  raw
) {

  const sections = [

    [
      "Belge Analizi",
      raw.evrak_analysis
    ],

    [
      "Sınıflandırma",
      raw.classification
    ],

    [
      "Mevzuat",
      raw.rag
    ],

    [
      "Yönlendirme",
      raw.routing
    ],

    [
      "Doğrulama",
      raw.validation
    ],

    [
      "Performans",
      raw.timing
    ]

  ].filter(
    ([name, value]) =>
      value
  );


  const html =
    sections
      .map(
        ([name, value]) => `

          <div class="source-item">

            <strong>
              ${escapeHtml(name)}
            </strong>

            <pre
              style="
                white-space:pre-wrap;
                color:#bcd0e3;
                font-size:12px;
                overflow:auto;
              "
            >${escapeHtml(
              JSON.stringify(
                value,
                null,
                2
              )
            )}</pre>

          </div>
        `
      )
      .join("");


  openModal(

    "Teknik Detaylar",

    "UZMAN MODU",

    html ||

    `
      <p>
        Teknik detay bulunamadı.
      </p>
    `
  );
}


/* ========================================
   INITIALIZE
======================================== */

renderHistory();

updateModeUI();