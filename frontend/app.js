const API_URL = "http://127.0.0.1:8000/process";

const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const selectFileBtn = document.getElementById("selectFileBtn");

const selectedFileBox = document.getElementById("selectedFile");
const fileNameElement = document.getElementById("fileName");
const fileSizeElement = document.getElementById("fileSize");
const clearFileBtn = document.getElementById("clearFileBtn");

const questionInput = document.getElementById("questionInput");
const analyzeBtn = document.getElementById("analyzeBtn");

const processingSection = document.getElementById("processingSection");
const processingStep = document.getElementById("processingStep");
const progressBar = document.getElementById("progressBar");

const resultsSection = document.getElementById("resultsSection");
const newAnalysisBtn = document.getElementById("newAnalysisBtn");

let selectedFile = null;
let progressInterval = null;
let progressIndex = 0;

const processingMessages = [
  {
    progress: 12,
    text: "Belge okunuyor..."
  },
  {
    progress: 25,
    text: "OCR işlemi gerçekleştiriliyor..."
  },
  {
    progress: 38,
    text: "Belge türü sınıflandırılıyor..."
  },
  {
    progress: 52,
    text: "Belge içeriği analiz ediliyor..."
  },
  {
    progress: 67,
    text: "İlgili mevzuat araştırılıyor..."
  },
  {
    progress: 79,
    text: "Yönlendirme değerlendiriliyor..."
  },
  {
    progress: 90,
    text: "Doğrulama kontrolleri yapılıyor..."
  },
  {
    progress: 95,
    text: "Sonuç hazırlanıyor..."
  }
];

// دالة تحديث حالة زر التحليل (تفعيله إذا وجد ملف أو كتب سؤال)
function updateButtonState() {
  const hasFile = selectedFile !== null;
  const hasQuestion = questionInput.value.trim().length > 0;
  analyzeBtn.disabled = !(hasFile || hasQuestion);
}

// الاستماع لكتابة السؤال لتحديث حالة الزر
questionInput.addEventListener("input", updateButtonState);

selectFileBtn.addEventListener(
  "click",
  () => fileInput.click()
);

dropZone.addEventListener(
  "click",
  (event) => {
    if (event.target !== selectFileBtn) {
      fileInput.click();
    }
  }
);

fileInput.addEventListener(
  "change",
  () => {
    if (fileInput.files.length > 0) {
      setFile(fileInput.files[0]);
    }
  }
);

dropZone.addEventListener(
  "dragover",
  (event) => {
    event.preventDefault();
    dropZone.classList.add("drag-active");
  }
);

dropZone.addEventListener(
  "dragleave",
  () => {
    dropZone.classList.remove("drag-active");
  }
);

dropZone.addEventListener(
  "drop",
  (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag-active");

    const file = event.dataTransfer.files[0];
    if (file) {
      setFile(file);
    }
  }
);

clearFileBtn.addEventListener(
  "click",
  () => {
    selectedFile = null;
    fileInput.value = "";
    selectedFileBox.classList.add("hidden");
    updateButtonState();
  }
);

function setFile(file) {
  selectedFile = file;

  fileNameElement.textContent = file.name;
  fileSizeElement.textContent = formatFileSize(file.size);

  selectedFileBox.classList.remove("hidden");
  updateButtonState();
}

function formatFileSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

