const API_URL = "http://127.0.0.1:8000/dashboard";
let currentLastProcess = null;

function percent(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "-";
    }

    return `${Math.round(value * 100)}%`;
}


function valueOrDash(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "-";
    }

    return value;
}


function validationBadge(status) {

    const normalized = (
        status || ""
    ).toLowerCase();

    if (normalized === "passed") {

        return `
            <span class="badge success">
                Geçerli
            </span>
        `;
    }

    if (normalized === "invalid") {

        return `
            <span class="badge invalid">
                Geçersiz
            </span>
        `;
    }

    if (normalized === "warning") {

        return `
            <span class="badge warning">
                Uyarı
            </span>
        `;
    }

    return `
        <span class="badge neutral">
            -
        </span>
    `;
}

function renderAgentPipeline(last) {

    const empty =
        document.getElementById(
            "pipelineEmpty"
        );

    const pipeline =
        document.getElementById(
            "agentPipeline"
        );

    const pipelineStatus =
        document.getElementById(
            "pipelineStatus"
        );


    if (!last) {

        empty.classList.remove(
            "hidden"
        );

        pipeline.classList.add(
            "hidden"
        );

        pipelineStatus.className =
            "badge neutral";

        pipelineStatus.textContent =
            "Bekleniyor";

        return;
    }


    empty.classList.add(
        "hidden"
    );

    pipeline.classList.remove(
        "hidden"
    );


    // ==================================
    // CLASSIFICATION
    // ==================================

    const classConfidence =
        last.classification_confidence;


    const classState =
        document.getElementById(
            "classificationAgentState"
        );


    document.getElementById(
        "classificationAgentDetail"
    ).textContent =

        `${valueOrDash(last.classification)} · ${
            percent(classConfidence)
        } güven`;


    if (
        classConfidence !== null &&
        classConfidence !== undefined &&
        classConfidence < 0.70
    ) {

        classState.className =
            "agent-state warning-state";

        classState.textContent =
            "Düşük Güven";

    } else {

        classState.className =
            "agent-state success-state";

        classState.textContent =
            "Tamamlandı";
    }


    // ==================================
    // EVRAK ANALIZ
    // ==================================

    const analysisConfidence =
        last.analysis_confidence;


    const analysisState =
        document.getElementById(
            "analysisAgentState"
        );


    document.getElementById(
        "analysisAgentDetail"
    ).textContent =

        `${
            percent(
                analysisConfidence
            )
        } analiz güveni`;


    if (
        analysisConfidence !== null &&
        analysisConfidence !== undefined &&
        analysisConfidence < 0.70
    ) {

        analysisState.className =
            "agent-state warning-state";

        analysisState.textContent =
            "Düşük Güven";

    } else {

        analysisState.className =
            "agent-state success-state";

        analysisState.textContent =
            "Tamamlandı";
    }


    // ==================================
    // RAG
    // ==================================

    const ragSources =
        last.rag_sources ?? 0;


    const ragState =
        document.getElementById(
            "ragAgentState"
        );


    document.getElementById(
        "ragAgentDetail"
    ).textContent =
        `${ragSources} mevzuat kaynağı bulundu`;


    if (ragSources > 0) {

        ragState.className =
            "agent-state success-state";

        ragState.textContent =
            "Tamamlandı";

    } else {

        ragState.className =
            "agent-state warning-state";

        ragState.textContent =
            "Kaynak Yok";
    }


    // ==================================
    // ROUTING
    // ==================================

    const routing =
        last.routing;


    const routingState =
        document.getElementById(
            "routingAgentState"
        );


    document.getElementById(
        "routingAgentDetail"
    ).textContent =
        valueOrDash(
            routing
        );


    if (routing) {

        routingState.className =
            "agent-state success-state";

        routingState.textContent =
            "Yönlendirildi";

    } else {

        routingState.className =
            "agent-state warning-state";

        routingState.textContent =
            "Birim Yok";
    }


    // ==================================
    // VALIDATION
    // ==================================

    const validationStatus =
        (
            last.validation_status ||
            ""
        ).toLowerCase();


    const issueCount =
        last.issue_count ?? 0;


    const validationState =
        document.getElementById(
            "validationAgentState"
        );


    document.getElementById(
        "validationAgentDetail"
    ).textContent =
        `${issueCount} doğrulama sorunu`;


    if (
        validationStatus === "passed"
    ) {

        validationState.className =
            "agent-state success-state";

        validationState.textContent =
            "Geçerli";

    } else if (
        validationStatus === "invalid"
    ) {

        validationState.className =
            "agent-state error-state";

        validationState.textContent =
            "Geçersiz";

    } else {

        validationState.className =
            "agent-state warning-state";

        validationState.textContent =
            "Kontrol";
    }


    // ==================================
    // PIPELINE GENERAL STATUS
    // ==================================

    if (
        validationStatus === "invalid"
    ) {

        pipelineStatus.className =
            "badge invalid";

        pipelineStatus.textContent =
            "Kontrol Gerekli";

    } else {

        pipelineStatus.className =
            "badge success";

        pipelineStatus.textContent =
            "Tamamlandı";
    }
}
function openValidationDetails() {

    if (!currentLastProcess) {
        return;
    }

    const modal =
        document.getElementById(
            "validationModal"
        );

    const issues =
        currentLastProcess.validation_issues || [];

    const status =
        currentLastProcess.validation_status || "-";

    document.getElementById(
        "modalValidationStatus"
    ).textContent = status;

    document.getElementById(
        "modalIssueCount"
    ).textContent = issues.length;

    const list =
        document.getElementById(
            "validationIssuesList"
        );

    if (issues.length === 0) {

        list.innerHTML = `
            <div class="empty">
                Doğrulama sorunu bulunamadı.
            </div>
        `;

    } else {

        list.innerHTML =
            issues.map(
                (issue, index) => {

                    const type =
                        issue.type ||
                        issue.code ||
                        "VALIDATION_ERROR";

                    const field =
                        issue.field ||
                        "-";

                    const severity =
                        (
                            issue.severity ||
                            "medium"
                        ).toLowerCase();

                    const message =
                        issue.message ||
                        "Detay bulunamadı.";

                    return `
                        <div class="validation-issue">

                            <div class="validation-issue-header">

                                <div class="validation-issue-title">
                                    ${index + 1}. ${type}
                                </div>

                                <span
                                    class="issue-severity ${severity}"
                                >
                                    ${severity.toUpperCase()}
                                </span>

                            </div>

                            <div class="validation-issue-meta">
                                <span>
                                    Alan:
                                    <strong>${field}</strong>
                                </span>
                            </div>

                            <div class="validation-issue-message">
                                ${message}
                            </div>

                        </div>
                    `;
                }
            ).join("");
    }

    modal.classList.remove(
        "hidden"
    );
}


