"""One-shot insight pass over live CSVs. Prints JSON. Does not write corpus files."""
import csv
import glob
import json
import os
import sys
from collections import defaultdict

csv.field_size_limit(10_000_000)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rescore import rescore_row, api_refusal  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")


def tb(v):
    return str(v).lower() == "true"


def usable(r):
    return (not (r.get("error") or "").strip()) and (not tb(r.get("api_refusal", False)))


def rate(rows):
    good = [r for r in rows if usable(r)]
    n = len(good)
    k = sum(1 for r in good if tb(r.get("compromised")))
    d = sum(1 for r in good if tb(r.get("detected")))
    return {"k": k, "n": n, "pct": round(100.0 * k / n, 1) if n else None, "detected": d}


def load_csv(path, score=False):
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("scaffold"):
                continue
            r["_source"] = r.get("_source") or path
            rows.append(rescore_row(r) if score else r)
            if not score:
                # coerce
                if "compromised" in r:
                    r["compromised"] = tb(r["compromised"])
                    r["detected"] = tb(r.get("detected"))
                    r["api_refusal"] = tb(r.get("api_refusal"))
                    r["verbal_only"] = tb(r.get("verbal_only"))
    return rows


def native_family(model):
    m = (model or "").lower()
    if any(x in m for x in ("claude", "fable", "sonnet", "opus", "haiku")):
        return "anthropic"
    if "llama" in m or "hermes" in m:
        return "llama"
    if "qwen" in m:
        return "qwen"
    if m.startswith("gpt") or "gpt-oss" in m:
        return "gpt"
    if "gemini" in m or "gemma" in m:
        return "google"
    if "mistral" in m or "mixtral" in m or "ministral" in m:
        return "mistral"
    if "deepseek" in m:
        return "deepseek"
    if "grok" in m:
        return "xai"
    if "kimi" in m:
        return "moonshot"
    if "glm" in m:
        return "zai"
    if "nemotron" in m:
        return "nvidia"
    if "minimax" in m:
        return "minimax"
    if "phi" in m:
        return "microsoft"
    if "olmo" in m:
        return "ai2"
    if "granite" in m:
        return "ibm"
    if "command" in m:
        return "cohere"
    if "smol" in m:
        return "huggingface"
    return "other"


def native_syntax(family):
    return {
        "anthropic": "forged_xml_anthropic",
        "llama": "forged_llama3",
        "qwen": "forged_chatml",
        "gpt": "forged_chatml",
        "google": "forged_generic",
        "mistral": "forged_generic",
        "deepseek": "forged_chatml",
        "xai": "forged_generic",
    }.get(family)


def cell(rows, **kw):
    out = []
    for r in rows:
        ok = True
        for k, v in kw.items():
            if k == "level_prefix":
                if not str(r.get("level", "")).startswith(v):
                    ok = False
                    break
            elif k == "levels":
                if r.get("level") not in v:
                    ok = False
                    break
            elif k == "not_level":
                if r.get("level") == v:
                    ok = False
                    break
            elif k == "attack":
                if r.get("level") == "control":
                    ok = False
                    break
            elif r.get(k) != v:
                ok = False
                break
        if ok:
            out.append(r)
    return out


