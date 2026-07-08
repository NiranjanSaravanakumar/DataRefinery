/**
 * DataRefinery — Upload Flow
 * ===========================
 * Handles:
 *  - Drag-and-drop file selection
 *  - File info display + clear
 *  - XHR upload with progress tracking
 *  - POST /clean pipeline trigger
 *  - Redirect to result page on success
 *  - Error display
 */

(function () {
  "use strict";

  // ── DOM references ────────────────────────────────────────
  const dropZone       = document.getElementById("drop-zone");
  const fileInput      = document.getElementById("file-input");
  const progressCont   = document.getElementById("progress-container");
  const progressBar    = document.getElementById("progress-bar-fill");
  const progressStatus = document.getElementById("progress-status");
  const progressPct    = document.getElementById("progress-pct");
  const uploadError    = document.getElementById("upload-error");
  const uploadErrorTxt = document.getElementById("upload-error-text");
  const btnClean       = document.getElementById("btn-clean");
  const btnCleanTxt    = document.getElementById("btn-clean-text");
  const dropIcon       = document.getElementById("drop-icon");
  const dropTitle      = document.getElementById("drop-title");
  const dropSub        = document.getElementById("drop-sub");

  // Session state set after a successful /upload response
  let sessionId = null;
  let sessionFilename = null;

  // ── Helpers ───────────────────────────────────────────────
  function formatBytes(bytes) {
    if (bytes < 1024)       return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function showError(message) {
    uploadErrorTxt.textContent = message;
    uploadError.hidden = false;
    progressCont.hidden = true;
    resetButton();
  }

  function hideError() {
    uploadError.hidden = true;
  }

  function resetButton() {
    btnClean.disabled = !sessionId;
    btnClean.setAttribute("aria-disabled", btnClean.disabled ? "true" : "false");
    btnCleanTxt.textContent = "Upload & Clean Data";
  }

  function setProgress(pct, label) {
    progressBar.style.width = pct + "%";
    progressPct.textContent = pct + "%";
    progressStatus.textContent = label;
  }

  // ── File selected / dropped ───────────────────────────────
  function handleFile(file) {
    if (!file) return;

    // Client-side extension guard (server validates properly)
    if (!file.name.toLowerCase().endsWith(".csv")) {
      showError("Invalid file type. Please select a .csv file.");
      return;
    }

    hideError();
    sessionId = null;
    sessionFilename = null;

    // Update drop zone appearance
    dropIcon.textContent = "✅";
    dropTitle.textContent = file.name;
    dropSub.textContent   = formatBytes(file.size);

    btnClean.disabled = false;
    btnClean.setAttribute("aria-disabled", "false");

    // Automatically kick off upload
    uploadFile(file);
  }

  // ── Upload via XHR ────────────────────────────────────────
  function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();

    // Show progress bar
    progressCont.hidden = false;
    setProgress(0, "Uploading…");
    btnClean.disabled = true;
    btnCleanTxt.textContent = "Uploading…";

    // Track upload progress
    xhr.upload.addEventListener("progress", function (evt) {
      if (evt.lengthComputable) {
        const pct = Math.round((evt.loaded / evt.total) * 100);
        setProgress(pct, pct < 100 ? "Uploading…" : "Processing…");
      }
    });

    xhr.addEventListener("load", function () {
      if (xhr.status === 200) {
        let data;
        try { data = JSON.parse(xhr.responseText); } catch (e) {
          showError("Unexpected server response. Please try again.");
          return;
        }
        sessionId = data.session_id;
        sessionFilename = data.filename;

        setProgress(100, "Upload complete ✓");
        btnClean.disabled = false;
        btnClean.setAttribute("aria-disabled", "false");
        btnCleanTxt.textContent = "⚡ Clean Data Now";

      } else {
        let errMsg = "Upload failed. Please try again.";
        try {
          const resp = JSON.parse(xhr.responseText);
          if (resp.error) errMsg = resp.error;
        } catch (_) {}
        showError(errMsg);
      }
    });

    xhr.addEventListener("error", function () {
      showError("Network error during upload. Check your connection and try again.");
    });

    xhr.open("POST", "/upload");
    xhr.send(formData);
  }

  // ── Clean trigger ─────────────────────────────────────────
  btnClean.addEventListener("click", function () {
    if (!sessionId || !sessionFilename) {
      // User clicked without upload completing yet
      showError("Please wait for the file to finish uploading.");
      return;
    }

    hideError();
    btnClean.disabled = true;
    btnCleanTxt.textContent = "Cleaning data…";
    setProgress(100, "Running pipeline…");

    fetch("/clean", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, filename: sessionFilename }),
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data.redirect) {
          // Animate out then redirect
          progressStatus.textContent = "Done! Redirecting…";
          setTimeout(function () {
            window.location.href = data.redirect;
          }, 400);
        } else if (data.error) {
          showError(data.error);
        }
      })
      .catch(function () {
        showError("An error occurred while cleaning the data. Please try again.");
      });
  });

  // ── Clear: click the drop zone to reset ──────────────────────────
  // (Picking a new file via the input naturally replaces the current selection.)

  // ── File input change ─────────────────────────────────────
  fileInput.addEventListener("change", function () {
    if (fileInput.files && fileInput.files[0]) {
      handleFile(fileInput.files[0]);
    }
  });

  // ── Drag & drop ───────────────────────────────────────────
  dropZone.addEventListener("dragover", function (e) {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });

  dropZone.addEventListener("dragleave", function (e) {
    // Only remove class if leaving the drop zone entirely
    if (!dropZone.contains(e.relatedTarget)) {
      dropZone.classList.remove("drag-over");
    }
  });

  dropZone.addEventListener("drop", function (e) {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

})();
