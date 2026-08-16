# CoT-forgery arm, LOCAL Ollama models. Authorized by Dave 2026-08-15 ~23:42.
#
# This one runs on Yggdrasil's GPU (RTX 3070 Ti, 8 GB VRAM), not on a paid API.
# All 15 arms verified present via `ollama list` before this was written; no
# model is pulled by this script.
#
# Two of these (phi4:14b, qwen2.5:14b) are larger than 8 GB at q4 and will
# partially offload to system RAM, so they are ordered LAST -- if the run is
# interrupted, the 13 arms that fit in VRAM are already done.
#
# Same two-invocation structure as run_cot_batch.ps1: refund_variants() raises
# on L3_notags / forged_*, so the canary levels and refund levels cannot share
# an invocation. Zero harness edits.

Set-Location "M:\Projects\Anthropic-Fellows\role-boundary-plasticity"

$CANARY_LV = 'control,L3_notags,forged_llama3,think_forged,think_forged_destyled'
$REFUND_LV = 'control,think_forged,think_forged_destyled'
$LOG = "out\cot\COT-LOCAL-LOG.txt"

New-Item -ItemType Directory -Force -Path "out\cot" | Out-Null

# Smallest first: fastest feedback, and the VRAM-safe ones bank early.
$models = @(
  'smollm2:1.7b',
  'qwen2.5:1.5b',
  'nemotron-mini',
  'gemma3:4b',
  'olmo2:7b',
  'mistral:7b',
  'qwen2.5:7b',
  'command-r7b',
  'granite3.3:8b',
  'hermes3:8b',
  'llama3.1:8b',
  'deepseek-r1:8b',
  'qwen3:8b',
  # over 8 GB at q4 -- these spill to system RAM and run slow. Last on purpose.
  'qwen2.5:14b',
  'phi4:14b'
)

"=== COT LOCAL BATCH START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File $LOG -Append -Encoding utf8

foreach ($m in $models) {
  $safe = $m -replace '[:./]','_'
  $out  = "out/cot/local_$safe.csv"
  $expected = 33

  if (Test-Path $out) {
    $existing = @(Import-Csv $out).Count
    if ($existing -ge $expected) {
      "[$(Get-Date -Format HH:mm:ss)] SKIP $m (already $existing rows)" | Out-File $LOG -Append -Encoding utf8
      continue
    }
    $bak = "out/cot/partial_local_${safe}_$(Get-Date -Format 'HHmmss').csv"
    Rename-Item $out (Split-Path $bak -Leaf)
    "[$(Get-Date -Format HH:mm:ss)] partial $m ($existing rows) set aside as $bak" | Out-File $LOG -Append -Encoding utf8
  }

  "[$(Get-Date -Format HH:mm:ss)] START $m" | Out-File $LOG -Append -Encoding utf8
  try {
    python -u harness.py --provider ollama --model $m --out $out --canary-only --levels $CANARY_LV 2>&1 | Out-Null
    python -u harness.py --provider ollama --model $m --out $out --refund-only --levels $REFUND_LV 2>&1 | Out-Null

    $n = if (Test-Path $out) { @(Import-Csv $out).Count } else { 0 }
    $errs = if ($n -gt 0) { @(Import-Csv $out | Where-Object { $_.error }).Count } else { 0 }
    "[$(Get-Date -Format HH:mm:ss)] DONE  $m : $n rows ($errs error rows)" | Out-File $LOG -Append -Encoding utf8
  } catch {
    "[$(Get-Date -Format HH:mm:ss)] ERROR $m : $($_.Exception.Message)" | Out-File $LOG -Append -Encoding utf8
  }
}

"=== COT LOCAL BATCH END $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File $LOG -Append -Encoding utf8
