/* solve.js */

(function () {
  function $id(id) {
    return document.getElementById(id);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const base = window.location.origin;

    const fileInput = $id("file-input");
    const dropZone = $id("drop-zone");
    const browseBtn = $id("browse-btn");
    const modeSelect = $id("mode");
    const payloadArea = $id("payload-area");
    const payloadInput = $id("payload");
    const submitBtn = $id("submit-btn");
    const resultInfos = $id("result-infos");
    const resultAnalyzers = $id("result-analyzers");
    const uploadStatus = $id("upload-status");

    let savedFilename = null;

    /* ---------- helpers ---------- */
    function clearResults() {
      if (resultInfos) resultInfos.innerHTML = "";
      if (resultAnalyzers) resultAnalyzers.innerHTML = "";
    }

    function pretty(obj) {
      return `<pre style="white-space:pre-wrap">${JSON.stringify(obj, null, 2)}</pre>`;
    }

    /* ---------- mode toggle ---------- */
    if (modeSelect && payloadArea) {
      const updateMode = () => {
        payloadArea.classList.toggle("d-none", modeSelect.value !== "embed");
      };
      modeSelect.addEventListener("change", updateMode);
      updateMode();
    }

    /* ---------- browse ---------- */
    if (browseBtn && fileInput) {
      browseBtn.addEventListener("click", () => fileInput.click());
    }

    /* ---------- auto upload ---------- */
    async function autoUpload(file) {
      const fd = new FormData();
      fd.append("file", file);

      const res = await fetch(base + "/upload", {
        method: "POST",
        body: fd
      });

      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Upload failed");

      savedFilename = json.filename;
      if (uploadStatus) {
        uploadStatus.innerHTML =
          `<span style="color:#6bff8a;">✔ File uploaded: ${savedFilename}</span>`;
      }
    }

    /* ---------- file input ---------- */
    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;
      clearResults();
      await autoUpload(file);
    });

    /* ---------- drag & drop ---------- */
    if (dropZone) {
      dropZone.addEventListener("dragover", e => {
        e.preventDefault();
        dropZone.classList.add("border-primary");
      });

      dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("border-primary");
      });

      dropZone.addEventListener("drop", async e => {
        e.preventDefault();
        dropZone.classList.remove("border-primary");
        const file = e.dataTransfer.files[0];
        if (!file) return;
        fileInput.files = e.dataTransfer.files;
        clearResults();
        await autoUpload(file);
      });
    }

    /* ---------- submit ---------- */
    submitBtn.addEventListener("click", async e => {
      e.preventDefault();
      clearResults();

      const mode = modeSelect.value;
      const password = $id("password")?.value || "";
      const file = fileInput.files[0];
      if (!file) return alert("Select a file first.");

      if (!savedFilename) await autoUpload(file);

      try {
        if (mode === "analyze") {
          const fd = new FormData();
          fd.append("filename", savedFilename);

          const res = await fetch(base + "/analyze", { method: "POST", body: fd });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error);

          resultInfos.innerHTML = pretty({
            filename: savedFilename,
            mime: json.mime,
            size: json.size
          });

          delete json.mime;
          delete json.size;
          delete json.filename;

          resultAnalyzers.innerHTML =
            `<h6>Analyzer output</h6>${pretty(json)}`;
          return;
        }

        if (mode === "embed") {
          const payloadFile = payloadInput.files[0];
          if (!payloadFile) return alert("Select a payload file.");

          const fd = new FormData();
          fd.append("filename", savedFilename);
          fd.append("password", password);
          fd.append("payload", payloadFile);

          const res = await fetch(base + "/embed", { method: "POST", body: fd });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error);

          resultInfos.innerHTML = pretty(json);

          const link = document.createElement("a");
          link.href = `/uploads/${encodeURIComponent(json.outfile)}`;
          link.download = json.outfile;
          link.textContent = `Download embedded file`;
          link.className = "btn btn-sm btn-outline-light mt-2";
          resultInfos.appendChild(link);
          return;
        }

        if (mode === "extract") {
          const fd = new FormData();
          fd.append("filename", savedFilename);
          fd.append("password", password);

          const res = await fetch(base + "/extract", { method: "POST", body: fd });
          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error);
          }

          const blob = await res.blob();
          const cd = res.headers.get("content-disposition") || "";
          const match = /filename="?([^"]+)"?/.exec(cd);
          const name = match ? match[1] : "extracted.bin";

          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = name;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(url);

          resultInfos.innerHTML =
            `<div class="text-success">Downloaded ${name}</div>`;
        }
      } catch (err) {
        alert("Error: " + err.message);
      }
    });
  });
})();
