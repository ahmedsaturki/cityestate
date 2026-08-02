"""
Seed Data Script — بيانات تجريبية (Premium Focus)
=================================================
Populates the database with PREMIUM Egyptian real estate data
for El Sadat City (مدينة السادات).

FOCUS: Luxury compounds, villas, commercial hubs, industrial investment.
NO social housing or budget properties.

Run: python scripts/seed_data.py
"""

import sys
import random
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.ingester import Base, Lead
from src.database.models import Property, ClientRequest


# ---------------------------------------------------------------------------
# El Sadat City Premium Areas
# ---------------------------------------------------------------------------
SADAT_AREAS = [
    # Premium Residential
    ("المنطقة 7 الشريط المميز", "مدينة السادات", 25000),
    ("المنطقة 9 الشريط المميز", "مدينة السادات", 22000),
    ("المنطقة 15 الشريط المميز", "مدينة السادات", 20000),
    ("الفردوس", "مدينة السادات", 18000),
    ("الكوثر", "مدينة السادات", 19000),
    ("النخيل", "مدينة السادات", 21000),
    ("الروضة", "مدينة السادات", 20000),
    ("النرجس", "مدينة السادات", 17000),
    ("الريحان", "مدينة السادات", 16000),
    # Industrial/Commercial
    ("المنطقة الصناعية الأولى", "مدينة السادات", 8000),
    ("المنطقة الصناعية الثانية", "مدينة السادات", 9000),
    ("المنطقة الصناعية الثالثة", "مدينة السادات", 10000),
    ("المنطقة الصناعية الرابعة", "city Sadat", 11000),
    ("المنطقة الصناعية الخامسة", "مدينة السادات", 12000),
    ("المنطقة الصناعية السادسة", "مدينة السادات", 13000),
    ("المنطقة الصناعية السابعة", "مدينة السادات", 14000),
    ("Polaris Parks", "مدينة السادات", 18000),
]


# ---------------------------------------------------------------------------
# Premium Developers
# ---------------------------------------------------------------------------
PREMIUM_DEVELOPERS = [
    "شركة السادات للتطوير العقاري",
    "شركة جيديكس للتطوير العقاري",
    "شركة النيل للمكاتب",
    "شركة النخيل للتطوير",
    "شركة الفردوس العقارية",
    "Polaris Development",
    "شركة الكوثر العقارية",
    "شركة الروضة للتطوير",
    "شركة الشريط المميز",
    "شركة البراميتر للتطوير",
]


# ---------------------------------------------------------------------------
# Premium Property Types
# ---------------------------------------------------------------------------
PROPERTY_TYPES = [
    "شقة فاخرة", "شقة فاخرة", "شقة فاخرة",  # 30%
    "فيلا", "فيلا دوبلكس", "تاون هاوس",  # 35%
    "محل تجاري", "مكتب", "مستودع",  # 35%
]


# ---------------------------------------------------------------------------
# Premium Clients
# ---------------------------------------------------------------------------
PREMIUM_CLIENTS = [
    {"name": "د. أحمد رشدي", "type": "investor", "origin": "القاهرة", "budget_range": "5-10M"},
    {"name": "م. محمدῡ", "type": "investor", "origin": "الإسكندرية", "budget_range": "3-5M"},
    {"name": "م. خالد العتيبي", "type": "businessman", "origin": "القاهرة", "budget_range": "10M+"},
    {"name": "د. سارة إبراهيم", "type": "professional", "origin": "شبين الكوم", "budget_range": "2-3M"},
    {"name": "م. عمر عبدالرحمن", "type": "investor", "origin": "الجيزة", "budget_range": "5-10M"},
    {"name": "أ. فاطمة الزهراء", "type": "businessman", "origin": "القاهرة", "budget_range": "3-5M"},
    {"name": "م. ياسر جمال", "type": "investor", "origin": "الإسكندرية", "budget_range": "10M+"},
    {"name": "د. هدى كريم", "type": "professional", "origin": "شبين الكوم", "budget_range": "2-3M"},
    {"name": "م. مصطفى عمرو", "type": "businessman", "origin": "القاهرة", "budget_range": "5-10M"},
    {"name": "أ. دينا فتحي", "type": "professional", "origin": "الجيزة", "budget_range": "3-5M"},
    {"name": "م. كريم سامي", "type": "investor", "origin": "الإسكندرية", "budget_range": "10M+"},
    {"name": "أ. منى حسين", "type": "businessman", "origin": "شبين الكوم", "budget_range": "2-3M"},
    {"name": "م. طارق ناصر", "type": "investor", "origin": "القاهرة", "budget_range": "5-10M"},
    {"name": "د. جنى أحمد", "type": "professional", "origin": "الجيزة", "budget_range": "3-5M"},
    {"name": "م. حاتم محمد", "type": "businessman", "origin": "الإسكندرية", "budget_range": "10M+"},
]


