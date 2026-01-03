(function () {
  function $id(id) {
    return document.getElementById(id);
  }

  const base = window.location.origin;

  /* ================= VISUAL RENDERERS ================= */

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
            <img src="data:image/png;base64,${img}"
                 style="width:100%;border-radius:4px;
                        border:1px solid rgba(255,255,255,.15);
                        image-rendering:pixelated"/>
            <div>Bit ${bit}</div>
          </div>`;
      }

      html += "</div></div>";
    }

    $id("result-analyzers").insertAdjacentHTML("beforeend", html);
  }

  function renderSuperimposed(planes) {
   let html = `
     <div class="mb-3">
       <strong>Superimposed RGB</strong>
       <div style="display:grid;grid-template-columns:repeat(8,1fr);gap:8px">
   `;

   for (let bit = 0; bit < 8; bit++) {
     const img = planes[`bit_${bit}`];
     html += `
        <div style="text-align:center;font-size:11px">
          <img
            src="data:image/png;base64,${img}"
            style="width:100%;
                   border-radius:4px;
                   border:1px solid rgba(255,255,255,.15);
                   image-rendering:pixelated"/>
          <div>Bit ${bit}</div>
        </div>
     `;
   }

   html += "</div></div>";

    $id("result-analyzers").insertAdjacentHTML("beforeend", html);
  }
  function renderSuspicionBar(score) {
    const clamped = Math.max(0, Math.min(1, score));
    const pct = clamped * 100;

    const html = `
      <div class="mt-4">
        <h6>Suspiciousness Indicator</h6>
        <div style="position:relative;height:12px;border-radius:6px;
                    background:linear-gradient(90deg,#2ecc71,#f1c40f,#e74c3c);">
          <div style="position:absolute;left:${pct}%;
                      top:-4px;transform:translateX(-50%);
                      width:14px;height:14px;border-radius:50%;
                      background:#fff;border:2px solid #000"></div>
        </div>
        <div class="small text-muted mt-1">Score: ${score.toFixed(4)}</div>
      </div>`;
    $id("result-analyzers").insertAdjacentHTML("beforeend", html);
  }

  /* ================= MAIN ================= */

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

      const res = await fetch(base + "/upload", { method: "POST", body: fd });
      const json = await res.json();

      if (!res.ok) throw new Error(json.error || "Upload failed");

      savedFilename = json.filename;
      uploadStatus.innerHTML =
        `<span style="color:#6bff8a;font-weight:600;">✔ File uploaded: ${savedFilename}</span>`;
    }

    browseBtn.onclick = () => fileInput.click();

    fileInput.onchange = async () => {
      const f = fileInput.files[0];
      if (!f) return;
      $id("drag-msg").textContent = f.name;
      await autoUploadFile(f);
    };

    drop.ondragover = e => { e.preventDefault(); drop.classList.add("border-primary"); };
    drop.ondragleave = () => drop.classList.remove("border-primary");

    drop.ondrop = async e => {
      e.preventDefault();
      drop.classList.remove("border-primary");
      const f = e.dataTransfer.files[0];
      if (!f) return;
      fileInput.files = e.dataTransfer.files;
      $id("drag-msg").textContent = f.name;
      await autoUploadFile(f);
    };

    modeSelect.onchange = () =>
      payloadArea.classList.toggle("d-none", modeSelect.value !== "embed");

    async function handleSubmit(e) {
      e.preventDefault();
      clearResults();

      if (!savedFilename) return alert("Upload a file first.");

      const mode = modeSelect.value;
      const password = $id("password").value.trim();

      /* ---------- ANALYZE ---------- */
      if (mode === "analyze") {
        const fd = new FormData();
        fd.append("filename", savedFilename);

        const res = await fetch(base + "/analyze", { method: "POST", body: fd });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "Analyze failed");

        resultInfos.innerHTML = pretty({
          filename: savedFilename,
          mime: json.mime,
          size: json.size
        });

        const plugins = structuredClone(json.plugins || {});

        if (plugins.image_bitplane_visualizer)
          delete plugins.image_bitplane_visualizer.planes;

        if (plugins.image_bitplane_superimposed)
          delete plugins.image_bitplane_superimposed.planes;

        if (Object.keys(plugins).length) {
          resultAnalyzers.insertAdjacentHTML(
            "beforeend",
            `<h6 class="mt-3">Analyzer Output</h6>${pretty(plugins)}`
          );
        }

        const adv = json.plugins?.image_lsb_advanced;
        if (adv?.suspiciousness_score !== undefined)
          renderSuspicionBar(adv.suspiciousness_score);

        const bit = json.plugins?.image_bitplane_visualizer;
        if (bit?.planes) renderBitplanes(bit.planes);

        const sup = json.plugins?.image_bitplane_superimposed;
        if (sup?.planes) renderSuperimposed(sup.planes);

        return;
      }

      /* ---------- EMBED ---------- */
      if (mode === "embed") {
        const payloadFile = payloadInput.files[0];
        if (!payloadFile) return alert("Select a payload.");

        const fd = new FormData();
        fd.append("filename", savedFilename);
        fd.append("password", password);
        fd.append("payload", payloadFile);

        const res = await fetch(base + "/embed", { method: "POST", body: fd });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "Embed failed");

        resultInfos.innerHTML = pretty(json);

        if (json.outfile) {
          const a = document.createElement("a");
          a.href = `/uploads/${encodeURIComponent(json.outfile)}`;
          a.download = json.outfile;
          a.textContent = "Download embedded file";
          a.className = "btn btn-sm btn-outline-light mt-2";
          resultInfos.appendChild(a);
        }
        return;
      }

      /* ---------- EXTRACT ---------- */
      if (mode === "extract") {
        const fd = new FormData();
        fd.append("filename", savedFilename);
        fd.append("password", password);

        const res = await fetch(base + "/extract", { method: "POST", body: fd });
        if (!res.ok) throw new Error("Extract failed");

        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "extracted_payload";
        a.click();
        URL.revokeObjectURL(a.href);
      }
    }

    form.onsubmit = handleSubmit;
    submitBtn.onclick = handleSubmit;

    /* ---------- Binary background ---------- */
    (function applyBinaryBackground() {
      function build() {
        const w = window.innerWidth, h = window.innerHeight;
        let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">`;
        for (let y = 0; y < h; y += 16)
          for (let x = 0; x < w; x += 14)
            svg += `<text x="${x}" y="${y}"
              font-size="12" fill="white" fill-opacity="0.12">`
              + (Math.random() > 0.5 ? "1" : "0") + `</text>`;
        svg += "</svg>";

        document.body.style.backgroundImage =
          `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}"),
           linear-gradient(135deg,#072d0f,#0b0f1a)`;
      }
      build();
      window.addEventListener("resize", () => setTimeout(build, 150));
    })();
  });
})();