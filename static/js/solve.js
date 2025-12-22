(function () {
  function $id(id) {
    return document.getElementById(id);
  }

  const base = window.location.origin;

  function renderBitplanes(planes) {
    let html = "<h6 class='mt-4'>Bitplane Visualization</h6>";

    for (const ch of ["R", "G", "B"]) {
      html += `
        <div class="mb-3">
          <strong>${ch} Channel</strong>
          <div style="display:grid;grid-template-columns:repeat(8,1fr);gap:8px">
      `;

      for (let bit = 0; bit < 8; bit++) {
        const img = planes[ch][`bit_${bit}`];
        html += `
          <div style="text-align:center;font-size:11px">
            <img
              src="data:image/png;base64,${img}"
              style="width:100%;border-radius:4px;
                     border:1px solid rgba(255,255,255,.15);
                     image-rendering:pixelated"
            />
            <div>Bit ${bit}</div>
          </div>
        `;
      }

      html += "</div></div>";
    }

    $id("result-analyzers").innerHTML += html;
  }

  document.addEventListener("DOMContentLoaded", () => {
    const fileInput = $id("file-input");
    const drop = $id("drop-zone");
    const browseBtn = $id("browse-btn");
    const modeSelect = $id("mode");
    const payloadArea = $id("payload-area");
    const payloadInput = $id("payload");
    const form = $id("upload-form");
    const submitBtn = $id("submit-btn");
    const resultInfos = $id("result-infos");
    const resultAnalyzers = $id("result-analyzers");
    const uploadStatus = $id("upload-status");

    let savedFilename = null;

    function clearResults() {
      resultInfos.innerHTML = "";
      resultAnalyzers.innerHTML = "";
    }

    function pretty(obj) {
      return `<pre style="white-space:pre-wrap">${JSON.stringify(obj, null, 2)}</pre>`;
    }

    async function autoUploadFile(file) {
      const fd = new FormData();
      fd.append("file", file);

      const res = await fetch(base + "/upload", {
        method: "POST",
        body: fd
      });

      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Upload failed");

      savedFilename = json.filename;
      uploadStatus.innerHTML =
        `<span style="color:#6bff8a;font-weight:600;">✔ File uploaded: ${savedFilename}</span>`;
    }

    browseBtn.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;
      $id("drag-msg").textContent = file.name;
      await autoUploadFile(file);
    });

    drop.addEventListener("dragover", e => {
      e.preventDefault();
      drop.classList.add("border-primary");
    });

    drop.addEventListener("dragleave", () => {
      drop.classList.remove("border-primary");
    });

    drop.addEventListener("drop", async e => {
      e.preventDefault();
      drop.classList.remove("border-primary");
      const file = e.dataTransfer.files[0];
      if (!file) return;
      fileInput.files = e.dataTransfer.files;
      $id("drag-msg").textContent = file.name;
      await autoUploadFile(file);
    });

    modeSelect.addEventListener("change", () => {
      payloadArea.classList.toggle("d-none", modeSelect.value !== "embed");
    });

    async function handleSubmit(e) {
      e.preventDefault();
      clearResults();

      if (!savedFilename) {
        alert("Please upload a file first.");
        return;
      }

      const mode = modeSelect.value;
      const password = $id("password").value.trim();

      if (mode === "analyze") {
        const fd = new FormData();
        fd.append("filename", savedFilename);

        const res = await fetch(base + "/analyze", {
          method: "POST",
          body: fd
        });

        if (!res.ok) {
          const err = await res.json().catch(() => null);
          throw new Error(err?.error || "Analyze failed");
        }

        const json = await res.json();

        resultInfos.classList.add("fade-in");
        resultInfos.innerHTML = pretty({
          server_saved_filename: savedFilename,
          basic: {
            mime: json.mime,
            size: json.size,
            type: json.type || "unknown"
          }
        });

        if (json.plugins) {
          const pluginsCopy = { ...json.plugins };
          delete pluginsCopy.image_bitplane_visualizer;

          if (Object.keys(pluginsCopy).length > 0) {
            resultAnalyzers.innerHTML += `
              <h6 class="mt-3">Analyzer Output</h6>
              ${pretty(pluginsCopy)}
            `;
          }
        }

        const bitplane = json.plugins?.image_bitplane_visualizer;
        if (bitplane?.planes) {
          renderBitplanes(bitplane.planes);
        }

        return;
      }

      if (mode === "embed") {
        const payloadFile = payloadInput.files[0];
        if (!payloadFile) {
          alert("Please select a payload file.");
          return;
        }

        const fd = new FormData();
        fd.append("filename", savedFilename);
        fd.append("password", password);
        fd.append("payload", payloadFile);

        const res = await fetch(base + "/embed", {
          method: "POST",
          body: fd
        });

        const json = await res.json().catch(() => null);
        if (!res.ok) throw new Error(json?.error || "Embed failed");

        resultInfos.classList.add("fade-in");
        resultInfos.innerHTML = `
          <h6 class="mb-2">Embedding Successful</h6>
          <ul class="small">
            <li><strong>Output file:</strong> ${json.outfile}</li>
            <li><strong>Payload size:</strong> ${json.info?.payload_bytes ?? "?"} bytes</li>
            <li><strong>Bits written:</strong> ${json.info?.bits_written ?? "?"}</li>
          </ul>
        `;

        if (json.outfile) {
          const link = document.createElement("a");
          link.href = `/uploads/${encodeURIComponent(json.outfile)}`;
          link.download = json.outfile;
          link.textContent = "Download embedded file";
          link.className = "btn btn-sm btn-outline-light mt-2";
          resultInfos.appendChild(link);
        }

        return;
      }

      if (mode === "extract") {
        const fd = new FormData();
        fd.append("filename", savedFilename);
        fd.append("password", password);

        const res = await fetch(base + "/extract", {
          method: "POST",
          body: fd
        });

        if (!res.ok) {
          const err = await res.json().catch(() => null);
          throw new Error(err?.error || "Extract failed");
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "extracted_payload";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }
    }

    form.addEventListener("submit", handleSubmit);
    submitBtn.addEventListener("click", handleSubmit);
  });
})();
