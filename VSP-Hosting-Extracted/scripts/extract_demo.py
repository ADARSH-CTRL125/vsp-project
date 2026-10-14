import json,re,sys
from pathlib import Path
html=Path(sys.argv[1] if len(sys.argv)>1 else "frontend/index.html").read_text(encoding="utf-8")
def array(pattern):
 m=re.search(pattern,html,re.S)
 if not m: raise SystemExit("Fixture array not found in supplied HTML")
 raw=m.group(1)
 raw=re.sub(r"([{,]\s*)([A-Za-z_$][\w$]*)\s*:",r'\1"\2":',raw)
 raw=re.sub(r"'([^']*)'",lambda m:json.dumps(m.group(1)),raw)
 return json.loads(raw)
parts=array(r"const PARTS100\s*=\s*(\[.*?\]);")
suppliers=array(r"if\(!this\.g\('suppliers'\)\) this\.s\('suppliers',\s*(\[.*?\])\);\s*if\(!this\.g\('customers'\)\)")
customers=array(r"if\(!this\.g\('customers'\)\) this\.s\('customers',\s*(\[.*?\])\);\s*if\(!this\.g\('purchases'\)\)")
Path("scripts/demo_data.json").write_text(json.dumps({"parts":parts,"suppliers":suppliers,"customers":customers},indent=2),encoding="utf-8")
print(f"Extracted {len(parts)} parts, {len(suppliers)} suppliers, {len(customers)} customers")
