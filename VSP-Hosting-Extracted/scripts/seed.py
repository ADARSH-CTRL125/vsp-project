import json
from pathlib import Path
from app.db import SessionLocal
from app.models import Part,Supplier,Customer
d=json.loads(Path("scripts/demo_data.json").read_text(encoding="utf-8"))
with SessionLocal() as db:
 for row in d["suppliers"]:
  if not db.get(Supplier,row["id"]): db.add(Supplier(**row))
 for row in d["customers"]:
  if not db.get(Customer,row["id"]): db.add(Customer(**row))
 db.flush()
 for x in d["parts"]:
  if not db.get(Part,x["id"]): db.add(Part(id=x["id"],name=x["name"],category=x["category"],brand=x["brand"],models=x["models"],qty=x["qty"],reorder=x["reorder"],purchase_price=x["purchasePrice"],selling_price=x["sellingPrice"],supplier_id=x.get("supplierId")))
 db.commit()
print("Seed complete; existing IDs untouched; no users/passwords imported.")