function closeValidationDetails() {

    document.getElementById(
        "validationModal"
    ).classList.add(
        "hidden"
    );
}
function openRagDetails() {

    if (!currentLastProcess) {
        return;
    }

    const rag =
        currentLastProcess.rag_details || {};

    const sources =
        rag.sources || [];


    document.getElementById(
        "ragQuery"
    ).textContent =
        valueOrDash(
            rag.query
        );


    document.getElementById(
        "ragAnswer"
    ).textContent =
        valueOrDash(
            rag.answer
        );


    document.getElementById(
        "ragSourceCount"
    ).textContent =
        sources.length;


    const sourcesList =
        document.getElementById(
            "ragSourcesList"
        );


    if (sources.length === 0) {

        sourcesList.innerHTML = `
            <div class="empty">
                Kaynak bulunamadı.
            </div>
        `;

    } else {

        sourcesList.innerHTML =
            sources.map(
                (source, index) => {

                    const title =
                        source.title ||
                        source.source ||
                        source.document ||
                        source.law_name ||
                        `Kaynak ${index + 1}`;


                    const article =
                        source.article ||
                        source.madde ||
                        source.article_number ||
                        "-";


                    const score =
                        source.score ??
                        source.rerank_score ??
                        source.similarity_score ??
                        null;


                    const content =
                        source.content ||
                        source.text ||
                        source.chunk ||
                        source.page_content ||
                        "Kaynak metni bulunamadı.";


                    let scoreText = "-";

                    if (
                        score !== null &&
                        score !== undefined
                    ) {

                        if (
                            typeof score === "number"
                        ) {
                            scoreText =
                                score.toFixed(3);
                        } else {
                            scoreText =
                                score;
                        }
                    }


                    return `
                        <div class="rag-source">

                            <div class="rag-source-header">

                                <div class="rag-source-title">
                                    ${index + 1}. ${title}
                                </div>

                                <span class="rag-source-score">
                                    ${scoreText}
                                </span>

                            </div>


                            <div class="rag-source-meta">

                                <span>
                                    Madde:
                                    <strong>${article}</strong>
                                </span>

                            </div>


                            <div class="rag-source-content">
                                ${content}
                            </div>

                        </div>
                    `;
                }
            ).join("");
    }


    document.getElementById(
        "ragModal"
    ).classList.remove(
        "hidden"
    );
}


