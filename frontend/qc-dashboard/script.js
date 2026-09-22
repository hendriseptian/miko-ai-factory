const checks = ["Story", "Character", "Visual", "Animation", "Voice", "Music", "Subtitle", "Technical"];
const qcList = document.getElementById("qcList");
const projectStatus = document.getElementById("projectStatus");

function renderQC() {
  qcList.innerHTML = checks.map(name => `
    <div class="qc-row">
      <span>${name}</span>
      <strong class="pending">PENDING</strong>
    </div>
  `).join("");
}

document.getElementById("loadDemo").addEventListener("click", () => {
  projectStatus.textContent = "MIKO-0001 — HUMAN_QC";
  renderQC();
});

renderQC();
