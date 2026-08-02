"""
Personalized Outreach Tasks — مهام الإرسال المخصص
==================================================
Task definitions for the personalized bulk outreach pipeline.
Each task is designed to create unique messages per recipient.
"""

from crewai import Task


def create_buyer_research_task(agent, buyer_data: dict) -> Task:
    """Create a task for researching a specific buyer.
    
    Args:
        agent: The researcher agent
        buyer_data: Dict with buyer profile info
        
    Returns:
        CrewAI Task object
    """
    name = buyer_data.get("name", "عميل")
    city = buyer_data.get("city", "القاهرة")
    property_type = buyer_data.get("property_type", "شقة")
    budget = buyer_data.get("budget", "2-3 مليون")
    source = buyer_data.get("source", "مجهول")
    notes = buyer_data.get("notes", "")

    return Task(
        description=(
            f"ابحث عن معلومات محددة للعميل التالي:\n\n"
            f"**بيانات العميل:**\n"
            f"- الاسم: {name}\n"
            f"- المدينة: {city}\n"
            f"- نوع العقار المطلوب: {property_type}\n"
            f"- الميزانية: {budget}\n"
            f"- مصدر العميل: {source}\n"
            f"- ملاحظات إضافية: {notes}\n\n"
            f"**المطلوب:**\n"
            f"1. متوسط أسعار {property_type} في {city} حالياً\n"
            f"2. أفضل 3 مشاريع في {city} تناسب ميزانية {budget}\n"
            f"3. أي عروض أو تخفيضات حالية في المنطقة\n"
            f"4. خطط التقسيط المتاحة في المشاريع\n"
            f"5. أحدث اتجاهات السوق في {city}\n\n"
            f"أعد النتيجة كـ JSON منظم."
        ),
        expected_output=(
            "JSON object بالشكل:\n"
            "{\n"
            '  "avg_price_per_sqm": "35,000 جنيه",\n'
            '  "projects": [\n'
            '    {"name": "Midtown Sky", "price": "3.5M", "developer": "Mountain View"},\n'
            '    {"name": "Zayed Top", "price": "2.8M", "developer": "Sodic"},\n'
            '    {"name": "New Egypt", "price": "3.2M", "developer": "Palm Hills"}\n'
            "  ],\n"
            '  "offers": "خصم 10% للمدفوعات النقدية",\n'
            '  "payment_plans": "تقسيط على 8 سنوات بدون فوائد",\n'
            '  "market_trend": "الأسعار في ارتصاد مستمر"\n'
            "}"
        ),
        agent=agent,
    )


def create_personalized_writing_task(
    agent, buyer_data: dict, research_context: list
) -> Task:
    """Create a task for writing a personalized message.
    
    Args:
        agent: The writer agent
        buyer_data: Dict with buyer profile info
        research_context: List of tasks to use as context (research task)
        
    Returns:
        CrewAI Task object
    """
    name = buyer_data.get("name", "عميل")
    city = buyer_data.get("city", "القاهرة")
    property_type = buyer_data.get("property_type", "شقة")
    budget = buyer_data.get("budget", "2-3 مليون")
    source = buyer_data.get("source", "مجهول")
    last_contact = buyer_data.get("last_contact", "لم يتواصل بعد")
    notes = buyer_data.get("notes", "")

    return Task(
        description=(
            f"اكتب رسالة واتساب فريدة ومخصصة لهذا العميل بالضبط.\n\n"
            f"**بيانات العميل:**\n"
            f"- الاسم: {name}\n"
            f"- المدينة: {city}\n"
            f"- نوع العقار: {property_type}\n"
            f"- الميزانية: {budget}\n"
            f"- مصدر العميل: {source}\n"
            f"- آخر تواصل: {last_contact}\n"
            f"- ملاحظات: {notes}\n\n"
            f"**تعليمات صارمة:**\n"
            f"1. الرسالة يجب أن تكون مختلفة تماماً عن أي رسالة أخرى\n"
            f"2. اكتب بالعامية المصرية الطبيعية\n"
            f"3. ابدأ بترحيب شخصي باسم {name}\n"
            f"4. اذكر شيئاً محدداً عن حالة العميل\n"
            f"5. أدرج 1-2 مشاريع محددة من بيانات البحث أعلاه\n"
            f"6. اذكر سبباً مقنعاً للacted الآن\n"
            f"7. اختتم بـ CTA: 'عايز تعرف أكتر؟'\n"
            f"8. لا تزيد الرسالة عن 150 كلمة\n"
            f"9. استخدم إيموجي بذكاء (2-3 إيموجي فقط)\n"
            f"10. اجعلها تبدو كأن صديق يرشدك لمشروع جيد"
        ),
        expected_output=(
            "رسالة واتساب واحدة جاهزة للإرسال بالعامية المصرية. "
            "لا تزيد عن 150 كلمة. تبدأ بترحيب شخصي وتنتهي بـ CTA."
        ),
        agent=agent,
        context=research_context,
    )


def create_message_review_task(agent, writing_context: list) -> Task:
    """Create a task for reviewing the generated message.
    
    Args:
        agent: The reviewer agent
        writing_context: List of tasks to use as context (writing task)
        
    Returns:
        CrewAI Task object
    """
    return Task(
        description=(
            "راجع رسالة الواتساب المولّدة وتأكد من أنها تلبي المعايير التالية:\n\n"
            "1. **فريدة**: لا تشبه رسالة تسويقية جماعية\n"
            "2. **طبيعية**: تبدو كرسالة شخصية\n"
            "3. **اللغة**: عامية مصرية صحيحة\n"
            "4. **الشخصية**: تبدأ باسم العميل\n"
            "5. **القيمة**: تذكر معلومات مفيدة عن العقارات\n"
            "6. **CTA**: دعوة واضحة بدون ضغط\n"
            "7. **الطول**: مناسبة للواتساب\n\n"
            "إذا فشلت في أي معيار، أعد كتابتها."
        ),
        expected_output=(
            "الرسالة النهائية الجاهزة للإرسال بعد المراجعة والتعديل."
        ),
        agent=agent,
        context=writing_context,
    )
