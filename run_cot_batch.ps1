# CoT-forgery arm batch. Authorized by Dave 2026-08-15 ~21:46.
#
# Runs the styled / destyled <think>-forgery pair plus the two in-family
# baselines (L3_notags, forged_llama3) against every model arm already in the
# corpus, EXCLUDING the 15 local Ollama models (those are GPU work on
# Yggdrasil and were not authorized -- separate ask).
#
# Design notes, mirroring run_cloud_batch.ps1:
#  - Each model writes its own CSV under out/cot/, so an interruption never
#    loses completed work.
#  - Already-complete models are skipped, so this is safe to re-run.
#  - try/catch per model: one failure cannot kill the batch.
#  - TWO invocations per model. refund_variants() raises ValueError on
#    L3_notags / forged_* (this is what silently killed every model's refund
#    pass in the 2026-08-11 cloud gauntlet), so the canary levels and the
#    refund levels must not share one invocation. This keeps the harness edit
#    count at zero.
#  - out/cot/ is a SUBDIRECTORY on purpose: rescore.py globs "out/*.csv"
#    non-recursively, so nothing here can be absorbed into rescored_all.csv
#    without someone deciding to move it.
#  - Anthropic models run LAST, per Dave.

Set-Location "M:\Projects\Anthropic-Fellows\role-boundary-plasticity"

$CANARY_LV = 'control,L3_notags,forged_llama3,think_forged,think_forged_destyled'
$REFUND_LV = 'control,think_forged,think_forged_destyled'
$LOG = "out\cot\COT-BATCH-LOG.txt"

New-Item -ItemType Directory -Force -Path "out\cot" | Out-Null

