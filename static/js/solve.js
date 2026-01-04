(function () {
  /* ================= UTILITIES ================= */

  // Shorthand helper for document.getElementById
  function $id(id) {
    return document.getElementById(id);
  }

  // Base URL of backend server
  const base = window.location.origin;

  /* ================= VISUAL RENDERERS ================= */

  /**
   * Render per-channel bitplane visualizations (R, G, B)
   * Each channel shows 8 bitplanes (bit 0 = LSB, bit 7 = MSB)
   */
  function renderBitplanes(planes) {
    let html = "<h6 class='mt-4'>Bitplane Visualization</h6>";

    // Iterate over RGB channels
    for (const ch of ["R", "G", "B"]) {
      html += `
        <div class="mb-3">
          <strong>${ch} Channel</strong>
          <div style="display:grid;grid-template-columns:repeat(8,1fr);gap:8px">
      `;

      // Render each bitplane image
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

    // Inject visualization into results section
    $id("result-analyzers").insertAdjacentHTML("beforeend", html);
  }

  /**
   * Render superimposed RGB bitplanes
   * Combines R, G, B bits into a single image per bit index
   */
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

  /**
   * Render a horizontal suspiciousness indicator bar
   * Score range: 0.0 (clean) → 1.0 (highly suspicious)
   */
  function renderSuspicionBar(score, label = "Suspiciousness Indicator") {
    const clamped = Math.max(0, Math.min(1, score));
    const pct = clamped * 100;

    const html = `
      <div class="mt-4">
        <h6>${label}</h6>
        <div class="suspicion-bar">
          <div
            class="suspicion-marker"
            style="left:${pct}%"
          ></div>
        </div>
        <div class="small text-muted mt-1">
          Score: ${score.toFixed(4)} (${pct.toFixed(1)}%)
        </div>
      </div>
    `;

    $id("result-analyzers").insertAdjacentHTML("beforeend", html);
  }
  
  function renderSpectrogram(spec) {
    if (!spec.spectrogram_url) return;

    const html = `
      <div class="mt-4">
        <h6>Audio Spectrogram</h6>

        <img
          src="${spec.spectrogram_url}?t=${Date.now()}"
          style="
            width:100%;
            border-radius:8px;
            background:black;
            border:1px solid rgba(255,255,255,0.15);
          "
          alt="Audio spectrogram"
        />

        <div class="small text-muted mt-1">
          Duration: ${spec.duration_seconds}s ·
          Sample rate: ${spec.sample_rate} Hz ·
          ${spec.log_scale ? "Log scale" : "Linear scale"} ·
          Scroll speed: ${spec.scroll_speed}
        </div>
      </div>
    `;

    document
      .getElementById("result-analyzers")
      .insertAdjacentHTML("beforeend", html);
  }


  /* ================= MAIN APP LOGIC ================= */

  document.addEventListener("DOMContentLoaded", () => {
    // DOM references
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
    const audioControls = $id("audio-controls");


    // Stores filename returned by backend after upload
    let savedFilename = null;

    // Clear previous analysis results
    function clearResults() {
      resultInfos.innerHTML = "";
      resultAnalyzers.innerHTML = "";
      audioControls.classList.add("d-none");
    }

    // Pretty-print JSON output
    function pretty(obj) {
      return `<pre style="white-space:pre-wrap">${JSON.stringify(obj, null, 2)}</pre>`;
    }

    /**
     * Automatically uploads file immediately after selection
     * Required before analyze / embed / extract
     */
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

    // Trigger file picker
    browseBtn.onclick = () => fileInput.click();

    // Handle manual file selection
    fileInput.onchange = async () => {
      const f = fileInput.files[0];
      if (!f) return;
      $id("drag-msg").textContent = f.name;
      await autoUploadFile(f);
    };

    // Drag-and-drop handlers
    drop.ondragover = e => {
      e.preventDefault();
      drop.classList.add("border-primary");
    };

    drop.ondragleave = () =>
      drop.classList.remove("border-primary");

    drop.ondrop = async e => {
      e.preventDefault();
      drop.classList.remove("border-primary");
      const f = e.dataTransfer.files[0];
      if (!f) return;
      fileInput.files = e.dataTransfer.files;
      $id("drag-msg").textContent = f.name;
      await autoUploadFile(f);
    };

    // Show payload input only in embed mode
    modeSelect.onchange = () =>
      payloadArea.classList.toggle("d-none", modeSelect.value !== "embed");

    /**
     * Main submit handler for Analyze / Embed / Extract
     */
    async function handleSubmit(e) {
      e.preventDefault();
      clearResults();

      if (!savedFilename)
        return alert("Upload a file first.");

      const mode = modeSelect.value;
      const password = $id("password").value.trim();

      /* ---------- ANALYZE MODE ---------- */
      if (mode === "analyze") {
        const fd = new FormData();
        fd.append("filename", savedFilename);

        const logScaleEl = document.getElementById("log-scale");
        const scrollSpeedEl = document.getElementById("scroll-speed");

        const logScale = logScaleEl ? logScaleEl.checked : true;
        const scrollSpeed = scrollSpeedEl ? parseInt(scrollSpeedEl.value,10) : 3;

        fd.append("log_scale", logScale ? "1" : "0");
        fd.append("scroll_speed", scrollSpeed.toString());

        const res = await fetch(base + "/analyze", { method: "POST", body: fd });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "Analyze failed");
        // Show audio-only controls if file is audio
        if (json.mime && json.mime.startsWith("audio/")) {
          audioControls.classList.remove("d-none");
        }

        // Basic file metadata
        resultInfos.innerHTML = pretty({
          filename: savedFilename,
          mime: json.mime,
          size: json.size
        });

        // Clone plugin output to avoid mutation
        const plugins = structuredClone(json.plugins || {});

        // Remove large image blobs from JSON display
        if (plugins.image_bitplane_visualizer)
          delete plugins.image_bitplane_visualizer.planes;

        if (plugins.image_bitplane_superimposed)
          delete plugins.image_bitplane_superimposed.planes;

        // Display remaining plugin outputs
        if (Object.keys(plugins).length) {
          resultAnalyzers.insertAdjacentHTML(
            "beforeend",
            `<h6 class="mt-3">Analyzer Output</h6>${pretty(plugins)}`
          );
        }

        // Suspicion score bar
        const scores = [];

        for (const [pluginName, pluginData] of Object.entries(json.plugins || {})) {
          if (
            pluginData &&
            typeof pluginData.suspiciousness_score === "number"
          ) {
            scores.push({
              name: pluginName,
              score: pluginData.suspiciousness_score
            });
          }
        }

        // Render bars (one per plugin)
        for (const s of scores) {
          renderSuspicionBar(s.score, s.name);
        }

        // Bitplane visualizations
        const bit = json.plugins?.image_bitplane_visualizer;
        if (bit?.planes) renderBitplanes(bit.planes);

        const sup = json.plugins?.image_bitplane_superimposed;
        if (sup?.planes) renderSuperimposed(sup.planes);
        
        // Spectrogram visualization
        const spec = json.plugins?.audio_spectrogram_visualizer;
        if (spec?.spectrogram_url) {
          renderSpectrogram(spec);
        }

        return;
      }

      /* ---------- EMBED MODE ---------- */
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

        // Download embedded output
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

      /* ---------- EXTRACT MODE ---------- */
      if (mode === "extract") {
        const fd = new FormData();
        fd.append("filename", savedFilename);
        fd.append("password", password);

        const res = await fetch(base + "/extract", { method: "POST", body: fd });
        if (!res.ok) throw new Error("Extract failed");

        // Download extracted payload
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "extracted_payload";
        a.click();
        URL.revokeObjectURL(a.href);
      }
    }

    // Bind submit handlers
    form.onsubmit = handleSubmit;
    submitBtn.onclick = handleSubmit;

    /* ---------- Binary Background Effect ---------- */
    (function applyBinaryBackground() {
      function build() {
        const w = window.innerWidth, h = window.innerHeight;
        let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">`;

        // Random binary characters across screen
        for (let y = 0; y < h; y += 16)
          for (let x = 0; x < w; x += 14)
            svg += `<text x="${x}" y="${y}"
              font-size="12" fill="white" fill-opacity="0.12">`
              + (Math.random() > 0.5 ? "1" : "0") + `</text>`;

        svg += "</svg>";

        // Apply SVG + gradient background
        document.body.style.backgroundImage =
          `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}"),
           linear-gradient(135deg,#072d0f,#0b0f1a)`;
      }

      build();
      window.addEventListener("resize", () => setTimeout(build, 150));
    })();
  });
})();
