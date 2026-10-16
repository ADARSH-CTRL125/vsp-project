from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from itertools import groupby
from pathlib import Path
from uuid import uuid4
from hashlib import sha256
from secrets import token_urlsafe
from email.message import EmailMessage
import smtplib
import logging
import jwt
import csv
import io
from pwdlib import PasswordHash
from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select, func, inspect, text
from sqlalchemy.orm import Session, selectinload
from .config import settings
from .db import Base, engine, get_db, SessionLocal
from . import models as m, schemas as s

Base.metadata.create_all(bind=engine)
# create_all does not change existing tables; add the optional customer email
# field safely for databases created by earlier project versions.
with engine.begin() as conn:
    columns={c["name"] for c in inspect(conn).get_columns("users")}
    if "email" not in columns:
        conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(254)"))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_unique ON users (email)"))
    order_columns={c["name"] for c in inspect(conn).get_columns("store_orders")}
    if "payment_status" not in order_columns:
        conn.execute(text("ALTER TABLE store_orders ADD COLUMN payment_status VARCHAR(32) NOT NULL DEFAULT 'Not required'"))
app=FastAPI(title="VSP Vehicle Parts Store", version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=False,allow_methods=["GET","POST","PUT","PATCH","DELETE"],allow_headers=["Authorization","Content-Type"])
FRONTEND=Path(__file__).resolve().parent.parent/"frontend"
app.mount("/assets",StaticFiles(directory=FRONTEND/"assets",check_dir=False),name="assets")
@app.get("/",include_in_schema=False)
def storefront(): return FileResponse(FRONTEND/"shop.html")
@app.get("/inventory",include_in_schema=False)
def inventory_page(): return FileResponse(FRONTEND/"index.html")
@app.get("/manage",include_in_schema=False)
def store_management_page(): return FileResponse(FRONTEND/"manage.html")
@app.get("/reset-password",include_in_schema=False)
def reset_password_page(): return FileResponse(FRONTEND/"reset-password.html")
@app.get("/autodukan",include_in_schema=False)
def earlier_preview(): return FileResponse(FRONTEND/"autodukan.html")
hasher=PasswordHash.recommended(); bearer=HTTPBearer()
def current_user(creds:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
    try: payload=jwt.decode(creds.credentials,settings.jwt_secret,algorithms=["HS256"])
    except jwt.PyJWTError: raise HTTPException(401,"Invalid or expired token",headers={"WWW-Authenticate":"Bearer"})
    user=db.get(m.User,int(payload["sub"]))
    if not user or not user.active: raise HTTPException(401,"User inactive or missing")
    return user
def allow(*roles):
    def check(user:m.User=Depends(current_user)):
        if user.role not in roles: raise HTTPException(403,"Insufficient role")
        return user
    return check

def store_product_json(p):
    return {"id":p.id,"name":p.name,"category":p.category,"brand":p.brand,"models":p.models,"description":p.description,"partNumber":p.part_number,"price":float(p.price),"compareAt":float(p.compare_at) if p.compare_at is not None else None,"stock":p.stock,"image":p.image,"active":p.active}

@app.on_event("startup")
def seed_store_catalog():
    catalog=[
      ("air-filter-maruti-swift","Engine Air Filter","Filters","Maruti Suzuki","Swift, Baleno, Dzire","Genuine replacement air filter for clean airflow and efficient engine performance.","13780M74L00",549,699,24,"🧰"),
      ("front-brake-pad-hyundai","Front Brake Pad Set","Brakes","Hyundai","i20, Venue, Grand i10 Nios","Quality brake pads engineered for dependable stopping performance.","58101K0A10",1899,2299,18,"🛞"),
      ("oil-filter-tata","Engine Oil Filter","Filters","Tata","Nexon, Altroz, Tiago","Oil filter element for routine service and engine protection.","481H1000",389,499,35,"⚙️"),
      ("spark-plug-honda","Spark Plug","Electrical","Honda","City, Amaze, Jazz","Reliable ignition performance with a precise OEM-style fit.","12290R1AA01",679,799,20,"⚡"),
      ("clutch-kit-maruti","Clutch Kit","Clutch","Maruti Suzuki","Swift, Dzire, Wagon R","Complete clutch kit for smooth engagement and dependable service.","SE7001",4890,5590,12,"🔩"),
      ("headlamp-toyota","Headlamp Assembly","Lighting","Toyota","Innova Crysta, Fortuner","Replacement headlamp assembly with clear optics and secure fitment.","81110-0K490",7290,8490,8,"💡"),
      ("cabin-filter-kia","Cabin Air Filter","Filters","Kia","Seltos, Sonet, Carens","Cabin filter helps reduce dust and particles entering the cabin.","97133-Q5000",629,799,26,"🌬️"),
      ("shock-absorber-mahindra","Front Shock Absorber","Suspension","Mahindra","Scorpio, XUV500, Bolero","Durable suspension component for a controlled and comfortable ride.","0302AAW00101N",3190,3790,10,"🛠️"),
      ("brake-disc-renault","Front Brake Disc","Brakes","Renault","Kwid, Triber, Kiger","Precision-machined brake disc for consistent braking response.","4020600Q0J",2390,2890,9,"🔘"),
      ("wiper-blade-universal","Wiper Blade Pair","Accessories","Universal","Most hatchbacks and sedans","All-weather front wiper blade pair for a clear view in rain.","VSP-WB-22",449,599,42,"🌧️"),
      ("battery-tata","Car Battery 45Ah","Electrical","Tata","Tiago, Tigor, Altroz","Maintenance-free battery for dependable everyday starts.","45B24LS",5290,5990,7,"🔋"),
      ("engine-mount-hyundai","Engine Mounting","Engine","Hyundai","i10, i20, Grand i10","Replacement engine mounting designed to reduce vibration.","21810-1J000",1590,1890,11,"⚙️"),
      ("demo-air-filter-vw","Air Filter","Filters","Volkswagen","Polo, Taigun","Sample project listing. Confirm exact fitment, part number, stock and price before purchase.","DEMO-VW-AF",650,790,0,"🧰"),
      ("demo-brake-pads-skoda","Front Brake Pad Set","Brakes","Skoda","Slavia, Kushaq","Sample project listing. Confirm exact fitment, part number, stock and price before purchase.","DEMO-SK-BP",1850,2200,0,"🛞"),
      ("demo-cabin-filter-mg","Cabin Air Filter","Filters","MG","Hector, Astor","Sample project listing. Confirm exact fitment, part number, stock and price before purchase.","DEMO-MG-CF",700,850,0,"🌬️"),
      ("demo-oil-filter-nissan","Engine Oil Filter","Filters","Nissan","Magnite, Kicks","Sample project listing. Confirm exact fitment, part number, stock and price before purchase.","DEMO-NS-OF",420,520,0,"⚙️"),
      ("demo-air-filter-vw-taigun","Engine Air Filter","Filters","Volkswagen","Taigun, Virtus","Sample project listing. Verify the exact year, engine and part number before purchase.","DEMO-VW-EAF",720,890,0,"🧰"),
      ("demo-air-filter-skoda","Engine Air Filter","Filters","Skoda","Slavia, Kushaq","Sample project listing. Verify the exact year, engine and part number before purchase.","DEMO-SK-EAF",690,850,0,"🧰"),
      ("demo-brake-pad-mg","Front Brake Pad Set","Brakes","MG","Hector, Astor","Sample project listing. Verify the exact year, trim and part number before purchase.","DEMO-MG-BP",2100,2590,0,"🛞"),
      ("demo-cabin-filter-nissan","Cabin Air Filter","Filters","Nissan","Magnite, Kicks","Sample project listing. Verify the exact year, engine and part number before purchase.","DEMO-NS-CF",550,690,0,"🌬️"),
      ("demo-car-shampoo","Car Wash Shampoo","Car Care","Universal","All makes; check product directions","Sample project care item. Example price only; confirm supplier, ingredients and stock.","DEMO-CARE-01",299,399,0,"🧴"),
      ("demo-microfiber-kit","Microfiber Cleaning Cloth Kit","Car Care","Universal","All makes","Sample project care item. Example price only; confirm supplier and stock.","DEMO-CARE-02",249,349,0,"🧽"),
      ("demo-interior-cleaner","Interior Surface Cleaner","Car Care","Universal","All makes; test on a hidden area first","Sample project care item. Example price only; confirm supplier, ingredients and stock.","DEMO-CARE-03",349,449,0,"✨"),
      ("demo-car-wax","Car Wax Polish","Car Care","Universal","All makes; follow product directions","Sample project care item. Example price only; confirm supplier, ingredients and stock.","DEMO-CARE-04",499,649,0,"🫧"),
      ("demo-floor-mats","All-weather Floor Mat Set","Accessories","Universal","Confirm vehicle shape before purchase","Sample project accessory. Example price only; confirm sizing and stock.","DEMO-ACC-01",1599,1999,0,"🚘"),
      ("demo-phone-holder","Dashboard Phone Holder","Accessories","Universal","Most dashboards; verify mounting compatibility","Sample project accessory. Example price only; confirm supplier and stock.","DEMO-ACC-02",399,599,0,"📱"),
      ("demo-tyre-inflator","12V Tyre Inflator","Accessories","Universal","12V vehicles; confirm electrical rating","Sample project accessory. Example price only; confirm supplier and stock.","DEMO-ACC-03",1799,2299,0,"🛞"),
      ("demo-seat-cover","Universal Seat Cover Set","Accessories","Universal","Confirm seat/airbag compatibility before purchase","Sample project accessory. Example price only; confirm fit and stock.","DEMO-ACC-04",2499,3199,0,"💺")]
    # Additional college-project catalogue rows. These are intentionally marked
    # as demo data with zero stock; never use invented numbers as OEM references.
    vehicle_parts=[
      ("Engine Oil Filter","Filters","⚙️",250, "Filter service item"),
      ("Cabin Air Filter","Filters","🌬️",350, "Cabin filter service item"),
      ("Front Brake Pad Set","Brakes","🛞",1400, "Brake service item"),
      ("Rear Brake Shoe Set","Brakes","🛞",1250, "Brake service item"),
      ("Front Brake Disc","Brakes","🔘",2200, "Brake service item"),
      ("Rear Brake Disc","Brakes","🔘",2100, "Brake service item"),
      ("Clutch Plate","Clutch","🔩",2800, "Clutch service item"),
      ("Clutch Cover Assembly","Clutch","🔩",3300, "Clutch service item"),
      ("Clutch Release Bearing","Clutch","⚙️",750, "Clutch service item"),
      ("Engine Mount","Engine","⚙️",1300, "Engine service item"),
      ("Gearbox Mount","Engine","⚙️",1500, "Engine service item"),
      ("Timing Belt Kit","Engine","🔧",2400, "Engine service item"),
      ("Accessory Drive Belt","Engine","🔧",650, "Engine service item"),
      ("Water Pump","Cooling","💧",1900, "Cooling service item"),
      ("Thermostat Assembly","Cooling","🌡️",900, "Cooling service item"),
      ("Radiator Assembly","Cooling","🌡️",5200, "Cooling service item"),
      ("Radiator Fan Motor","Cooling","🌀",2800, "Cooling service item"),
      ("Alternator Assembly","Electrical","🔋",6500, "Electrical service item"),
      ("Starter Motor","Electrical","⚡",5400, "Electrical service item"),
      ("Ignition Coil","Electrical","⚡",1150, "Electrical service item"),
      ("Spark Plug Set","Electrical","⚡",800, "Electrical service item"),
      ("Front Shock Absorber","Suspension","🛠️",2800, "Suspension service item"),
      ("Rear Shock Absorber","Suspension","🛠️",2500, "Suspension service item"),
      ("Front Strut Mount","Suspension","🛠️",950, "Suspension service item"),
      ("Lower Control Arm","Suspension","🛠️",3200, "Suspension service item"),
      ("Stabilizer Link Pair","Suspension","🛠️",850, "Suspension service item"),
      ("Wheel Bearing Hub","Suspension","🛞",2100, "Suspension service item"),
      ("Tie Rod End Pair","Steering","🔧",1100, "Steering service item"),
      ("Steering Rack Assembly","Steering","🔧",9800, "Steering service item"),
      ("CV Joint Kit","Drivetrain","⚙️",1800, "Drivetrain service item"),
      ("Drive Shaft Assembly","Drivetrain","⚙️",7600, "Drivetrain service item"),
      ("Fuel Pump Module","Fuel System","⛽",4200, "Fuel system service item"),
      ("Fuel Injector","Fuel System","⛽",3600, "Fuel system service item"),
      ("Air Flow Sensor","Electrical","🔌",3900, "Electrical service item"),
      ("Oxygen Sensor","Electrical","🔌",3200, "Electrical service item"),
      ("Headlamp Assembly","Lighting","💡",5800, "Lighting service item"),
      ("Tail Lamp Assembly","Lighting","💡",3600, "Lighting service item"),
      ("Wiper Motor Assembly","Electrical","🌧️",2400, "Electrical service item"),
      ("Door Mirror Assembly","Body Parts","🚘",2900, "Body service item"),
      ("Power Window Regulator","Body Parts","🚘",1900, "Body service item")]
    brand_models={"Maruti Suzuki":"Swift, Baleno, Dzire, Wagon R","Hyundai":"i20, Creta, Venue, Grand i10 Nios","Tata":"Nexon, Altroz, Tiago, Punch","Honda":"City, Amaze, Elevate, Jazz","Mahindra":"Scorpio, XUV700, Bolero, Thar","Toyota":"Innova, Fortuner, Glanza, Urban Cruiser","Kia":"Seltos, Sonet, Carens","Renault":"Kwid, Triber, Kiger","Volkswagen":"Polo, Taigun, Virtus","Skoda":"Slavia, Kushaq, Rapid","MG":"Hector, Astor, Comet EV","Nissan":"Magnite, Kicks, Sunny"}
    brand_codes={"Maruti Suzuki":"MS","Hyundai":"HY","Tata":"TA","Honda":"HO","Mahindra":"MH","Toyota":"TY","Kia":"KI","Renault":"RE","Volkswagen":"VW","Skoda":"SK","MG":"MG","Nissan":"NI"}
    for brand, models in brand_models.items():
      brand_code=brand_codes[brand]
      for index,(name,category,icon,price,kind) in enumerate(vehicle_parts,1):
        slug="".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-").replace("--","-")
        catalog.append((f"demo-{brand_code.lower()}-{index:02d}-{slug}",name,category,brand,models,
          f"Sample project listing for {brand}. {kind}; exact year, model, engine, trim, part number and fitment are not verified. Example price only; confirm with an authorized supplier.",
          f"DEMO-{brand_code}-{index:02d}",price,int(price*1.18),0,icon))
    nut_bolt_types=[
      ("Hex Head Bolt M6 × 1.0 × 20 mm","🔩"),("Hex Head Bolt M8 × 1.25 × 25 mm","🔩"),("Hex Head Bolt M10 × 1.5 × 30 mm","🔩"),("Hex Head Bolt M12 × 1.75 × 40 mm","🔩"),
      ("Flange Bolt M6 × 1.0 × 16 mm","🔩"),("Flange Bolt M8 × 1.25 × 20 mm","🔩"),("Flange Bolt M10 × 1.5 × 25 mm","🔩"),("Flange Bolt M12 × 1.75 × 35 mm","🔩"),
      ("Hex Nut M6 × 1.0","⚙️"),("Hex Nut M8 × 1.25","⚙️"),("Hex Nut M10 × 1.5","⚙️"),("Hex Nut M12 × 1.75","⚙️"),
      ("Nyloc Lock Nut M6","⚙️"),("Nyloc Lock Nut M8","⚙️"),("Nyloc Lock Nut M10","⚙️"),("Nyloc Lock Nut M12","⚙️"),
      ("Wheel Lug Nut M12 × 1.5","🛞"),("Wheel Lug Nut M12 × 1.25","🛞"),("Wheel Stud M12 × 1.5","🛞"),("Wheel Stud M12 × 1.25","🛞"),
      ("Oil Drain Plug M12 × 1.5","🛢️"),("Oil Drain Plug M14 × 1.5","🛢️"),("Oil Drain Plug M16 × 1.5","🛢️"),("Oil Drain Plug Washer Kit","🛢️"),
      ("Sump Bolt Kit","🔩"),("Cylinder Head Bolt Set","🔩"),("Connecting Rod Bolt Set","🔩"),("Flywheel Bolt Set","🔩"),
      ("Exhaust Manifold Stud Kit","🔩"),("Exhaust Flange Nut Set","⚙️"),("Brake Caliper Bolt Set","🛞"),("Brake Disc Retaining Screw Set","🔩"),
      ("Suspension Control Arm Bolt Set","🔩"),("Strut Mount Nut Set","⚙️"),("Engine Mount Bolt Set","🔩"),("Gearbox Mount Bolt Set","🔩"),
      ("Bumper Retainer Clip & Screw Kit","🚘"),("Underbody Shield Clip Kit","🚘"),("License Plate Screw Kit","🔩"),("Mixed Metric Automotive Fastener Kit","🧰")]
    for index,(name,icon) in enumerate(nut_bolt_types,1):
      price=49+index*11
      catalog.append((f"demo-fastener-{index:02d}",name,"Nut & Bolt","Universal","Dimensions and strength grade must match vehicle; fitment is not verified",
        "Sample fastener listing only. Verify thread pitch, length, material, strength grade and OEM specification before installation. Not a substitute for a verified vehicle fitment.",
        f"DEMO-FST-{index:02d}",price,int(price*1.2),0,icon))
    care_products=[
      ("Car Perfume Vent Clip","🌸",199),("Car Perfume Gel Can","🌸",249),("Car Perfume Hanging Diffuser","🌸",299),("Car Perfume Spray","🌸",349),
      ("Snow Foam Car Wash Shampoo","🫧",399),("pH-Neutral Car Foam Concentrate","🫧",549),("Foam Cannon Wash Kit","🚿",1499),("Foam Sprayer","🚿",799),
      ("Tyre Foam Cleaner","✨",299),("Dashboard Polish & Protectant","✨",349),("Glass Cleaner Spray","🪟",249),("All-purpose Interior Cleaner","🧽",349),
      ("Upholstery & Fabric Cleaner","🧴",399),("Leather Cleaner & Conditioner","🪑",599),("Waterless Car Wash Spray","💧",449),("Quick Detailer Spray","✨",499),
      ("Ceramic Spray Coating","🛡️",899),("Bug & Tar Remover","🧴",399),("Wheel & Rim Cleaner","🛞",399),("Engine Bay Cleaner","⚙️",449),
      ("Microfiber Drying Towel","🧽",299),("Detailing Brush Set","🖌️",249),("Car Wash Mitt","🧤",199),("Interior Detailing Brush Kit","🖌️",349)]
    for index,(name,icon,price) in enumerate(care_products,1):
      catalog.append((f"demo-care-extra-{index:02d}",name,"Car Care","Universal","Check label for surface compatibility",
        "Sample project car-care listing. Verify ingredients, surface compatibility, safety instructions, supplier, price and availability before sale or use.",
        f"DEMO-CARE-X{index:02d}",price,int(price*1.2),0,icon))
    with SessionLocal() as db:
      for row in catalog:
        if not db.get(m.StoreProduct,row[0]):
          db.add(m.StoreProduct(id=row[0],name=row[1],category=row[2],brand=row[3],models=row[4],description=row[5],part_number=row[6],price=Decimal(str(row[7])),compare_at=Decimal(str(row[8])),stock=row[9],image=row[10]))
      db.commit()

@app.get("/api/store/products")
def store_products(q:str|None=None,category:str|None=None,brand:str|None=None,vehicle:str|None=None,db:Session=Depends(get_db)):
    stmt=select(m.StoreProduct).where(m.StoreProduct.active.is_(True)).order_by(m.StoreProduct.name)
    if category: stmt=stmt.where(m.StoreProduct.category==category)
    if brand: stmt=stmt.where(m.StoreProduct.brand==brand)
    rows=db.scalars(stmt).all()
    if q:
      term=q.casefold();rows=[p for p in rows if term in " ".join([p.name,p.brand,p.category,p.models,p.part_number]).casefold()]
    if vehicle:
      term=vehicle.casefold();rows=[p for p in rows if term in p.models.casefold() or "universal" in p.models.casefold()]
    return [store_product_json(p) for p in rows]

@app.get("/api/admin/store/products")
def admin_store_products(db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    return [store_product_json(p) for p in db.scalars(select(m.StoreProduct).order_by(m.StoreProduct.name)).all()]

@app.get("/api/store/products/{pid}")
def store_product(pid:str,db:Session=Depends(get_db)):
    p=db.get(m.StoreProduct,pid)
    if not p or not p.active:raise HTTPException(404,"Product not found")
    return store_product_json(p)

@app.get("/api/store/payment-qr")
def store_payment_qr():
    qr_path=FRONTEND/"assets"/"payment-qr.png"
    return {"imageUrl":f"/assets/payment-qr.png?v={qr_path.stat().st_mtime_ns}" if qr_path.is_file() else None}

@app.post("/api/admin/store/payment-qr")
async def upload_payment_qr(file:UploadFile=File(...),u:m.User=Depends(allow("Admin"))):
    if file.content_type!="image/png":raise HTTPException(415,"Upload a PNG UPI QR image")
    content=await file.read(5_000_001)
    if len(content)>5_000_000:raise HTTPException(413,"UPI QR image must be smaller than 5 MB")
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):raise HTTPException(422,"The uploaded file is not a valid PNG image")
    path=FRONTEND/"assets"/"payment-qr.png";path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    return {"imageUrl":f"/assets/payment-qr.png?v={path.stat().st_mtime_ns}"}

@app.get("/api/store/brands")
def store_brands(db:Session=Depends(get_db)):
    return db.scalars(select(m.StoreProduct.brand).where(m.StoreProduct.active.is_(True)).distinct().order_by(m.StoreProduct.brand)).all()

@app.get("/api/store/categories")
def store_categories(db:Session=Depends(get_db)):
    return db.scalars(select(m.StoreProduct.category).where(m.StoreProduct.active.is_(True)).distinct().order_by(m.StoreProduct.category)).all()

@app.post("/api/store/products",status_code=201)
def create_store_product(d:s.StoreProductIn,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    pid="vsp-"+uuid4().hex[:12]
    p=m.StoreProduct(id=pid,name=d.name,category=d.category,brand=d.brand,models=d.models,description=d.description,part_number=d.partNumber,price=d.price,compare_at=d.compareAt,stock=d.stock,image=d.image,active=d.active)
    db.add(p);db.commit();db.refresh(p);return store_product_json(p)

@app.put("/api/store/products/{pid}")
def update_store_product(pid:str,d:s.StoreProductIn,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    p=db.get(m.StoreProduct,pid)
    if not p:raise HTTPException(404,"Product not found")
    for key,value in d.model_dump().items():setattr(p,{"partNumber":"part_number","compareAt":"compare_at"}.get(key,key),value)
    db.commit();db.refresh(p);return store_product_json(p)

@app.post("/api/admin/store/products/import")
async def import_store_products(file:UploadFile=File(...),db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    if not file.filename.lower().endswith(".csv"):raise HTTPException(415,"Upload a CSV export file")
    content=await file.read(10_000_001)
    if len(content)>10_000_000:raise HTTPException(413,"CSV must be smaller than 10 MB")
    try: text=content.decode("utf-8-sig")
    except UnicodeDecodeError:raise HTTPException(422,"CSV must use UTF-8 encoding")
    reader=csv.DictReader(io.StringIO(text))
    required={"id","name","category","brand","price","stock"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):raise HTTPException(422,"CSV must include id, name, category, brand, price and stock columns")
    created=updated=0
    try:
      for row_no,row in enumerate(reader,start=2):
        if row_no>10002:raise HTTPException(413,"CSV is limited to 10,000 products")
        pid=(row.get("id") or "").strip()
        if not pid:raise HTTPException(422,f"Row {row_no}: id is required")
        values=s.StoreProductIn(name=(row.get("name") or "").strip(),category=(row.get("category") or "").strip(),brand=(row.get("brand") or "").strip(),models=(row.get("models") or "All models").strip(),description=(row.get("description") or "").strip(),partNumber=(row.get("partNumber") or "").strip(),price=(row.get("price") or "").strip(),compareAt=(row.get("compareAt") or "").strip() or None,stock=(row.get("stock") or "0").strip(),image=(row.get("image") or "").strip(),active=(row.get("active") or "true").strip().lower() not in {"false","0","no","hidden"})
        product=db.get(m.StoreProduct,pid)
        if product:
          for key,value in values.model_dump().items():setattr(product,{"partNumber":"part_number","compareAt":"compare_at"}.get(key,key),value)
          updated+=1
        else:
          product=m.StoreProduct(id=pid,name=values.name,category=values.category,brand=values.brand,models=values.models,description=values.description,part_number=values.partNumber,price=values.price,compare_at=values.compareAt,stock=values.stock,image=values.image,active=values.active);db.add(product);created+=1
      db.commit()
    except HTTPException:
      db.rollback();raise
    except Exception as exc:
      db.rollback();raise HTTPException(422,f"CSV import stopped; check row data ({str(exc)[:180]})")
    return {"created":created,"updated":updated,"total":created+updated}

@app.post("/api/store/orders",status_code=201)
def create_store_order(d:s.StoreOrderIn,db:Session=Depends(get_db)):
    if not d.phone.replace("+","").replace(" ","").replace("-","").isdigit():raise HTTPException(422,"Enter a valid contact number")
    quantities={}
    if d.paymentMode=="UPI" and not (FRONTEND/"assets"/"payment-qr.png").is_file():
      raise HTTPException(409,"UPI is not configured yet. Please choose Cash on Delivery or contact VSP.")
    for line in d.items: quantities[line.productId]=quantities.get(line.productId,0)+line.qty
    products={}
    for pid in quantities:
      p=db.scalar(select(m.StoreProduct).where(m.StoreProduct.id==pid).with_for_update())
      if not p or not p.active:raise HTTPException(404,f"Product {pid} is unavailable")
      products[pid]=p
    if d.paymentMode=="Cash on Delivery":
      for pid,qty in quantities.items():
        p=products[pid]
        if p.stock<qty:raise HTTPException(409,f"Only {p.stock} left for {p.name}")
    order_id="VSP"+uuid4().hex[:10].upper();total=Decimal("0")
    payment_status="Not required" if d.paymentMode=="Cash on Delivery" else "Awaiting verification"
    order=m.StoreOrder(id=order_id,customer_name=d.name,phone=d.phone,email=d.email,address=d.address,city=d.city,state=d.state,pincode=d.pincode,payment_mode=d.paymentMode,payment_status=payment_status,status="Received",total=Decimal("0"))
    for pid,qty in quantities.items():
      p=products[pid]
      if d.paymentMode=="Cash on Delivery":p.stock-=qty
      total+=p.price*qty
      order.items.append(m.StoreOrderItem(product_id=p.id,product_name=p.name,part_number=p.part_number,qty=qty,unit_price=p.price))
    order.total=total;db.add(order);db.commit();db.refresh(order)
    return {"id":order.id,"status":order.status,"paymentStatus":order.payment_status,"paymentMode":order.payment_mode,"total":float(order.total),"message":"Your order has been received. Our team will contact you to confirm delivery."}

@app.get("/api/store/orders")
def list_store_orders(db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    rows=db.scalars(select(m.StoreOrder).options(selectinload(m.StoreOrder.items)).order_by(m.StoreOrder.created_at.desc())).all()
    return [{"id":o.id,"name":o.customer_name,"phone":o.phone,"email":o.email,"address":o.address,"city":o.city,"state":o.state,"pincode":o.pincode,"paymentMode":o.payment_mode,"paymentStatus":o.payment_status,"status":o.status,"total":float(o.total),"createdAt":o.created_at.isoformat(),"items":[{"productId":i.product_id,"name":i.product_name,"partNumber":i.part_number,"qty":i.qty,"unitPrice":float(i.unit_price)} for i in o.items]} for o in rows]

@app.post("/api/store/orders/track")
def track_store_order(d:s.StoreOrderTrackIn,db:Session=Depends(get_db)):
    order=db.scalar(select(m.StoreOrder).options(selectinload(m.StoreOrder.items)).where(m.StoreOrder.id==d.orderId.strip().upper()))
    digits=lambda value:"".join(ch for ch in value if ch.isdigit())
    if not order or digits(order.phone)!=digits(d.phone):raise HTTPException(404,"Order number or mobile number was not found")
    return {"id":order.id,"status":order.status,"paymentMode":order.payment_mode,"paymentStatus":order.payment_status,"total":float(order.total),"createdAt":order.created_at.isoformat(),"items":[{"name":i.product_name,"qty":i.qty,"unitPrice":float(i.unit_price)} for i in order.items]}

@app.patch("/api/store/orders/{oid}/payment")
def set_store_order_payment(oid:str,status_value:str=Query(alias="status"),db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    if status_value not in {"Paid","Failed"}:raise HTTPException(422,"Payment status must be Paid or Failed")
    order=db.scalar(select(m.StoreOrder).options(selectinload(m.StoreOrder.items)).where(m.StoreOrder.id==oid))
    if not order:raise HTTPException(404,"Order not found")
    if order.payment_mode!="UPI":raise HTTPException(409,"Only UPI orders have a payment verification status")
    if order.payment_status=="Paid":
      if status_value=="Paid":return {"id":order.id,"paymentStatus":order.payment_status}
      raise HTTPException(409,"A verified payment cannot be changed to Failed")
    if status_value=="Paid":
      products={}
      for line in order.items:
        product=db.scalar(select(m.StoreProduct).where(m.StoreProduct.id==line.product_id).with_for_update())
        if not product or not product.active:raise HTTPException(409,f"Part {line.product_name} is no longer available")
        products[line.product_id]=product
      for line in order.items:
        product=products[line.product_id]
        if product.stock<line.qty:raise HTTPException(409,f"Insufficient stock for {product.name}; only {product.stock} remain")
      for line in order.items:products[line.product_id].stock-=line.qty
    order.payment_status=status_value if status_value=="Paid" else "Failed"
    db.commit();return {"id":order.id,"paymentStatus":order.payment_status}

@app.patch("/api/store/orders/{oid}/status")
def set_store_order_status(oid:str,status_value:str=Query(alias="status"),db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    if status_value not in {"Received","Confirmed","Packed","Shipped","Delivered","Cancelled"}:raise HTTPException(422,"Invalid order status")
    order=db.get(m.StoreOrder,oid)
    if not order:raise HTTPException(404,"Order not found")
    if status_value in {"Confirmed","Packed","Shipped","Delivered"} and order.payment_mode=="UPI" and order.payment_status!="Paid":raise HTTPException(409,"Verify UPI payment before moving this order forward")
    order.status=status_value;db.commit();return {"id":order.id,"status":order.status}

@app.post("/api/store/leads",status_code=201)
def create_store_lead(d:s.StoreLeadIn,db:Session=Depends(get_db)):
    lead=m.StoreLead(name=d.name,phone=d.phone,vehicle=d.vehicle,part_query=d.partQuery,note=d.note);db.add(lead);db.commit();db.refresh(lead)
    return {"id":lead.id,"message":"Thanks. Our parts team will contact you shortly."}

@app.get("/api/store/leads")
def list_store_leads(db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    return [{"id":x.id,"name":x.name,"phone":x.phone,"vehicle":x.vehicle,"partQuery":x.part_query,"note":x.note,"createdAt":x.created_at.isoformat()} for x in db.scalars(select(m.StoreLead).order_by(m.StoreLead.created_at.desc())).all()]
def next_id(db, model, prefix):
    # IDs are readable legacy-compatible labels; PostgreSQL advisory lock serializes allocation.
    if db.bind.dialect.name=="postgresql": db.execute(select(func.pg_advisory_xact_lock(71002)))
    ids=db.scalars(select(model.id)).all(); n=max([int(x[len(prefix):]) for x in ids if x.startswith(prefix) and x[len(prefix):].isdigit()] or [0])+1
    return f"{prefix}{n:03d}"
def part_json(p): return {"id":p.id,"name":p.name,"category":p.category,"brand":p.brand,"models":p.models,"qty":p.qty,"reorder":p.reorder,"purchasePrice":float(p.purchase_price),"sellingPrice":float(p.selling_price),"supplierId":p.supplier_id}
def party_json(x, supplier=False):
    d={"id":x.id,"name":x.name,"phone":x.phone,"email":x.email,"address":x.address}
    if supplier:d["contact"]=x.contact
    return d
def tx_json(x, sale=False):
    d={"id":x.id,"date":x.date.isoformat(),"total":float(x.total),"items":[{"partId":i.part_id,"partName":i.part_name,"qty":i.qty,"unitPrice":float(i.unit_price)} for i in x.items]}
    if sale:d.update(customerId=x.customer_id,customerName=x.customer_name,paymentMode=x.payment_mode)
    else:d.update(supplierId=x.supplier_id,supplierName=x.supplier_name)
    return d

@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/api/auth/login")
def login(data:s.LoginIn,db:Session=Depends(get_db)):
    identity=data.username.strip()
    u=db.scalar(select(m.User).where(func.lower(m.User.username)==identity.casefold()))
    if not u and "@" in identity:u=db.scalar(select(m.User).where(func.lower(m.User.email)==identity.casefold()))
    if not u or not u.active or not hasher.verify(data.password,u.password_hash): raise HTTPException(401,"Invalid username or password")
    token=jwt.encode({"sub":str(u.id),"role":u.role,"exp":datetime.now(timezone.utc)+timedelta(minutes=settings.jwt_minutes)},settings.jwt_secret,algorithm="HS256")
    return {"access_token":token,"token_type":"bearer","user":{"id":u.id,"username":u.username,"fullName":u.full_name,"email":u.email,"role":u.role}}
@app.post("/api/auth/register",status_code=201)
def register(data:s.RegisterIn,db:Session=Depends(get_db)):
    username=data.username.strip();email=data.email.strip().casefold()
    if "@" not in email or "." not in email.rsplit("@",1)[-1]:raise HTTPException(422,"Enter a valid email address")
    if db.scalar(select(m.User.id).where(func.lower(m.User.username)==username.casefold())):raise HTTPException(409,"That username is already taken")
    if db.scalar(select(m.User.id).where(func.lower(m.User.email)==email)):raise HTTPException(409,"That email is already registered")
    user=m.User(username=username,email=email,full_name=data.full_name.strip(),password_hash=hasher.hash(data.password),role="Viewer",active=True)
    db.add(user);db.commit();db.refresh(user)
    token=jwt.encode({"sub":str(user.id),"role":user.role,"exp":datetime.now(timezone.utc)+timedelta(minutes=settings.jwt_minutes)},settings.jwt_secret,algorithm="HS256")
    return {"access_token":token,"token_type":"bearer","user":{"id":user.id,"username":user.username,"fullName":user.full_name,"email":user.email,"role":user.role}}
@app.post("/api/auth/forgot-password")
def forgot_password(data:s.ForgotPasswordIn,db:Session=Depends(get_db)):
    email=data.email.strip().casefold();user=db.scalar(select(m.User).where(func.lower(m.User.email)==email,m.User.active.is_(True)))
    if user:
        raw=token_urlsafe(32);now=datetime.now(timezone.utc)
        for old in db.scalars(select(m.PasswordResetToken).where(m.PasswordResetToken.user_id==user.id,m.PasswordResetToken.used_at.is_(None))).all():old.used_at=now
        db.add(m.PasswordResetToken(user_id=user.id,token_hash=sha256(raw.encode()).hexdigest(),expires_at=now+timedelta(minutes=30)))
        db.commit()
        if settings.smtp_host and settings.email_from:
            msg=EmailMessage();msg["Subject"]="Reset your VSP account password";msg["From"]=settings.email_from;msg["To"]=email
            msg.set_content(f"Use this one-time link within 30 minutes to reset your VSP password:\n\n{settings.public_base_url.rstrip('/')}/reset-password?token={raw}\n\nIf you did not request this, ignore this email.")
            try:
                with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=10) as server:
                    server.starttls()
                    if settings.smtp_user:server.login(settings.smtp_user,settings.smtp_password)
                    server.send_message(msg)
            except Exception:
                logging.exception("VSP password reset email could not be delivered")
    return {"message":"If an active account uses that email, a password reset link will be sent."}
@app.post("/api/auth/reset-password")
def reset_password(data:s.ResetPasswordIn,db:Session=Depends(get_db)):
    digest=sha256(data.token.encode()).hexdigest();record=db.scalar(select(m.PasswordResetToken).where(m.PasswordResetToken.token_hash==digest).with_for_update())
    now=datetime.now(timezone.utc)
    if not record or record.used_at or record.expires_at.replace(tzinfo=timezone.utc)<now:raise HTTPException(400,"This reset link is invalid or expired. Request a new one.")
    user=db.get(m.User,record.user_id)
    if not user or not user.active:raise HTTPException(400,"This reset link is invalid or expired. Request a new one.")
    user.password_hash=hasher.hash(data.password);record.used_at=now;db.commit()
    return {"message":"Password updated. You can now sign in with your new password."}
@app.get("/api/auth/me")
def me(u:m.User=Depends(current_user)): return {"id":u.id,"username":u.username,"fullName":u.full_name,"email":u.email,"role":u.role}
@app.post("/api/users",response_model=s.UserOut)
def create_user(d:s.UserCreate,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    if db.scalar(select(m.User).where(m.User.username==d.username)):raise HTTPException(409,"Username exists")
    email=d.email.strip().casefold() if d.email else None
    if email and ("@" not in email or db.scalar(select(m.User.id).where(func.lower(m.User.email)==email))):raise HTTPException(409,"Email is invalid or already registered")
    x=m.User(username=d.username,full_name=d.full_name,email=email,password_hash=hasher.hash(d.password),role=d.role,active=True);db.add(x);db.commit();db.refresh(x);return x
@app.get("/api/users",response_model=list[s.UserOut])
def users(db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):return db.scalars(select(m.User).order_by(m.User.id)).all()
@app.patch("/api/users/{uid}/active")
def activate(uid:int,active:bool,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    x=db.get(m.User,uid)
    if not x:raise HTTPException(404,"User not found")
    x.active=active;db.commit();return {"ok":True}

@app.get("/api/parts")
def parts(db:Session=Depends(get_db),u:m.User=Depends(current_user)):return [part_json(x) for x in db.scalars(select(m.Part).order_by(m.Part.id)).all()]
@app.post("/api/parts",status_code=201)
def add_part(d:s.PartIn,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin","Staff"))):
    x=m.Part(id=next_id(db,m.Part,"P"),name=d.name,category=d.category,brand=d.brand,models=d.models,qty=d.qty,reorder=d.reorder,purchase_price=d.purchasePrice,selling_price=d.sellingPrice,supplier_id=d.supplierId);db.add(x);db.commit();return part_json(x)
@app.put("/api/parts/{pid}")
def update_part(pid:str,d:s.PartIn,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin","Staff"))):
    x=db.get(m.Part,pid)
    if not x:raise HTTPException(404,"Part not found")
    for k,v in d.model_dump().items():setattr(x, {"purchasePrice":"purchase_price","sellingPrice":"selling_price","supplierId":"supplier_id"}.get(k,k),v)
    db.commit();return part_json(x)
@app.delete("/api/parts/{pid}",status_code=204)
def delete_part(pid:str,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
    x=db.get(m.Part,pid)
    if not x:raise HTTPException(404,"Part not found")
    try:db.delete(x);db.commit()
    except Exception:db.rollback();raise HTTPException(409,"Part is referenced by transaction history")

def party_routes(model, label):
    def list_all(db:Session=Depends(get_db),u:m.User=Depends(current_user)):return [party_json(x,label=="supplier") for x in db.scalars(select(model).order_by(model.id)).all()]
    return list_all
app.get("/api/suppliers")(party_routes(m.Supplier,"supplier")); app.get("/api/customers")(party_routes(m.Customer,"customer"))
def add_party(model,prefix,body,supplier=False):
    def handler(d:body,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin","Staff"))):
        x=model(id=next_id(db,model,prefix),**d.model_dump());db.add(x);db.commit();return party_json(x,supplier)
    return handler
def update_party(model,body,supplier=False):
    def handler(pid:str,d:body,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin","Staff"))):
        x=db.get(model,pid)
        if not x:raise HTTPException(404,"Record not found")
        for k,v in d.model_dump().items():setattr(x,k,v)
        db.commit();return party_json(x,supplier)
    return handler
def delete_party(model):
    def handler(pid:str,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin"))):
        x=db.get(model,pid)
        if not x:raise HTTPException(404,"Record not found")
        try:db.delete(x);db.commit()
        except Exception:db.rollback();raise HTTPException(409,"Record is used by transaction history")
    return handler
for path,model,prefix,body,supplier in [("suppliers",m.Supplier,"S",s.SupplierIn,True),("customers",m.Customer,"C",s.CustomerIn,False)]:
    app.post(f"/api/{path}",status_code=201)(add_party(model,prefix,body,supplier));app.put(f"/api/{path}/{{pid}}") (update_party(model,body,supplier));app.delete(f"/api/{path}/{{pid}}",status_code=204)(delete_party(model))

def record_purchase(data,db,user):
    supplier=db.get(m.Supplier,data.supplierId)
    if not supplier:raise HTTPException(404,"Supplier not found")
    # Combine duplicate part rows, lock stock rows and commit header/items/stock as one transaction.
    lines={k:list(v) for k,v in groupby(sorted(data.items,key=lambda i:i.partId),key=lambda i:i.partId)}
    if db.bind.dialect.name=="postgresql": db.execute(select(func.pg_advisory_xact_lock(71003)))
    tx=m.Purchase(id=next_id(db,m.Purchase,"PU"),supplier_id=supplier.id,supplier_name=supplier.name,total=Decimal("0"),created_by=user.id)
    total=Decimal("0")
    for pid,rows in lines.items():
        p=db.scalar(select(m.Part).where(m.Part.id==pid).with_for_update())
        if not p:raise HTTPException(404,f"Part {pid} not found")
        qty=sum(i.qty for i in rows);price=rows[-1].unitPrice;total+=qty*price;p.qty+=qty;p.purchase_price=price
        tx.items.append(m.PurchaseItem(part_id=pid,part_name=p.name,qty=qty,unit_price=price))
    tx.total=total;db.add(tx);db.commit();db.refresh(tx);return tx_json(tx)
@app.post("/api/purchases",status_code=201)
def purchase(d:s.PurchaseIn,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin","Staff"))):
    try:return record_purchase(d,db,u)
    except Exception:db.rollback();raise
@app.get("/api/purchases")
def purchases(db:Session=Depends(get_db),u:m.User=Depends(current_user)):return [tx_json(x) for x in db.scalars(select(m.Purchase).options(selectinload(m.Purchase.items)).order_by(m.Purchase.date,m.Purchase.id)).all()]
@app.post("/api/sales",status_code=201)
def sale(d:s.SaleIn,db:Session=Depends(get_db),u:m.User=Depends(allow("Admin","Staff"))):
    try:
        customer=db.get(m.Customer,d.customerId)
        if not customer:raise HTTPException(404,"Customer not found")
        if db.bind.dialect.name=="postgresql": db.execute(select(func.pg_advisory_xact_lock(71004)))
        rows={k:list(v) for k,v in groupby(sorted(d.items,key=lambda i:i.partId),key=lambda i:i.partId)}
        tx=m.Sale(id=next_id(db,m.Sale,"SL"),customer_id=customer.id,customer_name=customer.name,payment_mode=d.paymentMode,total=Decimal("0"),created_by=u.id)
        total=Decimal("0")
        for pid,items in rows.items():
            p=db.scalar(select(m.Part).where(m.Part.id==pid).with_for_update())
            if not p:raise HTTPException(404,f"Part {pid} not found")
            qty=sum(i.qty for i in items)
            if p.qty<qty:raise HTTPException(409,f"Insufficient stock for {p.name}; available {p.qty}")
            price=items[-1].unitPrice;total+=qty*price;p.qty-=qty
            tx.items.append(m.SaleItem(part_id=pid,part_name=p.name,qty=qty,unit_price=price))
        tx.total=total;db.add(tx);db.commit();db.refresh(tx);return tx_json(tx,True)
    except Exception:db.rollback();raise
@app.get("/api/sales")
def sales(db:Session=Depends(get_db),u:m.User=Depends(current_user)):return [tx_json(x,True) for x in db.scalars(select(m.Sale).options(selectinload(m.Sale.items)).order_by(m.Sale.date,m.Sale.id)).all()]
@app.on_event("startup")
def bootstrap_admin_from_env():
    import os
    username=os.getenv("ADMIN_USERNAME","").strip()
    password=os.getenv("ADMIN_PASSWORD","")
    full_name=os.getenv("ADMIN_FULL_NAME","Store Admin").strip() or "Store Admin"
    if not username or not password:
        return
    with SessionLocal() as db:
        existing=db.scalar(select(m.User).where(func.lower(m.User.username)==username.casefold()))
        if existing:
            return
        db.add(m.User(username=username,full_name=full_name,password_hash=PasswordHash.recommended().hash(password),role="Admin",active=True))
        db.commit()
