# Unattended cloud gauntlet batch. Authorized by Dave 2026-08-11 ~00:10.
# Runs the full 90-trial gauntlet against every Ollama Cloud model, one per CSV,
# scoring each as it finishes and appending to out/CLOUD-BATCH-LOG.txt.
#
# Design notes:
#  - Each model writes its own CSV, so an interruption never loses completed work.
#  - Already-complete models (90 rows) are skipped, so this is safe to re-run.
#  - try/catch per model: one failure cannot kill the batch.
#  - Nothing existing is touched. rescored_all.csv and chart_data.json are NOT
#    regenerated, because folding cloud data into the main corpus is Dave's call.

Set-Location "M:\Projects\Anthropic-Fellows\role-boundary-integrity"
${env:OLLAMA-API-KEY} = [Environment]::GetEnvironmentVariable('OLLAMA-API-KEY','User')

$LV = 'control,L1,L2,L3,L3_notags,forged_generic,forged_chatml,forged_llama3,forged_json,forged_xml_anthropic,forged_plain_label,bare_command'
$LOG = "out\CLOUD-BATCH-LOG.txt"

# Ordered biggest / most interesting first, so if it stops early the best data exists.
$models = @(
  'mistral-large-3:675b',
  'nemotron-3-ultra',
  'nemotron-3-super',
  'gpt-oss:120b',
  'gpt-oss:20b',
  'kimi-k3',
  'kimi-k2.6',
  'kimi-k2.7-code',
  'minimax-m3',
  'minimax-m2.7',
  'glm-5.2',
  'glm-5.1',
  'deepseek-v4-flash:preview'
)

"=== CLOUD BATCH START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File $LOG -Append -Encoding utf8

foreach ($m in $models) {
  $safe = $m -replace '[:./]','_'
  $out  = "out/cloud_$safe.csv"

  if (Test-Path $out) {
    $existing = @(Import-Csv $out).Count
    if ($existing -ge 90) {
      "[$(Get-Date -Format HH:mm:ss)] SKIP $m (already $existing rows)" | Out-File $LOG -Append -Encoding utf8
      continue
    }
    # partial file: move aside so the retry starts clean (rename, not delete)
    $bak = "out/partial_${safe}_$(Get-Date -Format 'HHmmss').csv"
    Rename-Item $out (Split-Path $bak -Leaf)
    "[$(Get-Date -Format HH:mm:ss)] partial $m ($existing rows) set aside as $bak" | Out-File $LOG -Append -Encoding utf8
  }

  "[$(Get-Date -Format HH:mm:ss)] START $m" | Out-File $LOG -Append -Encoding utf8
  try {
    python -u harness.py --provider openai-compatible --model $m `
      --base-url https://ollama.com/v1 --api-key-env OLLAMA-API-KEY `
      --out $out --levels $LV 2>&1 | Out-Null

    $n = if (Test-Path $out) { @(Import-Csv $out).Count } else { 0 }
    "[$(Get-Date -Format HH:mm:ss)] DONE  $m : $n rows" | Out-File $LOG -Append -Encoding utf8
    if ($n -gt 0) {
      python score_cloud.py $out 2>&1 | Out-File $LOG -Append -Encoding utf8
    }
  } catch {
    "[$(Get-Date -Format HH:mm:ss)] ERROR $m : $($_.Exception.Message)" | Out-File $LOG -Append -Encoding utf8
  }
}

"=== CLOUD BATCH END $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File $LOG -Append -Encoding utf8
