/*solve.js*/

(function(){
  function $id(name) {
    const el = document.getElementById(name);
    if (!el) console.warn(`solve.js: missing element with id="${name}"`);
    return el;
  }
  
  document.addEventListener("DOMContentLoaded", () => {
    console.log("solve.js loaded — DOMContentLoaded");

    const base = window.location.origin;
    const fileInput = $id("file-input");
    const drop = $id("drop-zone");
    const browseBtn = $id("browse-btn");
    const sampleBtn = $id("sample-btn");
    const modeSelect = $id("mode");
    const payloadArea = $id("payload-area");
    const payloadInput = $id("payload");
    const form = $id("upload-form");
    const submitBtn = $id("submit-btn");
    const resultInfos = $id("result-infos");
    const resultAnalyzers = $id("result-analyzers");

    const criticalMissing = [];
    if (!form) criticalMissing.push("upload-form (form)");
    if (!fileInput) criticalMissing.push("file-input (hidden file field)");
    if (!browseBtn) criticalMissing.push("browse-btn (choose file button)");
    if (!submitBtn) criticalMissing.push("submit-btn (submit button)");

    if (criticalMissing.length) {
      console.error("solve.js: critical elements missing:", criticalMissing.join(", "));
      if (resultInfos) {
        resultInfos.innerHTML = `<div style="color: #ffb3b3; background:#2b0f0f; padding:12px; border-radius:6px;">
          <strong>UniSteno UI error:</strong> Missing required elements: ${criticalMissing.join(", ")}.
          Check your <code>index.html</code> that these IDs exist. See console for details.
        </div>`;
      }
      return;
    }

    console.log("solve.js: all critical elements present, attaching handlers.");

    let savedFilename = null;

    function clearResults() {
      if (resultInfos) resultInfos.innerHTML = "";
      if (resultAnalyzers) resultAnalyzers.innerHTML = "";
    }
    function pretty(obj) {
      try { return `<pre style="white-space:pre-wrap">${JSON.stringify(obj, null, 2)}</pre>`; }
      catch(e) { return String(obj); }
    }

    if (browseBtn && fileInput) {
      browseBtn.addEventListener("click", () => fileInput.click());
    }

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;

      const dm = document.getElementById("drag-msg");
      if (dm) dm.textContent = file.name;

      try {
        await autoUploadFile(file);
      } catch (err) {
        alert("Upload error: " + err.message);
      }
    });

    if (sampleBtn) {
      sampleBtn.addEventListener("click", () => {
        alert("No sample file added yet.");
      });
    }

    if (drop) {
      drop.addEventListener("dragover", (e) => {
        e.preventDefault();
        drop.classList.add("border-primary");
      });
      drop.addEventListener("dragleave", () => {
        drop.classList.remove("border-primary");
      });
      drop.addEventListener("drop", async (e) => {
        e.preventDefault();
        drop.classList.remove("border-primary");
        const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
        if (f && fileInput) {
          fileInput.files = e.dataTransfer.files;
          const dm = $id("drag-msg");
          if (dm) dm.textContent = `${f.name} selected`;

          try {
            await autoUploadFile(f);
          } catch (err) {
            alert("Upload error: " + err.message);
          }
        }
      });
    }

    if (modeSelect) {
      function updateMode() {
        if (modeSelect.value === "embed" && payloadArea) payloadArea.classList.remove("d-none");
        else if (payloadArea) payloadArea.classList.add("d-none");
      }
      modeSelect.addEventListener("change", updateMode);
      updateMode();
    }

    async function autoUploadFile(file) {
      const fd = new FormData();
      fd.append("file", file);

      console.log("[client] Auto-uploading:", file.name);

      const res = await fetch(base + "/upload", {
        method: "POST",
        body: fd
      });

      const text = await res.text().catch(()=>null);
      let json = null;
      try { json = text ? JSON.parse(text) : null; } catch(e) {
        throw new Error("Upload returned non-JSON: " + text);
      }

      if (!res.ok) {
        throw new Error(json?.error || "Upload failed");
      }

      savedFilename = json.filename;

      const uploadStatus = document.getElementById("upload-status");
      if (uploadStatus) {
        uploadStatus.innerHTML =
          `<span style="color:#6bff8a; font-weight:600;">✔ File uploaded: ${savedFilename}</span>`;
      }

      return json;
    }

    async function handleSubmitEvent(e) {
      if (e && typeof e.preventDefault === "function") e.preventDefault();
      clearResults();

      const mode = (modeSelect && modeSelect.value) || "analyze";
      const password = ($id("password") && $id("password").value.trim()) || "";
      const file = (fileInput && fileInput.files && fileInput.files[0]) || null;

      if (!file) {
        alert("Please choose a file first.");
        return;
      }

      try {
        if (!savedFilename) {
          try {
            await autoUploadFile(file);
          } catch (err) {
            throw new Error("Failed to upload before submit: " + (err.message || err));
          }
        }

        const uploadStatus = document.getElementById("upload-status");
        if (uploadStatus) {
          uploadStatus.innerHTML = `<span style="color:#6bff8a;">✔ File uploaded: ${savedFilename}</span>`;
        }

        if (mode === "analyze") {
          const analyzeData = new FormData();
          analyzeData.append("filename", savedFilename);
          const analyzeRes = await fetch(base + "/analyze", { method: "POST", body: analyzeData });
          if (!analyzeRes.ok) {
            const err = await analyzeRes.json().catch(()=>null);
            throw new Error(err?.error || `Analyze failed (${analyzeRes.status})`);
          }
          const analyzeJson = await analyzeRes.json();
          resultInfos.classList.add("fade-in");
          resultInfos.innerHTML = pretty({ server_saved_filename: savedFilename, basic: { mime: analyzeJson.mime, size: analyzeJson.size, type: analyzeJson.type || "unknown" }});
          const analyzers = Object.assign({}, analyzeJson);
          delete analyzers.mime; delete analyzers.size; delete analyzers.filename;
          if (resultAnalyzers){
            resultAnalyzers.classList.add("fade-in");
            resultAnalyzers.innerHTML = `<h6>Analyzer output</h6>${pretty(analyzers)}`;
          }
          return;
        }

        if (mode === "embed") {
          const payloadFile = (payloadInput && payloadInput.files && payloadInput.files[0]) || null;
          if (!payloadFile) { alert("You must select a payload to embed."); return; }

          const embedData = new FormData();
          embedData.append("filename", savedFilename);
          embedData.append("password", password);
          embedData.append("payload", payloadFile);

          const embedRes = await fetch(base + "/embed", { method: "POST", body: embedData });
          if (!embedRes.ok) {
            const err = await embedRes.json().catch(()=>null);
            throw new Error(err?.error || `Embed failed (${embedRes.status})`);
          }
          const embedJson = await embedRes.json();
          if (resultInfos) resultInfos.innerHTML = pretty(embedJson);
          if (embedJson.outfile && resultInfos) {
            const link = document.createElement("a");
            link.href = `/uploads/${encodeURIComponent(embedJson.outfile)}`;
            link.download = embedJson.outfile;
            link.textContent = `Download embedded file (${embedJson.outfile})`;
            link.className = "btn btn-sm btn-outline-light mt-2";
            const wrap = document.createElement("div");
            wrap.appendChild(link);
            resultInfos.appendChild(wrap);
          }
          return;
        }

        if (mode === "extract") {
          const extractData = new FormData();
          extractData.append("filename", savedFilename);
          extractData.append("password", password);

          const extractRes = await fetch(base + "/extract", { method: "POST", body: extractData });
          const contentType = extractRes.headers.get("content-type") || "";

          if (!extractRes.ok) {
            const err = await extractRes.json().catch(()=>null);
            throw new Error(err?.error || `Extract failed (${extractRes.status})`);
          }

          if (!contentType.includes("application/json")) {
            const blob = await extractRes.blob();
            const cd = extractRes.headers.get("content-disposition") || "";
            let suggestedName = "extracted.bin";
            const match = /filename="?([^"]+)"?/.exec(cd);
            if (match) suggestedName = match[1];
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = suggestedName;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            if (resultInfos) resultInfos.innerHTML = `<div class="text-success">Downloaded extracted payload (${suggestedName})</div>`;
            return;
          }

          const extractJson = await extractRes.json();
          if (resultInfos) resultInfos.innerHTML = pretty(extractJson);
          return;
        }

      } catch (error) {
        console.error("handleSubmitEvent error:", error);
        alert("An error occurred: " + (error.message || error));
      }
    }

    if (form) form.addEventListener("submit", handleSubmitEvent);
    if (submitBtn) submitBtn.addEventListener("click", handleSubmitEvent);

    submitBtn.addEventListener("click", () => console.log("submit-btn clicked"));

    console.log("solve.js initialization complete.");
  });
  // Stable static random-binary SVG background (fixed to viewport, not reactive to mouse)
  (function applyStableSvgBinaryBackground() {
    const OPACITY = 0.12;   // tweak visibility (0.12 = 12%)
   const FONT_PX = 12;     // char size in px
   const MAX_COLS = 200;   // safety caps
   const MAX_ROWS = 120;
   const FONT_FAMILY = "Noto Sans Mono, monospace";

   function buildAndSet() {
     // viewport size (use innerWidth/innerHeight for accurate viewport)
     const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
     const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);

     // measure monospace char width (accurate)
     const measure = document.createElement("span");
     measure.style.fontFamily = FONT_FAMILY;
     measure.style.fontSize = FONT_PX + "px";
     measure.style.visibility = "hidden";
     measure.style.position = "absolute";
     measure.textContent = "0";
     document.body.appendChild(measure);
     const charW = Math.ceil(measure.getBoundingClientRect().width) || Math.ceil(FONT_PX * 0.6);
     document.body.removeChild(measure);

     // compute columns/rows, but cap so we don't create huge SVGs
     let cols = Math.ceil(vw / charW);
     let rows = Math.ceil(vh / FONT_PX);
     cols = Math.min(cols, MAX_COLS);
     rows = Math.min(rows, MAX_ROWS);

     // SVG dimensions: set to actual viewport so it covers full screen
     const svgW = vw;
     const svgH = vh;

     // We'll draw characters at integer positions scaled to fill viewport
     // Compute effective spacing so grid covers svgW/svgH
     const xStep = svgW / cols;
     const yStep = svgH / rows;
     const xOffset = Math.floor(xStep / 2);
     const yOffset = Math.floor(yStep * 0.85); // baseline tweak

     // Build SVG as string
     let parts = [];
     parts.push(`<svg xmlns='http://www.w3.org/2000/svg' width='${svgW}' height='${svgH}' viewBox='0 0 ${svgW} ${svgH}'>`);
     parts.push(`<rect width='100%' height='100%' fill='transparent'/>`);

     // paint each character deterministically random (non-repeating grid)
     // Use Math.random() here — if you want reproducible results, replace with a seeded PRNG.
     for (let r = 0; r < rows; r++) {
       const y = r * yStep + yOffset;
       for (let c = 0; c < cols; c++) {
         const x = Math.round(c * xStep + xOffset);
         const bit = Math.random() > 0.5 ? "1" : "0";
         parts.push(
           `<text x='${x}' y='${y}' font-family='${FONT_FAMILY}' font-size='${FONT_PX}px' text-anchor='middle' fill='white' fill-opacity='${OPACITY}' style='dominant-baseline:alphabetic; text-rendering:optimizeLegibility;'>${bit}</text>`
         );
       }
     }

     parts.push("</svg>");
     const svg = parts.join("");

     // Convert to data URL (URI-encode)
     const dataUrl = "data:image/svg+xml;utf8," + encodeURIComponent(svg);

     // Compose gradient + svg. Put svg first so it's painted on top of gradient,
     // but UI content (container) should have higher z-index so it remains above.
     const gradient = "linear-gradient(135deg, #072d0f 0%, #0b0f1a 100%)";

     // Apply in one go (minimize repaints) and set safe static properties
     const body = document.body;
     body.style.backgroundImage = `url("${dataUrl}"), ${gradient}`;
     body.style.backgroundRepeat = "no-repeat, no-repeat";
     body.style.backgroundSize = `${svgW}px ${svgH}px, cover`;
     body.style.backgroundPosition = `left top, center center`;
     // Keep background-attachment fixed for both layers so they don't jitter relative to viewport
     body.style.backgroundAttachment = "fixed, fixed";
   }

   function onResizeDebounced() {
     clearTimeout(onResizeDebounced._t);
     onResizeDebounced._t = setTimeout(buildAndSet, 140);
   }

   if (document.readyState === "loading") {
     document.addEventListener("DOMContentLoaded", () => {
       buildAndSet();
       window.addEventListener("resize", onResizeDebounced);
     }, { once: true });
   } else {
     buildAndSet();
     window.addEventListener("resize", onResizeDebounced);
   }
  })();
})();