# provider, model, base-url, key-env, extra-flags, repeats, do-refund
$arms = @(
  # --- Phase A: Ollama Cloud gauntlet (18) ---
  @{p='openai-compatible'; m='mistral-large-3:675b';      u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='qwen3.5:397b';              u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='deepseek-v4-pro';           u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='deepseek-v4-flash:0731';    u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='deepseek-v4-flash:preview'; u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='gemma4:31b';                u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='nemotron-3-ultra';          u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='nemotron-3-super';          u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='nemotron-3-nano:30b';       u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='gpt-oss:120b';              u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='gpt-oss:20b';               u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  # kimi-k3 REMOVED 2026-08-15 by Dave. Not on the current Ollama Cloud plan:
  # every call returns 402 Payment Required, 33/33 rows here and 90/90 in the
  # 2026-08-11 gauntlet, so it has never produced a usable row in this project.
  # NOT an account balance problem -- gpt-oss:20b finished clean 17 seconds
  # before it and kimi-k2.6 finished clean 3 minutes after, on the same key.
  # Re-add this line if the plan changes:
  #   @{p='openai-compatible'; m='kimi-k3'; u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='kimi-k2.6';                 u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='kimi-k2.7-code';            u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='minimax-m3';                u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='minimax-m2.7';              u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='glm-5.2';                   u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}
  @{p='openai-compatible'; m='glm-5.1';                   u='https://ollama.com/v1'; k='OLLAMA-API-KEY'; x=''; r=1; ref=$true}

  # --- Phase B: other frontier APIs ---
  @{p='openai-compatible'; m='grok-4.5';      u='https://api.x.ai/v1';    k='XAI_API_KEY';    x='';                   r=1; ref=$true}
  @{p='openai-compatible'; m='gpt-5.6-luna';  u='https://api.openai.com/v1'; k='OPENAI-API-KEY'; x='--default-sampling'; r=1; ref=$true}
  @{p='openai-compatible'; m='gpt-5.6-terra'; u='https://api.openai.com/v1'; k='OPENAI-API-KEY'; x='--default-sampling'; r=1; ref=$true}
  # 6 repeats: the ONLY arm in this batch with non-deterministic sampling.
  @{p='openai-compatible'; m='gpt-5.6-sol';   u='https://api.openai.com/v1'; k='OPENAI-API-KEY'; x='--default-sampling'; r=6; ref=$true}
  # Gemini: canary only. main() never calls a refund runner for this provider.
  @{p='gemini'; m='gemini-3.6-flash';         u=''; k='GEMINI-API-KEY'; x=''; r=1; ref=$false}
  @{p='gemini'; m='gemini-3.1-pro-preview';   u=''; k='GEMINI-API-KEY'; x=''; r=1; ref=$false}
  @{p='gemini'; m='gemini-3.1-flash-lite';    u=''; k='GEMINI-API-KEY'; x=''; r=1; ref=$false}

  # --- Phase C: Anthropic, last ---
  @{p='anthropic'; m='claude-haiku-4-5';  u=''; k='X-API-KEY'; x=''; r=1; ref=$true}
  @{p='anthropic'; m='claude-sonnet-5';   u=''; k='X-API-KEY'; x=''; r=1; ref=$true}
  @{p='anthropic'; m='claude-fable-5';    u=''; k='X-API-KEY'; x=''; r=1; ref=$true}
  @{p='anthropic'; m='claude-opus-5';     u=''; k='X-API-KEY'; x=''; r=1; ref=$true}
)

"=== COT BATCH START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File $LOG -Append -Encoding utf8

foreach ($a in $arms) {
  $safe = $a.m -replace '[:./]','_'
  $out  = "out/cot/cot_$safe.csv"

  # 26 canary rows + 7 refund rows, times repeats; gemini has no refund pass.
  $expected = (26 + $(if ($a.ref) { 7 } else { 0 })) * $a.r

  if (Test-Path $out) {
    $existing = @(Import-Csv $out).Count
    if ($existing -ge $expected) {
      "[$(Get-Date -Format HH:mm:ss)] SKIP $($a.m) (already $existing rows)" | Out-File $LOG -Append -Encoding utf8
      continue
    }
    $bak = "out/cot/partial_${safe}_$(Get-Date -Format 'HHmmss').csv"
    Rename-Item $out (Split-Path $bak -Leaf)
    "[$(Get-Date -Format HH:mm:ss)] partial $($a.m) ($existing rows) set aside as $bak" | Out-File $LOG -Append -Encoding utf8
  }

  "[$(Get-Date -Format HH:mm:ss)] START $($a.m) (provider=$($a.p), repeats=$($a.r), expect $expected rows)" | Out-File $LOG -Append -Encoding utf8

  try {
    for ($i = 1; $i -le $a.r; $i++) {
      $common = @('--provider', $a.p, '--model', $a.m, '--api-key-env', $a.k, '--out', $out)
      if ($a.u) { $common += @('--base-url', $a.u) }
      if ($a.x) { $common += $a.x }

      python -u harness.py @common --canary-only --levels $CANARY_LV 2>&1 | Out-Null
      if ($a.ref) {
        python -u harness.py @common --refund-only --levels $REFUND_LV 2>&1 | Out-Null
      }
      if ($a.r -gt 1) {
        "[$(Get-Date -Format HH:mm:ss)]   rep $i/$($a.r) $($a.m) : $(@(Import-Csv $out).Count) rows so far" | Out-File $LOG -Append -Encoding utf8
      }
    }

    $n = if (Test-Path $out) { @(Import-Csv $out).Count } else { 0 }
    $errs = if ($n -gt 0) { @(Import-Csv $out | Where-Object { $_.error }).Count } else { 0 }
    "[$(Get-Date -Format HH:mm:ss)] DONE  $($a.m) : $n rows ($errs error rows)" | Out-File $LOG -Append -Encoding utf8
  } catch {
    "[$(Get-Date -Format HH:mm:ss)] ERROR $($a.m) : $($_.Exception.Message)" | Out-File $LOG -Append -Encoding utf8
  }
}

"=== COT BATCH END $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File $LOG -Append -Encoding utf8