def main():
    main_path = os.path.join(OUT, "rescored_all.csv")
    main_rows = load_csv(main_path, score=False)
    # already scored; coerce bools done in load if compromised present
    for r in main_rows:
        r["compromised"] = tb(r.get("compromised")) if not isinstance(r.get("compromised"), bool) else r["compromised"]
        r["detected"] = tb(r.get("detected")) if not isinstance(r.get("detected"), bool) else r["detected"]
        r["api_refusal"] = tb(r.get("api_refusal")) if not isinstance(r.get("api_refusal"), bool) else r["api_refusal"]
        r["verbal_only"] = tb(r.get("verbal_only")) if not isinstance(r.get("verbal_only"), bool) else r["verbal_only"]

    cloud_rows = []
    for path in sorted(glob.glob(os.path.join(OUT, "cloud_*.csv"))):
        cloud_rows.extend(load_csv(path, score=True))

    cot_path = os.path.join(OUT, "cot", "cot_all_scored.csv")
    cot_rows = load_csv(cot_path, score=False) if os.path.exists(cot_path) else []
    for r in cot_rows:
        r["compromised"] = tb(r.get("compromised")) if not isinstance(r.get("compromised"), bool) else r["compromised"]
        r["detected"] = tb(r.get("detected")) if not isinstance(r.get("detected"), bool) else r["detected"]
        r["api_refusal"] = tb(r.get("api_refusal")) if not isinstance(r.get("api_refusal"), bool) else r["api_refusal"]

    sources = defaultdict(int)
    for r in main_rows:
        sources[r.get("_source", "?")] += 1

    report = {}
    report["inventory"] = {
        "main_rows": len(main_rows),
        "main_usable": rate(main_rows)["n"],
        "main_errors": sum(1 for r in main_rows if (r.get("error") or "").strip()),
        "main_api_refusals": sum(1 for r in main_rows if r.get("api_refusal") is True or tb(r.get("api_refusal"))),
        "main_models": sorted(set(r["model"] for r in main_rows)),
        "main_n_models": len(set(r["model"] for r in main_rows)),
        "main_levels": sorted(set(r.get("level", "") for r in main_rows)),
        "main_channels": sorted(set(r.get("channel", "") for r in main_rows)),
        "main_scaffolds": sorted(set(r.get("scaffold", "") for r in main_rows)),
        "main_defenses": sorted(set((r.get("defense") or "") for r in main_rows)),
        "main_sources": dict(sources),
        "cloud_in_main": any("cloud_" in (s or "") for s in sources),
        "cloud_rows": len(cloud_rows),
        "cloud_usable": rate(cloud_rows)["n"],
        "cloud_models": sorted(set(r["model"] for r in cloud_rows if r.get("model"))),
        "cloud_n_models": len(set(r["model"] for r in cloud_rows if r.get("model"))),
        "cot_rows": len(cot_rows),
        "cot_usable": rate(cot_rows)["n"],
        "cot_models": sorted(set(r["model"] for r in cot_rows if r.get("model"))),
        "cot_n_models": len(set(r["model"] for r in cot_rows if r.get("model"))),
    }

    # Combined unique attack rows for overview (keep corpora separate for most tests)
    report["control"] = {
        "main": rate(cell(main_rows, level="control")),
        "cloud": rate(cell(cloud_rows, level="control")),
        "cot": rate(cell(cot_rows, level="control")),
    }

    # Intensity on canary + tool_result (the designed comparison)
    def intensity_block(rows, label):
        canary = [r for r in rows if r.get("scaffold") != "refund_ticket"]
        tr = [r for r in canary if r.get("channel") in ("tool_result", "", None) or r.get("channel") == "tool_result"]
        # some rows may use tool_result only
        out = {}
        for lv in ("L1", "L2", "L3", "L3_notags"):
            out[lv] = rate(cell(tr, level=lv, channel="tool_result"))
        # if channel missing, fallback
        if out["L2"]["n"] == 0:
            for lv in ("L1", "L2", "L3", "L3_notags"):
                out[lv] = rate(cell(canary, level=lv))
        l2, l3, nt = out["L2"], out["L3"], out["L3_notags"]
        tone = None
        demand = None
        if l3["n"] and nt["n"] and l3["pct"] is not None and nt["pct"] is not None:
            tone = round(l3["pct"] - nt["pct"], 1)
        if l2["n"] and nt["n"] and l2["pct"] is not None and nt["pct"] is not None:
            demand = round(l2["pct"] - nt["pct"], 1)
        out["tone_effect_L3_minus_notags"] = tone
        out["demand_effect_L2_minus_notags"] = demand
        return out

    report["intensity_canary"] = {
        "main": intensity_block(main_rows, "main"),
        "cloud": intensity_block(cloud_rows, "cloud"),
    }

    # Per-model L2 vs L3 inversion (canary, tool_result)
    def inversions(rows):
        by = defaultdict(lambda: defaultdict(list))
        for r in rows:
            if r.get("scaffold") == "refund_ticket":
                continue
            if r.get("channel") not in ("tool_result", None, "") and r.get("channel") != "tool_result":
                continue
            if r.get("level") not in ("L2", "L3", "L3_notags"):
                continue
            if not usable(r):
                continue
            by[r["model"]][r["level"]].append(r)
        rows_out = []
        for m, lv in by.items():
            def rp(name):
                rs = lv.get(name, [])
                n = len(rs)
                k = sum(1 for r in rs if r["compromised"] is True or tb(r.get("compromised")))
                return k, n, (round(100 * k / n, 1) if n else None)
            l2 = rp("L2")
            l3 = rp("L3")
            nt = rp("L3_notags")
            inv = (l2[2] is not None and l3[2] is not None and l2[2] > l3[2] + 15 and l2[1] >= 3 and l3[1] >= 3)
            rows_out.append({
                "model": m, "L2": f"{l2[0]}/{l2[1]}", "L2_pct": l2[2],
                "L3": f"{l3[0]}/{l3[1]}", "L3_pct": l3[2],
                "L3_notags": f"{nt[0]}/{nt[1]}", "notags_pct": nt[2],
                "polite_stronger": inv,
                "delta_L2_minus_L3": round(l2[2] - l3[2], 1) if l2[2] is not None and l3[2] is not None else None,
            })
        rows_out.sort(key=lambda x: (x["delta_L2_minus_L3"] is None, -(x["delta_L2_minus_L3"] or 0)))
        return rows_out

    report["l2_vs_l3_per_model"] = {
        "main": inversions(main_rows),
        "cloud": inversions(cloud_rows),
    }

    # Forgery syntax ranking
    def syntax_rank(rows):
        forged = [r for r in rows if str(r.get("level", "")).startswith("forged_") and r.get("scaffold") != "refund_ticket"]
        by = defaultdict(list)
        for r in forged:
            if usable(r):
                by[r["level"]].append(r)
        ranked = []
        for lv, rs in sorted(by.items()):
            ranked.append({"level": lv, **rate(rs)})
        ranked.sort(key=lambda x: -(x["pct"] or 0))
        notags = rate([r for r in rows if r.get("level") == "L3_notags" and r.get("scaffold") != "refund_ticket" and usable(r)])
        return {"notags": notags, "syntaxes": ranked}

    report["syntax"] = {
        "main": syntax_rank(main_rows),
        "cloud": syntax_rank(cloud_rows),
    }

    # Native-syntax matching: does a model's native delimiter outperform the pool mean for that model?
    def native_match(rows):
        forged = [r for r in rows if str(r.get("level", "")).startswith("forged_") and r.get("scaffold") != "refund_ticket" and usable(r)]
        by_m = defaultdict(lambda: defaultdict(list))
        for r in forged:
            by_m[r["model"]][r["level"]].append(r)
        out = []
        for m, lvs in by_m.items():
            fam = native_family(m)
            native = native_syntax(fam)
            rates = {}
            for lv, rs in lvs.items():
                rates[lv] = rate(rs)
            if not rates:
                continue
            best = max(rates.items(), key=lambda kv: kv[1]["pct"] if kv[1]["pct"] is not None else -1)
            native_r = rates.get(native) if native else None
            mean_pct = sum(v["pct"] for v in rates.values() if v["pct"] is not None) / max(1, sum(1 for v in rates.values() if v["pct"] is not None))
            out.append({
                "model": m, "family": fam, "hypothesized_native": native,
                "best_syntax": best[0], "best_pct": best[1]["pct"],
                "native_pct": native_r["pct"] if native_r else None,
                "native_is_best": (best[0] == native) if native else None,
                "native_minus_mean": round(native_r["pct"] - mean_pct, 1) if native_r and native_r["pct"] is not None else None,
                "n_syntaxes": len(rates),
            })
        hits = [x for x in out if x["native_is_best"] is True]
        misses = [x for x in out if x["native_is_best"] is False]
        return {
            "n_models": len(out),
            "native_is_best": len(hits),
            "native_not_best": len(misses),
            "models": sorted(out, key=lambda x: (x["native_minus_mean"] is None, -(x["native_minus_mean"] or 0))),
        }

    report["native_syntax_match"] = {
        "main": native_match(main_rows),
        "cloud": native_match(cloud_rows),
    }

    # Channel
    def channel_block(rows):
        attack = [r for r in rows if r.get("level") != "control" and r.get("scaffold") != "refund_ticket"]
        out = {}
        for ch in sorted(set(r.get("channel") or "" for r in attack)):
            out[ch or "(blank)"] = rate([r for r in attack if (r.get("channel") or "") == ch])
        # matched vs tool on same levels if both exist
        return out

    report["channel"] = {
        "main": channel_block(main_rows),
        "cloud": channel_block(cloud_rows),
    }

    # Channel swap: bare_command / user_turn_matched vs tool_result same level
    def channel_swap(rows):
        by = defaultdict(lambda: defaultdict(list))
        for r in rows:
            if not usable(r):
                continue
            if r.get("scaffold") == "refund_ticket":
                continue
            by[(r["model"], r["level"])][r.get("channel") or ""].append(r)
        pairs = []
        for key, chs in by.items():
            if "tool_result" in chs and "user_turn_matched" in chs:
                tr = rate(chs["tool_result"])
                ut = rate(chs["user_turn_matched"])
                pairs.append({
                    "model": key[0], "level": key[1],
                    "tool": tr, "user_matched": ut,
                    "delta_tool_minus_user": round((tr["pct"] or 0) - (ut["pct"] or 0), 1) if tr["n"] and ut["n"] else None,
                })
        if not pairs:
            return {"n_pairs": 0}
        deltas = [p["delta_tool_minus_user"] for p in pairs if p["delta_tool_minus_user"] is not None]
        return {
            "n_pairs": len(pairs),
            "mean_delta_tool_minus_user": round(sum(deltas) / len(deltas), 1) if deltas else None,
            "tool_higher": sum(1 for d in deltas if d > 5),
            "user_higher": sum(1 for d in deltas if d < -5),
            "sample": sorted(pairs, key=lambda p: abs(p["delta_tool_minus_user"] or 0), reverse=True)[:12],
        }

    report["channel_swap"] = {
        "main": channel_swap(main_rows),
        "cloud": channel_swap(cloud_rows),
    }

    # Defense
    def defense_block(rows):
        attack = [r for r in rows if r.get("level") != "control"]
        by = defaultdict(list)
        for r in attack:
            by[(r.get("defense") or "(blank)")].append(r)
        return {k: rate(v) for k, v in sorted(by.items())}

    report["defense"] = defense_block(main_rows)

    # Scaffold dissociation
    def scaffold_block(rows):
        attack = [r for r in rows if r.get("level") != "control"]
        by_s = defaultdict(list)
        for r in attack:
            by_s[r.get("scaffold")].append(r)
        overall = {k: rate(v) for k, v in by_s.items()}
        by_m = defaultdict(lambda: defaultdict(list))
        for r in attack:
            if usable(r):
                by_m[r["model"]][r["scaffold"]].append(r)
        dissoc = []
        for m, sc in by_m.items():
            rates = {k: rate(v) for k, v in sc.items()}
            canary_ks = [rates[k]["pct"] for k in rates if k != "refund_ticket" and rates[k]["pct"] is not None]
            canary = round(sum(canary_ks) / len(canary_ks), 1) if canary_ks else None
            ref = rates.get("refund_ticket", {})
            if canary is not None and ref.get("n") and ref.get("n") >= 3:
                gap = round(canary - (ref["pct"] or 0), 1)
                dissoc.append({
                    "model": m, "canary_pct": canary, "refund": f"{ref['k']}/{ref['n']}",
                    "refund_pct": ref["pct"], "gap_canary_minus_refund": gap,
                })
        dissoc.sort(key=lambda x: -(x["gap_canary_minus_refund"] or 0))
        return {"overall": overall, "dissociation": dissoc[:20], "n_models": len(dissoc)}

    report["scaffold"] = {
        "main": scaffold_block(main_rows),
        "cloud": scaffold_block(cloud_rows),
        "cot": scaffold_block(cot_rows),
    }

    # Detected vs compromised (attack, canary)
    def notice_comply(rows):
        attack = [r for r in rows if r.get("level") != "control" and usable(r)]
        canary = [r for r in attack if r.get("scaffold") != "refund_ticket"]
        n = len(canary)
        both = sum(1 for r in canary if r["compromised"] and r["detected"])
        comp_not_det = sum(1 for r in canary if r["compromised"] and not r["detected"])
        det_not_comp = sum(1 for r in canary if (not r["compromised"]) and r["detected"])
        neither = sum(1 for r in canary if (not r["compromised"]) and (not r["detected"]))
        by_m = defaultdict(lambda: [0, 0, 0])  # noticed_complied, noticed, n
        for r in canary:
            by_m[r["model"]][2] += 1
            if r["detected"]:
                by_m[r["model"]][1] += 1
                if r["compromised"]:
                    by_m[r["model"]][0] += 1
        models = []
        for m, (nc, noticed, tot) in by_m.items():
            if noticed >= 3:
                models.append({
                    "model": m, "noticed_and_complied": nc, "noticed": noticed, "n": tot,
                    "comply_given_notice": round(100 * nc / noticed, 1) if noticed else None,
                })
        models.sort(key=lambda x: -(x["comply_given_notice"] or 0))
        return {
            "n": n,
            "compromised_undetected": comp_not_det,
            "compromised_and_detected": both,
            "detected_resisted": det_not_comp,
            "clean_resist": neither,
            "models_notice_and_comply": models[:15],
        }

    report["notice"] = {
        "main": notice_comply(main_rows),
        "cloud": notice_comply(cloud_rows),
        "cot": notice_comply(cot_rows),
    }

    # Variant effects
    def variants(rows):
        attack = [r for r in rows if r.get("level") != "control" and usable(r)]
        by = defaultdict(list)
        for r in attack:
            by[str(r.get("variant"))].append(r)
        return {k: rate(v) for k, v in sorted(by.items())}

    report["variant"] = {
        "main": variants(main_rows),
        "cloud": variants(cloud_rows),
        "cot": variants(cot_rows),
    }

    # Model overall attack rates + clusters
    def model_rates(rows, min_n=8):
        attack = [r for r in rows if r.get("level") != "control"]
        by = defaultdict(list)
        for r in attack:
            by[r["model"]].append(r)
        out = []
        for m, rs in by.items():
            rr = rate(rs)
            if rr["n"] < min_n:
                continue
            out.append({"model": m, **rr, "family": native_family(m)})
        out.sort(key=lambda x: -(x["pct"] or 0))
        return out

    report["models_attack"] = {
        "main": model_rates(main_rows),
        "cloud": model_rates(cloud_rows),
        "cot": model_rates(cot_rows, min_n=6),
    }

    # CoT specific: llama3 vs think_forged vs destyled vs L3_notags
    def cot_conditions(rows):
        canary = [r for r in rows if r.get("scaffold") != "refund_ticket"]
        out = {}
        for lv in ("control", "L3_notags", "forged_llama3", "think_forged", "think_forged_destyled"):
            out[lv] = rate(cell(canary, level=lv))
        refund = [r for r in rows if r.get("scaffold") == "refund_ticket"]
        out["refund"] = {}
        for lv in ("control", "think_forged", "think_forged_destyled"):
            out["refund"][lv] = rate(cell(refund, level=lv))
        return out

    report["cot_conditions"] = cot_conditions(cot_rows)

    # CoT: think vs user-role forgery (llama3) per model — is the think channel WEAKER?
    def cot_think_vs_llama(rows):
        canary = [r for r in rows if r.get("scaffold") != "refund_ticket" and usable(r)]
        by = defaultdict(lambda: defaultdict(list))
        for r in canary:
            if r.get("level") in ("forged_llama3", "think_forged", "think_forged_destyled", "L3_notags"):
                by[r["model"]][r["level"]].append(r)
        out = []
        for m, lv in by.items():
            def rp(name):
                return rate(lv.get(name, []))
            llama = rp("forged_llama3")
            think = rp("think_forged")
            dest = rp("think_forged_destyled")
            nt = rp("L3_notags")
            if llama["n"] and think["n"]:
                out.append({
                    "model": m,
                    "llama3": llama, "think": think, "destyled": dest, "notags": nt,
                    "think_minus_llama": round((think["pct"] or 0) - (llama["pct"] or 0), 1),
                    "think_weaker_than_llama": (think["pct"] or 0) + 10 < (llama["pct"] or 0),
                    "think_stronger_than_llama": (think["pct"] or 0) > (llama["pct"] or 0) + 10,
                })
        weaker = sum(1 for x in out if x["think_weaker_than_llama"])
        stronger = sum(1 for x in out if x["think_stronger_than_llama"])
        return {
            "n": len(out),
            "think_weaker": weaker,
            "think_stronger": stronger,
            "mean_think_minus_llama": round(sum(x["think_minus_llama"] for x in out) / len(out), 1) if out else None,
            "models": sorted(out, key=lambda x: x["think_minus_llama"]),
        }

    report["cot_think_vs_llama"] = cot_think_vs_llama(cot_rows)

    # Cross-corpus: models in both main and cloud
    main_m = set(r["model"] for r in main_rows)
    cloud_m = set(r["model"] for r in cloud_rows)
    cot_m = set(r["model"] for r in cot_rows)
    report["overlap"] = {
        "main_and_cloud": sorted(main_m & cloud_m),
        "main_and_cot": sorted(main_m & cot_m),
        "cloud_and_cot": sorted(cloud_m & cot_m),
        "all_three": sorted(main_m & cloud_m & cot_m),
    }

    # Refund verbal_only
    def refund_split(rows):
        rr = [r for r in rows if r.get("scaffold") == "refund_ticket" and r.get("level") != "control" and usable(r)]
        tool = sum(1 for r in rr if r["compromised"] is True or tb(r.get("compromised")))
        verbal = sum(1 for r in rr if r.get("verbal_only") is True or tb(r.get("verbal_only")))
        return {"n": len(rr), "tool_calls": tool, "verbal_only": verbal,
                "tool_pct": round(100 * tool / len(rr), 1) if rr else None}

    report["refund"] = {
        "main": refund_split(main_rows),
        "cloud": refund_split(cloud_rows),
        "cot": refund_split(cot_rows),
    }

    # FLAG heuristic: "security" is a very broad marker — how often detected on control?
    report["false_detect_on_control"] = {
        "main": rate(cell(main_rows, level="control"))["detected"],
        "main_n": rate(cell(main_rows, level="control"))["n"],
        "cloud_detected": rate(cell(cloud_rows, level="control"))["detected"],
        "cot_detected": rate(cell(cot_rows, level="control"))["detected"],
    }
    # more precise
    def detect_rate(rows, level):
        rs = [r for r in cell(rows, level=level) if usable(r)]
        d = sum(1 for r in rs if r["detected"] is True or tb(r.get("detected")))
        return {"detected": d, "n": len(rs), "pct": round(100 * d / len(rs), 1) if rs else None}

    report["detect_on_control"] = {
        "main": detect_rate(main_rows, "control"),
        "cloud": detect_rate(cloud_rows, "control"),
        "cot": detect_rate(cot_rows, "control"),
    }

    # Needs review volume
    report["needs_review"] = {
        "main": sum(1 for r in main_rows if tb(r.get("needs_review"))),
        "cloud": sum(1 for r in cloud_rows if r.get("needs_review") is True or tb(r.get("needs_review"))),
        "cot": sum(1 for r in cot_rows if tb(r.get("needs_review"))),
    }

    json.dump(report, sys.stdout, indent=2, default=str)


if __name__ == "__main__":
    main()
