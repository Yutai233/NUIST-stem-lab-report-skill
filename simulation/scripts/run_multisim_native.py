"""Run declared AC/TRAN cases with installed Multisim; physical checks remain task-specific."""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def timestamp():
    return datetime.now().astimezone().isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, required=True, help="Per-case host wall-clock limit")
    parser.add_argument("--compiler", type=Path, help="Override x86 .NET Framework csc.exe")
    args = parser.parse_args()
    source_manifest, out = args.cases.resolve(), args.outdir.resolve()
    if out.exists():
        parser.error(f"Refuse to overwrite evidence: {out}")
    if not math.isfinite(args.timeout_s) or args.timeout_s <= 0:
        parser.error("--timeout-s must be finite and positive")
    manifest_hash = sha256(source_manifest)
    manifest = json.loads(source_manifest.read_text(encoding="utf-8-sig"))
    analysis = manifest["analysis"]
    for key in ("frequency_hz", "duration_s", "sample_rate_hz", "sample_count", "output_timeout_s"):
        value = analysis[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            parser.error(f"analysis.{key} must be a finite positive number")
    if not isinstance(analysis["sample_count"], int) or analysis["sample_count"] > 2147483647:
        parser.error("sample_count must be a positive Int32")
    config = {"analysis": analysis}
    if "outputs" in manifest:
        names = manifest["outputs"]
        if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names):
            parser.error("outputs must be a nonempty list of exact output names, or omitted")
        if len(names) != len(set(names)):
            parser.error("Duplicate outputs")
        config["outputs"] = names
    cases = manifest["cases"]
    if not isinstance(cases, list) or not cases:
        parser.error("cases must be a nonempty list")
    seen = set()
    resolved = []
    for case in cases:
        name = case["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
            parser.error(f"Unsafe case name: {name!r}")
        if name.casefold() in seen or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])", name):
            parser.error(f"Duplicate or reserved case name: {name}")
        seen.add(name.casefold())
        path = (source_manifest.parent / case["binary"]).resolve()
        digest = sha256(path)
        if digest.lower() != str(case["sha256"]).lower():
            parser.error(f"Input hash changed: {path}")
        resolved.append(dict(case, binary=str(path), sha256=digest))
    compiler = args.compiler or Path(os.environ.get("WINDIR", "C:/Windows")) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
    if os.name != "nt" or not compiler.is_file():
        parser.error("Windows and x86 .NET Framework csc.exe are required; use --compiler if needed")
    host_source = Path(__file__).with_name("NativeSolve.cs")
    out.mkdir(parents=True, exist_ok=False)
    host_dir = out / "_host"
    host_dir.mkdir()
    executable = host_dir / "NativeSolve.exe"
    config_path = host_dir / "config.json"
    write_json(config_path, config)
    records = [dict(case, native_execution="UNVERIFIED", physical_validation="UNVERIFIED",
                    reproduction="UNVERIFIED") for case in resolved]
    report = dict(start=timestamp(), source_manifest=str(source_manifest), source_manifest_sha256=manifest_hash,
                  host_source_sha256=sha256(host_source), runner_sha256=sha256(Path(__file__)),
                  python=sys.version, analysis=analysis, timeout_s=args.timeout_s, cases=records, complete=False)
    report_path = out / "run_manifest.json"
    write_json(report_path, report)
    try:
        with (host_dir / "compile.log").open("w", encoding="utf-8") as log:
            subprocess.run([str(compiler), "/nologo", "/platform:x86", "/r:Microsoft.CSharp.dll",
                            "/r:System.Web.Extensions.dll", "/r:System.Windows.Forms.dll",
                            f"/out:{executable}", str(host_source)], check=True, stdout=log,
                           stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        for record in records:
            path = Path(record["binary"])
            if sha256(path) != record["sha256"]:
                raise ValueError(f"Input changed before execution: {path}")
            target = out / record["name"]
            target.mkdir()
            record.update(output=str(target), start=timestamp())
            with (target / "host.log").open("w", encoding="utf-8") as log:
                proc = subprocess.Popen([str(executable), str(path), str(target), str(config_path)],
                                        stdout=log, stderr=subprocess.STDOUT,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    code = proc.wait(timeout=args.timeout_s)
                except subprocess.TimeoutExpired:
                    proc.kill()  # Only this host; never terminate the Multisim application.
                    proc.wait()
                    code = "TIMEOUT"
            required = ("ac.json", "transient.json", "native_netlist.txt", "native_schematic.png",
                        "verified.ms14", "execution.json")
            unchanged = sha256(path) == record["sha256"]
            ok = code == 0 and unchanged and all((target / f).is_file() and (target / f).stat().st_size for f in required)
            record.update(finish=timestamp(), exit_code=code, source_unchanged=unchanged,
                          native_execution="PASS" if ok else "FAIL",
                          artifacts={p.name: sha256(p) for p in target.iterdir() if p.is_file()})
            write_json(report_path, report)
            print(f"{record['name']}: {record['native_execution']}", flush=True)
            if not ok:
                raise RuntimeError(f"Native execution failed; inspect {target}")
        report["complete"] = True
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        report["finish"] = timestamp()
        report["source_manifest_unchanged"] = sha256(source_manifest) == manifest_hash
        report["all_sources_unchanged"] = all(sha256(Path(c["binary"])) == c["sha256"] for c in resolved)
        if not report["source_manifest_unchanged"] or not report["all_sources_unchanged"]:
            report["complete"] = False
        write_json(report_path, report)
    if not report["complete"]:
        raise RuntimeError("Source evidence changed during execution")


if __name__ == "__main__":
    main()
