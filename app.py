"""
Invoice Extractor — Single File App
=====================================
Local:  python app.py  →  http://localhost:5000
Hosted: Deploy to Render.com (free)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)

# ── CONFIG ───────────────────────────────────────────────────────
# Locally: reads from your environment or falls back to the string
# On Render: set OPENROUTER_API_KEY in the dashboard Environment tab
OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "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"
)
MODEL          = "google/gemini-2.0-flash-001"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# ────────────────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are an AI assistant for Indian CA firms.
Extract ALL financial data from this invoice document.
Return ONLY valid JSON — no explanation, no markdown, no backticks.

{
  "vendor_name": "",
  "invoice_number": "",
  "invoice_date": "",
  "due_date": "",
  "gstin_vendor": "",
  "gstin_buyer": "",
  "pan_number": "",
  "taxable_amount": "",
  "cgst": "",
  "sgst": "",
  "igst": "",
  "total_amount": "",
  "line_items": [
    { "description": "", "quantity": "", "rate": "", "amount": "" }
  ],
  "confidence": "High or Medium or Low",
  "summary": "one sentence summary of the invoice"
}

Rules:
- Amounts as numbers only — no Rs, no commas, no symbols
- Dates in DD-MM-YYYY format
- Empty string if field not found
"""

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Invoice Extractor</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f4f4f0; min-height: 100vh; padding: 2rem 1rem; color: #111;
    }
    .wrap { max-width: 580px; margin: 0 auto; }
    .header { display: flex; align-items: center; gap: 10px; margin-bottom: 1.75rem; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #1a56db; }
    .header h1 { font-size: 18px; font-weight: 600; }
    .badge {
      margin-left: auto; background: #dbeafe; color: #1e40af;
      font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 20px;
    }
    .card {
      background: #fff; border: 1px solid #e5e5e0;
      border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem;
    }
    .upload-zone {
      border: 2px dashed #d1d5db; border-radius: 12px;
      padding: 2.5rem 1rem; text-align: center; cursor: pointer;
      transition: all .2s; background: #fafafa; position: relative;
    }
    .upload-zone:hover { border-color: #1a56db; background: #eff6ff; }
    .upload-zone input {
      position: absolute; inset: 0; opacity: 0;
      cursor: pointer; width: 100%; height: 100%;
    }
    .upload-icon { font-size: 36px; margin-bottom: 10px; }
    .upload-title { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
    .upload-sub { font-size: 13px; color: #6b7280; }
    .or {
      display: flex; align-items: center; gap: 12px;
      color: #9ca3af; font-size: 12px; margin: 14px 0;
    }
    .or::before, .or::after { content:''; flex:1; height:1px; background:#e5e7eb; }
    .sample-btn {
      width: 100%; padding: 12px; border: 1px solid #e5e5e0;
      border-radius: 10px; background: #fff; font-size: 13px;
      font-weight: 500; color: #374151; cursor: pointer; transition: all .15s;
    }
    .sample-btn:hover { background: #eff6ff; border-color: #1a56db; color: #1a56db; }
    #state-processing { display: none; }
    .spinner {
      width: 40px; height: 40px; border: 3px solid #e5e7eb;
      border-top-color: #1a56db; border-radius: 50%;
      animation: spin .7s linear infinite; margin: 0 auto 16px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .proc-title { font-size: 14px; font-weight: 600; text-align: center; margin-bottom: 4px; }
    .proc-sub { font-size: 12px; color: #9ca3af; text-align: center; }
    .progress-bar { height: 4px; background: #e5e7eb; border-radius: 4px; margin-top: 16px; overflow: hidden; }
    .progress-fill { height: 100%; background: #1a56db; border-radius: 4px; transition: width .4s ease; }
    #state-result { display: none; }
    .result-header {
      background: #1a56db; border-radius: 12px; padding: 1.25rem 1.5rem;
      margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: flex-start;
    }
    .result-vendor { color: #fff; font-size: 16px; font-weight: 600; margin-bottom: 3px; }
    .result-inv { color: rgba(255,255,255,.7); font-size: 12px; }
    .conf-pill {
      background: rgba(255,255,255,.2); color: #fff; font-size: 11px;
      font-weight: 600; padding: 4px 10px; border-radius: 20px; white-space: nowrap;
    }
    .amounts { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin-bottom: 1rem; }
    .amt-box {
      background: #f9fafb; border: 1px solid #e5e7eb;
      border-radius: 10px; padding: 12px 8px; text-align: center;
    }
    .amt-label { font-size: 11px; color: #6b7280; margin-bottom: 4px; }
    .amt-val { font-size: 19px; font-weight: 700; color: #111; }
    .amt-val.green { color: #15803d; }
    .sec-label {
      font-size: 11px; font-weight: 600; color: #9ca3af;
      letter-spacing: .05em; text-transform: uppercase; margin: 16px 0 8px;
    }
    .fields {
      width: 100%; border-collapse: collapse; font-size: 13px;
      background: #fff; border: 1px solid #e5e7eb;
      border-radius: 12px; overflow: hidden; margin-bottom: 1rem;
    }
    .fields td { padding: 10px 14px; border-bottom: 1px solid #f3f4f6; }
    .fields tr:last-child td { border-bottom: none; }
    .fields .lbl { color: #6b7280; width: 45%; }
    .fields .val { font-weight: 500; text-align: right; }
    .lines {
      width: 100%; border-collapse: collapse; font-size: 12px;
      background: #fff; border: 1px solid #e5e7eb;
      border-radius: 12px; overflow: hidden; margin-bottom: 1rem;
    }
    .lines th {
      text-align: left; padding: 9px 12px; background: #f9fafb;
      color: #6b7280; font-size: 11px; font-weight: 600; border-bottom: 1px solid #e5e7eb;
    }
    .lines td { padding: 9px 12px; border-bottom: 1px solid #f3f4f6; color: #374151; }
    .lines tr:last-child td { border-bottom: none; }
    .summary-box {
      background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px;
      padding: 10px 14px; font-size: 13px; color: #1e40af; margin-bottom: 1rem; line-height: 1.5;
    }
    .btns { display: flex; gap: 8px; }
    .btn {
      flex: 1; padding: 12px; border-radius: 10px; font-size: 13px;
      font-weight: 600; cursor: pointer; border: 1px solid #e5e7eb;
      background: #fff; color: #374151; transition: all .15s;
    }
    .btn:hover { background: #f9fafb; }
    .btn-primary { background: #1a56db; color: #fff; border-color: #1a56db; }
    .btn-primary:hover { background: #1648c0; }
    .error-box {
      display: none; background: #fef2f2; border: 1px solid #fecaca;
      border-radius: 10px; padding: 12px 14px; font-size: 13px;
      color: #b91c1c; margin-top: 12px; line-height: 1.5;
    }
    .footer { text-align: center; font-size: 11px; color: #9ca3af; margin-top: 1.5rem; }
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="dot"></div>
    <h1>Invoice Extractor</h1>
    <span class="badge">AI Powered</span>
  </div>

  <div id="state-upload">
    <div class="card">
      <div class="upload-zone">
        <input type="file" id="file-input" accept=".pdf,.jpg,.jpeg,.png" onchange="handleFile(this)">
        <div class="upload-icon">📄</div>
        <div class="upload-title">Upload Invoice</div>
        <div class="upload-sub">PDF, JPG, PNG &middot; AI extracts all fields instantly</div>
      </div>
      <div class="or">or</div>
      <button class="sample-btn" onclick="runSample()">Try with a sample invoice &rarr;</button>
      <div class="error-box" id="err"></div>
    </div>
  </div>

  <div id="state-processing">
    <div class="card" style="text-align:center;padding:2rem">
      <div class="spinner"></div>
      <div class="proc-title" id="proc-msg">Reading invoice...</div>
      <div class="proc-sub" id="proc-step">Step 1 of 4</div>
      <div class="progress-bar"><div class="progress-fill" id="prog" style="width:10%"></div></div>
    </div>
  </div>

  <div id="state-result">
    <div class="result-header">
      <div>
        <div class="result-vendor" id="r-vendor">—</div>
        <div class="result-inv" id="r-invno">—</div>
      </div>
      <span class="conf-pill" id="r-conf">High confidence</span>
    </div>
    <div class="summary-box" id="r-summary"></div>
    <div class="amounts">
      <div class="amt-box"><div class="amt-label">Taxable</div><div class="amt-val" id="r-taxable">—</div></div>
      <div class="amt-box"><div class="amt-label">GST</div><div class="amt-val" id="r-gst">—</div></div>
      <div class="amt-box"><div class="amt-label">Total</div><div class="amt-val green" id="r-total">—</div></div>
    </div>
    <div class="sec-label">Invoice details</div>
    <table class="fields">
      <tr><td class="lbl">Invoice date</td><td class="val" id="r-date">—</td></tr>
      <tr><td class="lbl">Due date</td><td class="val" id="r-due">—</td></tr>
      <tr><td class="lbl">Vendor GSTIN</td><td class="val" id="r-gv">—</td></tr>
      <tr><td class="lbl">Buyer GSTIN</td><td class="val" id="r-gb">—</td></tr>
      <tr><td class="lbl">PAN</td><td class="val" id="r-pan">—</td></tr>
      <tr><td class="lbl">CGST</td><td class="val" id="r-cgst">—</td></tr>
      <tr><td class="lbl">SGST</td><td class="val" id="r-sgst">—</td></tr>
      <tr><td class="lbl">IGST</td><td class="val" id="r-igst">—</td></tr>
    </table>
    <div class="sec-label">Line items</div>
    <table class="lines">
      <thead><tr><th>Description</th><th>Qty</th><th>Rate</th><th>Amount</th></tr></thead>
      <tbody id="r-items"></tbody>
    </table>
    <div class="btns">
      <button class="btn btn-primary" onclick="exportCSV()">Export to Excel / CSV</button>
      <button class="btn" onclick="reset()">Extract another</button>
    </div>
  </div>

  <div class="footer">Invoice Extractor &middot; Powered by AI</div>
</div>

<script>
const SAMPLE = `TAX INVOICE
Vendor: Rajan Traders Pvt Ltd
GSTIN: 33AABCR1234F1Z5
Invoice No: RT/2024/1847
Invoice Date: 15-03-2024
Due Date: 30-03-2024
Bill To: Mehta & Associates, Chennai
GSTIN: 33AABCM9876G1Z2
Items:
1. Professional Consulting - 10 hrs @ Rs.2500 = Rs.25000
2. Documentation & Filing - 1 lot = Rs.5000
3. Travel Expenses - 1 lot = Rs.2000
Taxable Amount: Rs.32,000
CGST 9%: Rs.2,880
SGST 9%: Rs.2,880
Total: Rs.37,760`;

const STEPS = [
  ["Reading document...",   "Step 1 of 4", "25%"],
  ["Identifying fields...", "Step 2 of 4", "50%"],
  ["Extracting amounts...", "Step 3 of 4", "75%"],
  ["Validating data...",    "Step 4 of 4", "90%"],
];

let saved = null, timer = null;

function show(id) {
  ["state-upload","state-processing","state-result"].forEach(s =>
    document.getElementById(s).style.display = s === id ? "block" : "none"
  );
}

function startSteps() {
  let i = 0;
  function tick() {
    if (i >= STEPS.length) return;
    document.getElementById("proc-msg").textContent  = STEPS[i][0];
    document.getElementById("proc-step").textContent = STEPS[i][1];
    document.getElementById("prog").style.width      = STEPS[i][2];
    i++; timer = setTimeout(tick, 800);
  }
  tick();
}

function stopSteps() {
  clearTimeout(timer);
  document.getElementById("prog").style.width = "100%";
}

function handleFile(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    const b64 = e.target.result.split(",")[1];
    callServer("file", null, b64, file.type);
  };
  reader.readAsDataURL(file);
}

function runSample() { callServer("text", SAMPLE, null, null); }

async function callServer(mode, text, b64, ftype) {
  show("state-processing");
  startSteps();
  document.getElementById("err").style.display = "none";

  const body = { mode };
  if (mode === "text") body.text = text;
  if (mode === "file") { body.file_base64 = b64; body.file_type = ftype; }

  try {
    const res = await fetch("/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    stopSteps();
    const result = await res.json();
    if (result.error) { showErr(result.error); return; }
    saved = result.data;
    render(result.data);
  } catch (e) {
    stopSteps();
    showErr("Network error: " + e.message);
  }
}

function fmt(v) {
  if (!v || v === "") return "—";
  const n = parseFloat(String(v).replace(/,/g, ""));
  return isNaN(n) || n === 0 ? "—" : "\u20B9" + n.toLocaleString("en-IN");
}

function render(d) {
  document.getElementById("r-vendor").textContent  = d.vendor_name  || "Unknown Vendor";
  document.getElementById("r-invno").textContent   = "Invoice #" + (d.invoice_number || "—");
  document.getElementById("r-conf").textContent    = (d.confidence  || "High") + " confidence";
  document.getElementById("r-summary").textContent = d.summary      || "Extraction complete.";
  document.getElementById("r-date").textContent    = d.invoice_date || "—";
  document.getElementById("r-due").textContent     = d.due_date     || "—";
  document.getElementById("r-gv").textContent      = d.gstin_vendor || "—";
  document.getElementById("r-gb").textContent      = d.gstin_buyer  || "—";
  document.getElementById("r-pan").textContent     = d.pan_number   || "—";
  document.getElementById("r-cgst").textContent    = fmt(d.cgst);
  document.getElementById("r-sgst").textContent    = fmt(d.sgst);
  document.getElementById("r-igst").textContent    = fmt(d.igst);
  document.getElementById("r-taxable").textContent = fmt(d.taxable_amount);
  document.getElementById("r-total").textContent   = fmt(d.total_amount);

  const gst = (parseFloat(d.cgst||0) + parseFloat(d.sgst||0) + parseFloat(d.igst||0));
  document.getElementById("r-gst").textContent = gst > 0
    ? "\u20B9" + gst.toLocaleString("en-IN") : "—";

  const tb = document.getElementById("r-items");
  tb.innerHTML = (d.line_items && d.line_items.length)
    ? d.line_items.map(i =>
        `<tr><td>${i.description||"—"}</td><td>${i.quantity||"—"}</td>
         <td>${fmt(i.rate)}</td><td>${fmt(i.amount)}</td></tr>`
      ).join("")
    : `<tr><td colspan="4" style="text-align:center;color:#9ca3af">No line items found</td></tr>`;

  show("state-result");
}

function exportCSV() {
  if (!saved) return;
  const d = saved;
  const rows = [
    ["Field","Value"],
    ["Vendor",d.vendor_name],["Invoice No",d.invoice_number],
    ["Date",d.invoice_date],["Due Date",d.due_date],
    ["GSTIN Vendor",d.gstin_vendor],["GSTIN Buyer",d.gstin_buyer],
    ["PAN",d.pan_number],["Taxable",d.taxable_amount],
    ["CGST",d.cgst],["SGST",d.sgst],["IGST",d.igst],["Total",d.total_amount],
    [""],["Description","Quantity","Rate","Amount"],
    ...(d.line_items||[]).map(i=>[i.description,i.quantity,i.rate,i.amount])
  ];
  const csv  = rows.map(r=>r.map(c=>`"${c||""}"`).join(",")).join("\\n");
  const blob = new Blob([csv],{type:"text/csv"});
  const a    = document.createElement("a");
  a.href     = URL.createObjectURL(blob);
  a.download = `invoice_${d.invoice_number||"extracted"}.csv`;
  a.click();
}

function showErr(msg) {
  show("state-upload");
  const e = document.getElementById("err");
  e.textContent   = "⚠ " + msg;
  e.style.display = "block";
}

function reset() {
  saved = null;
  document.getElementById("file-input").value = "";
  show("state-upload");
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return HTML


@app.route("/extract", methods=["POST"])
def extract():
    raw_text = ""
    try:
        data = request.get_json()
        mode = data.get("mode")

        if mode == "text":
            messages = [{
                "role": "user",
                "content": EXTRACTION_PROMPT + "\n\nInvoice text:\n" + data.get("text","")
            }]
        elif mode == "file":
            file_b64  = data.get("file_base64","")
            file_type = data.get("file_type","image/jpeg")
            messages = [{
                "role": "user",
                "content": [
                    {"type":"image_url","image_url":{"url":f"data:{file_type};base64,{file_b64}"}},
                    {"type":"text","text":EXTRACTION_PROMPT}
                ]
            }]
        else:
            return jsonify({"error": "Invalid mode"}), 400

        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://invoice-extractor.onrender.com",
                "X-Title":       "Invoice Extractor"
            },
            json={"model":MODEL,"messages":messages,"max_tokens":1500,"temperature":0.1},
            timeout=30
        )

        if resp.status_code != 200:
            return jsonify({"error":f"OpenRouter error {resp.status_code}","detail":resp.text}), 500

        raw_text = resp.json()["choices"][0]["message"]["content"]
        clean    = raw_text.strip().replace("```json","").replace("```","").strip()
        return jsonify({"success":True,"data":json.loads(clean)})

    except json.JSONDecodeError:
        return jsonify({"error":"AI returned invalid JSON. Try again.","raw":raw_text}), 500
    except requests.exceptions.Timeout:
        return jsonify({"error":"Request timed out."}), 500
    except Exception as e:
        return jsonify({"error":str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status":"ok","model":MODEL})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n{'='*45}")
    print(f"  Invoice Extractor running on port {port}")
    print(f"  Open: http://localhost:{port}")
    print(f"{'='*45}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