def generate_premium_properties(count=30):
    """Generate premium property listings for El Sadat City.
    
    Distribution:
    - Commercial/Industrial: 35% (11 properties)
    - Villas/Compounds: 35% (11 properties)
    - Premium Apartments: 30% (8 properties)
    """
    properties = []
    
    # Commercial/Industrial (35%)
    commercial_types = ["محل تجاري", "مكتب", "مستودع"]
    commercial_areas = [a for a in SADAT_AREAS if "صناعية" in a[0] or "Polaris" in a[0]]
    
    for i in range(11):
        area_name, city, base_price_per_sqm = random.choice(commercial_areas)
        prop_type = random.choice(commercial_types)
        
        if prop_type == "محل تجاري":
            area_sqm = random.randint(80, 250)
            price = random.randint(2500000, 8000000)
        elif prop_type == "مكتب":
            area_sqm = random.randint(60, 180)
            price = random.randint(1500000, 5000000)
        else:  # مستودع
            area_sqm = random.randint(200, 800)
            price = random.randint(3000000, 12000000)
        
        developer = random.choice(PREMIUM_DEVELOPERS)
        project = f"{developer} - {area_name}"
        
        prop = Property(
            title=f"{prop_type} في {area_name} - {project}",
            description=f"{prop_type} استثماري في {area_name}، مساحة {area_sqm} متر مربع. "
                        f"المطور: {developer}. تشطيب سوبر لوكس.",
            property_type=prop_type,
            status=random.choice(["available", "available", "reserved"]),
            area=area_name,
            city=city,
            district=area_name,
            price=price,
            bedrooms=None,
            bathrooms=1 if prop_type != "مستودع" else 2,
            area_sqm=area_sqm,
            developer=developer,
            project_name=project,
            delivery_date="جاهز",
            down_payment=round(price * 0.3, -3),
            monthly_installment=round(price * 0.7 / 60, -2),
            installment_years=5,
            payment_plan_details=f"دفعة أولى 30% - تقسيط 5 سنوات - كاش متاح",
            contact_name=f"م. {random.choice(['أحمد', 'محمد', 'علي', 'حسن', 'إبراهيم'])}",
            contact_phone=f"010{random.randint(10000000, 99999999)}",
            source="seed_data",
            score=round(random.uniform(7.0, 9.5), 1),
            tags="استثمار,تجاري,منطقة صناعية",
        )
        properties.append(prop)
    
    # Villas/Compounds (35%)
    villa_types = ["فيلا", "فيلا دوبلكس", "تاون هاوس"]
    villa_areas = [a for a in SADAT_AREAS if any(x in a[0] for x in ["الفردوس", "الكوثر", "النخيل", "الروضة", "شريط"])]
    
    for i in range(11):
        area_name, city, base_price_per_sqm = random.choice(villa_areas)
        prop_type = random.choice(villa_types)
        
        if prop_type == "فيلا":
            bedrooms = random.choice([4, 5, 5])
            area_sqm = random.randint(250, 450)
            price = random.randint(3000000, 12000000)
        elif prop_type == "فيلا دوبلكس":
            bedrooms = random.choice([4, 5, 5, 6])
            area_sqm = random.randint(300, 500)
            price = random.randint(4500000, 15000000)
        else:  # تاون هاوس
            bedrooms = random.choice([3, 4])
            area_sqm = random.randint(180, 280)
            price = random.randint(2500000, 5000000)
        
        bathrooms = bedrooms - 1
        developer = random.choice(PREMIUM_DEVELOPERS)
        project = f"كومباوند {developer} - {area_name}"
        
        prop = Property(
            title=f"{prop_type} في {area_name} - {project}",
            description=f"{prop_type} فاخرة في {area_name}، {bedrooms} غرف نوم، {area_sqm} متر مربع. "
                        f"المطور: {developer}. حديقة خاصة. أمن وحراسة 24/7.",
            property_type=prop_type,
            status=random.choice(["available", "available", "reserved"]),
            area=area_name,
            city=city,
            district=area_name,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            developer=developer,
            project_name=project,
            delivery_date=random.choice(["جاهز", "2026", "2027"]),
            down_payment=round(price * 0.2, -3),
            monthly_installment=round(price * 0.8 / 120, -2),
            installment_years=10,
            payment_plan_details=f"دفعة أولى 20% - تقسيط 10 سنوات - أسعار مميزة",
            contact_name=f"م. {random.choice(['أحمد', 'محمد', 'علي', 'حسن', 'إبراهيم'])}",
            contact_phone=f"010{random.randint(10000000, 99999999)}",
            source="seed_data",
            score=round(random.uniform(8.0, 9.8), 1),
            tags="فاخر,فيلا,كومباوند,حديقة خاصة",
        )
        properties.append(prop)
    
    # Premium Apartments (30%)
    apt_types = ["شقة فاخرة"]
    apt_areas = [a for a in SADAT_AREAS if any(x in a[0] for x in ["شريط", "الفردوس", "الكوثر", "النخيل", "الروضة"])]
    
    for i in range(8):
        area_name, city, base_price_per_sqm = random.choice(apt_areas)
        prop_type = "شقة فاخرة"
        
        bedrooms = random.choice([3, 3, 4])
        bathrooms = bedrooms - 1
        area_sqm = random.randint(150, 280)
        price = random.randint(1500000, 4500000)
        
        developer = random.choice(PREMIUM_DEVELOPERS)
        project = f"مجمع {developer} - {area_name}"
        
        prop = Property(
            title=f"{prop_type} في {area_name} - {project}",
            description=f"{prop_type} في {area_name}، {bedrooms} غرف نوم، {area_sqm} متر مربع. "
                        f"المطور: {developer}. تشطيب سوبر لوكس. فيو مميز.",
            property_type=prop_type,
            status=random.choice(["available", "available", "reserved"]),
            area=area_name,
            city=city,
            district=area_name,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            developer=developer,
            project_name=project,
            delivery_date=random.choice(["جاهز", "2026", "2027"]),
            down_payment=round(price * 0.25, -3),
            monthly_installment=round(price * 0.75 / 84, -2),
            installment_years=7,
            payment_plan_details=f"دفعة أولى 25% - تقسيط 7 سنوات - أسعار مميزة",
            contact_name=f"م. {random.choice(['أحمد', 'محمد', 'علي', 'حسن', 'إبراهيم'])}",
            contact_phone=f"010{random.randint(10000000, 99999999)}",
            source="seed_data",
            score=round(random.uniform(7.5, 9.2), 1),
            tags="فاخر,شقة,سوبر لوكس,فيو مميز",
        )
        properties.append(prop)
    
    return properties