function closeRagDetails() {

    document.getElementById(
        "ragModal"
    ).classList.add(
        "hidden"
    );
}
async function loadDashboard() {

    try {

        const response = await fetch(
            API_URL
        );

        if (!response.ok) {
            throw new Error(
                "Dashboard API error"
            );
        }

        const data = await response.json();


        // ===============================
        // SUMMARY
        // ===============================

        const summary =
            data.summary || {};


        document.getElementById(
            "totalRequests"
        ).textContent =
            summary.total_requests ?? 0;


        document.getElementById(
            "successful"
        ).textContent =
            summary.successful ?? 0;


        document.getElementById(
            "invalid"
        ).textContent =
            summary.invalid ?? 0;


        document.getElementById(
            "averageTime"
        ).textContent =
            `${summary.average_processing_time ?? 0} sn`;


        // ===============================
        // LAST PROCESS
        // ===============================

        const last =
    data.last_process;

currentLastProcess =
    last;

renderAgentPipeline(
    last
);



const emptyProcess =
    document.getElementById(
        "emptyProcess"
    );


        const processDetails =
            document.getElementById(
                "processDetails"
            );


        const lastStatus =
            document.getElementById(
                "lastStatus"
            );


        if (!last) {

            emptyProcess.classList.remove(
                "hidden"
            );

            processDetails.classList.add(
                "hidden"
            );

            lastStatus.className =
                "badge neutral";

            lastStatus.textContent =
                "Bekleniyor";

        } else {

            emptyProcess.classList.add(
                "hidden"
            );

            processDetails.classList.remove(
                "hidden"
            );


            document.getElementById(
                "fileName"
            ).textContent =
                valueOrDash(
                    last.file_name
                );


            document.getElementById(
                "requestType"
            ).textContent =
                last.request_type === "document"
                    ? "Belge"
                    : "Soru";


            document.getElementById(
                "classification"
            ).textContent =
                valueOrDash(
                    last.classification
                );


            document.getElementById(
                "classificationConfidence"
            ).textContent =
                percent(
                    last.classification_confidence
                );


            document.getElementById(
                "analysisConfidence"
            ).textContent =
                percent(
                    last.analysis_confidence
                );


            document.getElementById(
                "routing"
            ).textContent =
                valueOrDash(
                    last.routing
                );


            document.getElementById(
                "ragSources"
            ).textContent =
                last.rag_sources ?? 0;


            document.getElementById(
                "issueCount"
            ).textContent =
                last.issue_count ?? 0;


            const status =
                (
                    last.validation_status ||
                    ""
                ).toLowerCase();


            if (status === "passed") {

                lastStatus.className =
                    "badge success";

                lastStatus.textContent =
                    "Geçerli";

            } else if (
                status === "invalid"
            ) {

                lastStatus.className =
                    "badge invalid";

                lastStatus.textContent =
                    "Geçersiz";

            } else if (
                status === "warning"
            ) {

                lastStatus.className =
                    "badge warning";

                lastStatus.textContent =
                    "Uyarı";

            } else {

                lastStatus.className =
                    "badge neutral";

                lastStatus.textContent =
                    "Tamamlandı";
            }
        }


        // ===============================
        // HISTORY
        // ===============================

        const history =
            data.recent_processes || [];


        const tbody =
            document.getElementById(
                "historyBody"
            );


        if (history.length === 0) {

            tbody.innerHTML = `
                <tr>
                    <td
                        colspan="6"
                        class="table-empty"
                    >
                        Henüz veri yok.
                    </td>
                </tr>
            `;

            return;
        }


        tbody.innerHTML =
            history.map(
                item => `
                    <tr>

                        <td>
                            ${
                                valueOrDash(
                                    item.file_name
                                )
                            }
                        </td>

                        <td>
                            ${
                                item.request_type === "document"
                                    ? "Belge"
                                    : "Soru"
                            }
                        </td>

                        <td>
                            ${
                                valueOrDash(
                                    item.classification
                                )
                            }
                        </td>

                        <td>
                            ${
                                valueOrDash(
                                    item.routing
                                )
                            }
                        </td>

                        <td>
                            ${
                                validationBadge(
                                    item.validation_status
                                )
                            }
                        </td>

                        <td>
                            ${
                                item.issue_count ?? 0
                            }
                        </td>

                    </tr>
                `
            ).join("");

    }

    catch (error) {

        console.error(
            "Dashboard yüklenemedi:",
            error
        );
    }
}

document.getElementById(
    "validationAgentCard"
).addEventListener(
    "click",
    openValidationDetails
);


document.getElementById(
    "closeValidationModal"
).addEventListener(
    "click",
    closeValidationDetails
);


document.querySelector(
    "#validationModal .modal-backdrop"
).addEventListener(
    "click",
    closeValidationDetails
);
document.getElementById(
    "ragAgentCard"
).addEventListener(
    "click",
    openRagDetails
);


document.getElementById(
    "closeRagModal"
).addEventListener(
    "click",
    closeRagDetails
);


document.querySelector(
    "#ragModal .modal-backdrop"
).addEventListener(
    "click",
    closeRagDetails
);
// İlk yükleme
loadDashboard();


// Her 5 saniyede otomatik güncelle
setInterval(
    loadDashboard,
    5000
);