analyzeBtn.addEventListener(
  "click",
  async () => {
    const question = questionInput.value.trim();

    // منع الإرسال فقط إذا كان لا يوجد ملف ولا يوجد سؤال مكتوب
    if (!selectedFile && !question) {
      return;
    }

    startProcessing();

    const formData = new FormData();

    if (selectedFile) {
      formData.append("file", selectedFile);
    }

    if (question) {
      formData.append("question", question);
    }

    try {
      const response = await fetch(
        API_URL,
        {
          method: "POST",
          body: formData
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      finishProcessing();

      renderResults(
        result,
        selectedFile ? selectedFile.name : "Doğrudan Soru"
      );
    } catch (error) {
      finishProcessing();

      alert(
        "İşlem sırasında hata oluştu.\n\n" + error.message
      );

      console.error(error);
    }
  }
);

function startProcessing() {
  resultsSection.classList.add("hidden");
  processingSection.classList.remove("hidden");

  analyzeBtn.disabled = true;
  progressIndex = 0;

  progressBar.style.width = "8%";
  processingStep.textContent = "İşlem başlatılıyor...";

  progressInterval = setInterval(
    () => {
      const item =
        processingMessages[
          progressIndex % processingMessages.length
        ];

      processingStep.textContent = item.text;
      progressBar.style.width = `${item.progress}%`;

      if (progressIndex < processingMessages.length - 1) {
        progressIndex++;
      }
    },
    3500
  );

  processingSection.scrollIntoView({
    behavior: "smooth",
    block: "center"
  });
}

function finishProcessing() {
  if (progressInterval) {
    clearInterval(progressInterval);
  }

  progressBar.style.width = "100%";
  processingStep.textContent = "Analiz tamamlandı.";

  setTimeout(
    () => {
      processingSection.classList.add("hidden");
    },
    450
  );
}

function renderResults(data, originalFileName) {
  const classification = data.classification || {};
  const analysis = data.evrak_analysis || {};
  const routing = data.routing || {};
  const rag = data.rag || {};
  const validation = data.validation || {};
  const documentInfo = data.document_info || {};
  const ocr = data.ocr || {};
  const timing = data.timing || {};

  document.getElementById("classificationLabel").textContent =
    formatLabel(classification.label);

  document.getElementById("classificationConfidence").textContent =
    confidenceText(classification.confidence);

  document.getElementById("routingDepartment").textContent =
    routing.selected_department || "—";

  document.getElementById("routingConfidence").textContent =
    confidenceText(routing.confidence);

  document.getElementById("analysisConfidence").textContent =
    percentage(analysis.analysis_confidence);

  document.getElementById("totalTiming").textContent =
    timing.total ? `${timing.total} sn` : "—";

  document.getElementById("documentSummary").textContent =
    analysis.summary || "—";

  document.getElementById("documentTopic").textContent =
    analysis.topic || "—";

  document.getElementById("documentPurpose").textContent =
    analysis.purpose || "—";

  document.getElementById("documentIntent").textContent =
    analysis.intent || "—";

  document.getElementById("documentFileName").textContent =
    originalFileName || documentInfo.file_name || "—";

  document.getElementById("documentPageCount").textContent =
    documentInfo.page_count || "—";

  document.getElementById("documentLanguage").textContent =
    (documentInfo.language || "—").toUpperCase();

  document.getElementById("ragAnswer").textContent =
    rag.answer || "İlgili mevzuat sonucu bulunamadı.";

  document.getElementById("ragConfidence").textContent =
    confidenceText(rag.confidence);

  document.getElementById("routingReason").textContent =
    routing.reason || "—";

  document.getElementById("ocrText").textContent =
    ocr.text || "—";

  renderSources(rag.sources || []);
  renderValidation(validation);
  renderTiming(timing);

  resultsSection.classList.remove("hidden");

  setTimeout(
    () => {
      resultsSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    },
    500
  );
}

function renderSources(sources) {
  const container = document.getElementById("sourcesList");
  container.innerHTML = "";

  if (!sources.length) {
    container.innerHTML = `
      <div class="source-chip">
        Kaynak bulunamadı
      </div>
    `;
    return;
  }

  sources.forEach(source => {
    const element = document.createElement("div");
    element.className = "source-chip";

    const law = source.law_number ? `${source.law_number} · ` : "";
    element.textContent = `${law}${source.article || source.title || "Kaynak"}`;

    container.appendChild(element);
  });
}

function renderValidation(validation) {
  const badge = document.getElementById("validationBadge");
  const confidence = document.getElementById("validationConfidence");
  const issuesList = document.getElementById("issuesList");

  badge.className = "validation-badge";

  if (validation.status === "passed") {
    badge.textContent = "✓ Doğrulandı";
    badge.classList.add("success");
  } else {
    badge.textContent = "⚠ İnceleme Gerekli";
    badge.classList.add("invalid");
  }

  confidence.textContent = confidenceText(validation.confidence);

  const issues = validation.issues || [];
  issuesList.innerHTML = "";

  if (!issues.length) {
    issuesList.innerHTML = `
      <div class="empty-state">
        Herhangi bir tutarsızlık tespit edilmedi.
      </div>
    `;
    return;
  }

  issues.forEach(issue => {
    const item = document.createElement("div");
    item.className = "issue";

    const severity = (issue.severity || "low").toLowerCase();

    item.innerHTML = `
      <div class="issue-header">
        <span class="issue-field">
          ${escapeHtml(issue.field || "Kontrol")}
        </span>
        <span class="severity ${severity}">
          ${escapeHtml(severity)}
        </span>
      </div>
      <p>
        ${escapeHtml(issue.message || "Tutarsızlık tespit edildi.")}
      </p>
    `;

    issuesList.appendChild(item);
  });
}

function renderTiming(timing) {
  const timingGrid = document.getElementById("timingGrid");
  timingGrid.innerHTML = "";

  const labels = {
    ocr: "OCR",
    classification: "Sınıflandırma",
    evrak_analysis: "Evrak Analizi",
    rag: "Mevzuat RAG",
    routing: "Yönlendirme",
    official_writing: "Resmi Yazı",
    validation: "Doğrulama",
    total: "Toplam"
  };

  Object.entries(labels).forEach(([key, label]) => {
    if (timing[key] === undefined) {
      return;
    }

    const element = document.createElement("div");
    element.className = "timing-item";

    element.innerHTML = `
      <span>${label}</span>
      <strong>${timing[key]} sn</strong>
    `;

    timingGrid.appendChild(element);
  });
}

function percentage(value) {
  if (value === undefined || value === null) {
    return "—";
  }
  return `%${Math.round(value * 100)}`;
}

function confidenceText(value) {
  if (value === undefined || value === null) {
    return "Güven belirtilmedi";
  }
  return `Güven %${Math.round(value * 100)}`;
}

function formatLabel(label) {
  if (!label) {
    return "—";
  }
  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, char => char.toUpperCase());
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

newAnalysisBtn.addEventListener(
  "click",
  () => {
    resultsSection.classList.add("hidden");

    selectedFile = null;
    fileInput.value = "";
    questionInput.value = "";
    selectedFileBox.classList.add("hidden");

    analyzeBtn.disabled = true;

    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  }
);