def generate_premium_leads(count=15):
    """Generate premium lead records for El Sadat City."""
    BUYER_TYPES = ["Investor", "Investor", "Buyer", "Agency", "Developer"]
    URGENCY = ["High", "Normal", "Normal", "Low"]
    STATUSES = ["new", "new", "contacted", "qualified"]

    leads = []
    for i in range(count):
        client = PREMIUM_CLIENTS[i % len(PREMIUM_CLIENTS)]
        name = client["name"]
        phone = f"+2010{random.randint(10000000, 99999999)}"
        area = random.choice(SADAT_AREAS)[0]

        lead = Lead(
            title=name,
            url=f"whatsapp:{phone}",
            source=random.choice(["whatsapp_inbound", "website_form", "referral"]),
            lead_type=client["type"],
            budget=client["budget_range"],
            area=area,
            interest=random.choice(["شقة فاخرة", "فيلا", "محل تجاري", "مستودع"]),
            urgency=random.choice(URGENCY),
            phone=phone,
            email=f"{name.split()[0].lower()}@example.com" if random.random() > 0.5 else None,
            status=random.choice(STATUSES),
            score=round(random.uniform(60, 95), 1),
            tags=random.choice(["hot_lead", "investor", "premium_client", "follow_up"]),
        )
        leads.append(lead)
    return leads


def generate_premium_client_requests(count=10):
    """Generate premium client search requests for match-making."""
    requests = []
    for i in range(count):
        client = PREMIUM_CLIENTS[i % len(PREMIUM_CLIENTS)]
        area = random.choice(SADAT_AREAS)[0]
        
        # Premium budgets only
        min_budget = random.choice([1500000, 2500000, 5000000, 8000000])
        max_budget = min_budget + random.choice([1000000, 2500000, 5000000, 7000000])
        
        prop_type = random.choice(["شقة فاخرة", "فيلا", "محل تجاري", "مستودع"])
        bedrooms = random.choice([3, 4, 5]) if "شقة" in prop_type or "فيلا" in prop_type else None

        req = ClientRequest(
            client_name=client["name"],
            phone=f"+2011{random.randint(10000000, 99999999)}",
            property_type=prop_type,
            area=area,
            min_budget=min_budget,
            max_budget=max_budget,
            bedrooms=bedrooms,
            min_area_sqm=150 if bedrooms else 100,
            max_area_sqm=500 if bedrooms else 800,
            prefer_payment_plan=random.random() > 0.3,
            status=random.choice(["pending", "pending", "matched"]),
            priority=random.choice(["high", "high", "normal"]),
        )
        requests.append(req)
    return requests


def main():
    """Run the seed data script."""
    # Create output directory
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)

    # Database path
    db_path = output_dir / "cityestate.db"
    db_url = f"sqlite:///{db_path}"

    print(f"Database: {db_url}")
    print("=" * 50)

    # Create engine and tables
    engine = create_engine(db_url, echo=False, connect_args={"timeout": 30})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check existing data
        existing_props = session.query(Property).count()
        existing_leads = session.query(Lead).count()
        existing_reqs = session.query(ClientRequest).count()

        print(f"Existing: {existing_props} properties, {existing_leads} leads, {existing_reqs} requests")

        if existing_props > 0:
            print("\nDatabase already has data. Skipping seed.")
            print("Delete output/cityestate.db and re-run to refresh.")
            return

        # Generate premium properties
        print("\nGenerating 30 premium properties (El Sadat City)...")
        properties = generate_premium_properties(30)
        for p in properties:
            session.add(p)
        session.flush()
        print(f"  Added {len(properties)} premium properties")

        # Generate premium leads
        print("Generating 15 premium leads...")
        leads = generate_premium_leads(15)
        for l in leads:
            session.add(l)
        session.flush()
        print(f"  Added {len(leads)} premium leads")

        # Generate premium client requests
        print("Generating 10 premium client requests...")
        requests = generate_premium_client_requests(10)
        for r in requests:
            session.add(r)
        session.flush()
        print(f"  Added {len(requests)} premium client requests")

        # Commit
        session.commit()
        print("\n" + "=" * 50)
        print("PREMIUM SEED DATA CREATED SUCCESSFULLY!")
        print(f"  Properties:  {len(properties)} (Luxury/Commercial)")
        print(f"  Leads:       {len(leads)} (Premium Clients)")
        print(f"  Requests:    {len(requests)} (High-Value)")
        print(f"  Database:    {db_path}")
        print("=" * 50)

    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
